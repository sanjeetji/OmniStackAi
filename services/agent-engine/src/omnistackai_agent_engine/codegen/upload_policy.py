"""PC-102: what an attachment field accepts - types, size and count - follows the requirement.

The planner can state it on the field (validation rules ``accept:pdf|docx``, ``accept:images``,
``max_size_mb:10``, ``max_files:5``). When it does not, the field's name decides deterministically
("resume" takes documents, "photos" takes up to eight images, "invoice" takes PDFs, images and
spreadsheets), so every attachment field has a sensible, narrow policy. Whatever a field says,
executables, scripts and web pages are never accepted.

The same policy drives the browser check (Uppy restrictions), the server check (the API reads the
file's first bytes and refuses a type that does not match), and the words the form shows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..application_ir import ApplicationIR, Entity, Field, FieldType

#: Extension groups a rule may name instead of listing extensions.
GROUPS: dict[str, tuple[str, ...]] = {
    "images": ("jpg", "jpeg", "png", "webp", "gif", "avif", "heic"),
    "documents": ("pdf", "doc", "docx", "odt", "rtf", "txt"),
    "pdf": ("pdf",),
    "word": ("doc", "docx"),
    "spreadsheets": ("xlsx", "xls", "ods", "csv"),
    "presentations": ("pptx", "ppt", "odp"),
    "audio": ("mp3", "wav", "m4a", "ogg"),
    "video": ("mp4", "mov", "webm"),
    "archives": ("zip",),
    "medical": ("dcm",),
}

#: Every extension the generated apps know how to verify by content. Anything else is refused.
KNOWN: frozenset[str] = frozenset(ext for group in GROUPS.values() for ext in group)

#: Never accepted, whatever a rule says (they run code, or a browser would run their script).
FORBIDDEN: frozenset[str] = frozenset({
    "exe", "msi", "bat", "cmd", "com", "scr", "ps1", "vbs", "js", "mjs", "jar", "apk", "app", "dmg",
    "sh", "bash", "php", "py", "rb", "pl", "html", "htm", "xhtml", "svg", "hta", "dll", "so", "docm",
    "xlsm", "pptm",
})

MIME: dict[str, str] = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif",
    "avif": "image/avif", "heic": "image/heic", "pdf": "application/pdf", "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "odt": "application/vnd.oasis.opendocument.text", "rtf": "application/rtf", "txt": "text/plain",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel", "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "csv": "text/csv", "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint", "odp": "application/vnd.oasis.opendocument.presentation",
    "mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4", "ogg": "audio/ogg", "mp4": "video/mp4",
    "mov": "video/quicktime", "webm": "video/webm", "zip": "application/zip", "dcm": "application/dicom",
}

#: Uploads pass through the app's API (streamed and checked), so one file is capped here.
MAX_SIZE_MB = 100

_DEFAULTS: tuple[tuple[tuple[str, ...], tuple[str, ...], int, int], ...] = (
    # (name keywords, groups, max size MB, max files) - the first match wins.
    (("resume", "cv", "curriculum"), ("pdf", "word"), 10, 1),
    (("avatar", "logo", "icon", "profile_photo", "profile_picture", "headshot"), ("images",), 2, 1),
    (("xray", "x_ray", "mri", "ct_scan", "dicom", "lab_report", "prescription", "medical"), ("pdf", "images", "medical"), 50, 1),
    (("photo", "image", "picture", "pic", "thumbnail", "banner", "cover", "gallery", "screenshot"), ("images",), 5, 1),
    (("invoice", "receipt", "bill", "statement", "payslip", "quotation", "quote"), ("pdf", "images", "spreadsheets"), 10, 1),
    (("video", "clip", "recording_video"), ("video",), 100, 1),
    (("audio", "recording", "voice", "podcast", "song", "track"), ("audio",), 50, 1),
    (("spreadsheet", "sheet", "excel", "csv", "workbook"), ("spreadsheets",), 10, 1),
    (("presentation", "slides", "deck", "pitch"), ("presentations", "pdf"), 25, 1),
    (("contract", "agreement", "certificate", "license", "licence", "id_proof", "kyc", "passport", "document", "doc"),
     ("pdf", "word", "images"), 10, 1),
    (("archive", "zip", "bundle"), ("archives",), 50, 1),
)
_DEFAULT_GROUPS = ("documents", "images", "spreadsheets")
_PLURAL_FILES = 8


@dataclass(frozen=True, slots=True)
class UploadPolicy:
    extensions: tuple[str, ...]
    max_size_mb: int
    max_files: int

    @property
    def mime_types(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(MIME[ext] for ext in self.extensions))

    def describe(self) -> str:
        """Plain words for the form: "PDF, DOC or DOCX, up to 10 MB"."""
        names = [ext.upper() for ext in self.extensions if ext != "jpeg"]
        listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " or " + names[-1]
        count = f"up to {self.max_files} files, " if self.max_files > 1 else ""
        return f"{listed}; {count}up to {self.max_size_mb} MB each" if count else f"{listed}, up to {self.max_size_mb} MB"


def _expand(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for token in tokens:
        token = token.strip().lower().lstrip(".")
        out.extend(GROUPS.get(token, (token,)))
    return out


def _words(name: str) -> list[str]:
    return [w for w in re.split(r"[_\W]+", name.lower()) if w]


def _mentions(name_words: list[str], keyword: str) -> bool:
    """Whole words in order: "ct_scan" is in "chest_ct_scan", not in "contract_scan"."""
    wanted = keyword.split("_")
    return any(name_words[i:i + len(wanted)] == wanted for i in range(len(name_words)))


def policy_for(field: Field) -> UploadPolicy:
    """The field's upload policy: its own rules first, then its name, then a safe default."""
    accept: list[str] = []
    size: int | None = None
    count: int | None = None
    for rule in field.validation:
        key, _, value = rule.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "accept" and value:
            accept = _expand(re.split(r"[|,\s]+", value))
        elif key in ("max_size_mb", "max_size") and re.fullmatch(r"\d+", value):
            size = int(value)
        elif key == "max_files" and re.fullmatch(r"\d+", value):
            count = int(value)

    words = _words(field.name)
    singular = [w[:-1] if w.endswith("s") and not w.endswith("ss") else w for w in words]
    default_groups, default_size, default_count = _DEFAULT_GROUPS, 10, 1
    for keywords, groups, max_mb, max_files in _DEFAULTS:
        if any(_mentions(words, k) or _mentions(singular, k) for k in keywords):
            default_groups, default_size, default_count = groups, max_mb, max_files
            break
    if not accept:
        accept = _expand(list(default_groups))
    # "photos", "documents", "attachments", "files": several are expected.
    if count is None:
        count = _PLURAL_FILES if (field.name.endswith("s") and not field.name.endswith("ss")) else default_count
    extensions = tuple(dict.fromkeys(ext for ext in accept if ext in KNOWN and ext not in FORBIDDEN))
    if not extensions:  # a rule that named only unknown or forbidden types falls back to the default
        extensions = tuple(dict.fromkeys(_expand(list(default_groups))))
    size = max(1, min(size or default_size, MAX_SIZE_MB))
    return UploadPolicy(extensions, size, max(1, min(count, 20)))


def attachment_fields(ir: ApplicationIR) -> list[tuple[Entity, Field, UploadPolicy]]:
    return [(entity, field, policy_for(field)) for entity in ir.entities for field in entity.fields
            if field.type is FieldType.ATTACHMENT]


def has_uploads(ir: ApplicationIR) -> bool:
    return bool(attachment_fields(ir))
