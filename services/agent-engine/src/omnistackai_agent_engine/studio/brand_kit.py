"""PC-020: the brand kit - one place to change a built product's look, and every app follows.

`brand.json` (R-548) is already the single source: colours, fonts and corners reach every app live,
the phone app reads the name at start-up. What was missing is a way for the owner to change it
without editing JSON, and two things that never followed it:

* **the name** was written into each app's pages when they were generated;
* **a logo** had nowhere to go - the apps showed an initial on the brand colour.

``update_brand`` changes the inputs (validated), puts a logo where every app uses it - the header
of each web app (through `lib/brand.ts`, PC-020), the browser-tab and home-screen icons, the phone
app's icons - renames the product in the pages that were generated with the old name, regenerates
the icons the platform made (`brand/generate.mjs`, never one the owner supplied), keeps the
project's plan in step so later edits and page design use the new brand, and commits it all.
"""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_NAME = re.compile(r"^[\w][\w &'.\-]{0,59}$", re.UNICODE)
#: Google Fonts the design directions use, plus common choices; any of them loads in every app.
FONTS = ("Inter", "Manrope", "Space Grotesk", "Nunito", "Poppins", "DM Sans", "Playfair Display", "Figtree",
         "Source Sans 3", "Merriweather", "Roboto", "Open Sans", "Lato", "Montserrat", "Outfit", "Plus Jakarta Sans",
         "Work Sans", "Raleway", "Lora", "Rubik")
RADII = ("none", "sm", "md", "lg", "xl")
STYLES = ("professional", "bold", "playful", "elegant", "minimal", "editorial", "friendly", "calm", "vibrant")
MAX_LOGO_BYTES = 512 * 1024
_TEXT_SUFFIXES = (".tsx", ".ts", ".js", ".mjs", ".json", ".md", ".html", ".txt", ".webmanifest")
_SKIP_DIRS = {"node_modules", ".next", ".git", ".expo", "dist", "build"}


class BrandError(ValueError):
    pass


@dataclass(frozen=True)
class Logo:
    data: bytes
    kind: str  # "png" | "svg"


def read_brand(repo: str | Path) -> dict[str, Any]:
    path = Path(repo) / "brand.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BrandError("this project has no brand.json") from error
    return {
        "name": data.get("name", ""),
        "primary_color": data.get("primaryColor", ""),
        "accent_color": data.get("accentColor", ""),
        "font": data.get("fontFamily", ""),
        "heading_font": data.get("headingFont", ""),
        "radius": data.get("borderRadius", "md"),
        "style": data.get("style", ""),
        "logo": data.get("logo", ""),
        "apps": [p.name for p in sorted((Path(repo) / "apps").glob("*")) if p.is_dir()],
        "choices": {"fonts": list(FONTS), "radii": list(RADII), "styles": list(STYLES)},
    }


def decode_logo(value: str) -> Logo:
    """A logo sent as a data URL (``data:image/png;base64,...`` or SVG). PNG and SVG only, at most 512 KB."""
    match = re.match(r"^data:image/(png|svg\+xml);base64,([A-Za-z0-9+/=\s]+)$", value or "")
    if not match:
        raise BrandError("the logo must be a PNG or SVG image")
    data = base64.b64decode(match.group(2), validate=False)
    if len(data) > MAX_LOGO_BYTES:
        raise BrandError("the logo is larger than 512 KB")
    kind = "png" if match.group(1) == "png" else "svg"
    if kind == "png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise BrandError("the logo is not a PNG image")
    if kind == "svg":
        text = data.decode("utf-8", errors="replace")
        if "<svg" not in text or re.search(r"<script|on\w+\s*=|javascript:", text, re.I):
            raise BrandError("the SVG logo contains scripts, which an icon may not have")
    return Logo(data, kind)


def _validated(changes: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    if "name" in changes:
        name = str(changes["name"] or "").strip()
        if not _NAME.match(name):
            raise BrandError("the name must be 1-60 letters, numbers, spaces or & ' . -")
        out["name"] = name
    for key in ("primary_color", "accent_color"):
        if key in changes and changes[key]:
            value = str(changes[key])
            if not _HEX.match(value):
                raise BrandError(f"{key.replace('_', ' ')} must be a colour like #1d4ed8")
            out[key] = value.lower()
    for key in ("font", "heading_font"):
        if key in changes and changes[key]:
            if changes[key] not in FONTS:
                raise BrandError(f"{changes[key]!r} is not one of the fonts every app can load")
            out[key] = str(changes[key])
    if changes.get("radius"):
        if changes["radius"] not in RADII:
            raise BrandError("corners must be one of " + ", ".join(RADII))
        out["radius"] = str(changes["radius"])
    if changes.get("style"):
        if changes["style"] not in STYLES:
            raise BrandError("unknown style")
        out["style"] = str(changes["style"])
    return out


def _text_files(repo: Path):
    for path in (repo / "apps").rglob("*"):
        if path.is_file() and path.suffix in _TEXT_SUFFIXES and not (_SKIP_DIRS & set(path.relative_to(repo).parts)):
            yield path
    for name in ("README.md",):
        if (repo / name).is_file():
            yield repo / name


def rename_in_pages(repo: Path, old: str, new: str) -> list[str]:
    """Pages generated with the old name, renamed. Whole words only; brand.json is set separately."""
    if not old or old == new:
        return []
    pattern = re.compile(rf"(?<![\w-]){re.escape(old)}(?![\w-])")
    changed = []
    for path in _text_files(repo):
        text = path.read_text(encoding="utf-8", errors="replace")
        updated = pattern.sub(new.replace("\\", "\\\\"), text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(str(path.relative_to(repo)))
    return changed


def place_logo(repo: Path, logo: Logo) -> list[str]:
    """The logo where every app uses it: brand/, each web app's public/ and tab icon, the phone app's icons."""
    written = []
    (repo / "brand").mkdir(exist_ok=True)
    stored = repo / "brand" / f"logo.{logo.kind}"
    for old in (repo / "brand").glob("logo.*"):
        old.unlink()
    stored.write_bytes(logo.data)
    written.append(str(stored.relative_to(repo)))
    for app in sorted((repo / "apps").glob("*")):
        if (app / "next.config.mjs").exists() or (app / "next.config.ts").exists() or (app / "next.config.js").exists():
            (app / "public").mkdir(exist_ok=True)
            for old in (app / "public").glob("brand-logo.*"):
                old.unlink()
            (app / "public" / f"brand-logo.{logo.kind}").write_bytes(logo.data)
            written.append(str((app / "public" / f"brand-logo.{logo.kind}").relative_to(repo)))
            # The browser tab: Next serves app/icon.svg or app/icon.png - never both.
            for old in (app / "app").glob("icon.*"):
                old.unlink()
            (app / "app" / f"icon.{logo.kind}").write_bytes(logo.data)
            written.append(str((app / "app" / f"icon.{logo.kind}").relative_to(repo)))
        elif (app / "app.config.js").exists() and logo.kind == "png":
            # The phone app's home-screen icons (an SVG cannot be one; generated icons stay then).
            for name in ("icon.png", "adaptive-icon.png"):
                (app / "assets").mkdir(exist_ok=True)
                (app / "assets" / name).write_bytes(logo.data)
                written.append(str((app / "assets" / name).relative_to(repo)))
    return written


def _regenerate_icons(repo: Path) -> str:
    node = shutil.which("node")
    if not node or not (repo / "brand" / "generate.mjs").exists():
        return "icons not regenerated (Node is not available)"
    done = subprocess.run([node, "brand/generate.mjs"], cwd=repo, capture_output=True, text=True, timeout=120, check=False)
    return "icons regenerated" if done.returncode == 0 else f"icons not regenerated: {(done.stderr or done.stdout)[-200:]}"


def update_brand(repo: str | Path, changes: dict[str, Any], *, author_name: str = "OmniStackAI",
                 author_email: str = "agent@omnistack.ai") -> dict[str, Any]:
    """Apply a brand change to a built project; returns what changed. Raises BrandError for bad input."""
    from ..git_service import commit_all

    root = Path(repo)
    path = root / "brand.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BrandError("this project has no brand.json") from error
    values = _validated(changes)
    logo = decode_logo(str(changes["logo"])) if changes.get("logo") else None
    if not values and logo is None and not changes.get("remove_logo"):
        raise BrandError("nothing to change")

    keys = {"name": "name", "primary_color": "primaryColor", "accent_color": "accentColor", "font": "fontFamily",
            "heading_font": "headingFont", "radius": "borderRadius", "style": "style"}
    old_name = str(document.get("name") or "")
    for key, value in values.items():
        document[keys[key]] = value
    renamed: list[str] = []
    if "name" in values:
        renamed = rename_in_pages(root, old_name, values["name"])
    placed: list[str] = []
    if logo is not None:
        placed = place_logo(root, logo)
        document["logo"] = f"/brand-logo.{logo.kind}"
    elif changes.get("remove_logo") and document.get("logo"):
        document.pop("logo", None)
        for stale in list((root / "brand").glob("logo.*")) + list((root / "apps").glob("*/public/brand-logo.*")):
            stale.unlink()
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    icons = _regenerate_icons(root)
    commit = commit_all(str(root), author_name=author_name, author_email=author_email,
                        message="chore(brand): " + ", ".join(sorted(set(values) | ({"logo"} if logo else set())) or {"logo removed"}))
    return {"brand": read_brand(root), "changed": sorted(values), "logo": placed, "renamed_files": len(renamed),
            "icons": icons, "commit_sha": getattr(commit, "commit_sha", "")}


def brand_tokens_for(brand: dict[str, Any], current: Any) -> Any:
    """The plan's brand after a change, so later edits and page design use it."""
    from dataclasses import replace

    from ..codegen.brand import mix

    primary = brand.get("primary_color") or current.primary_color
    return replace(current, primary_color=primary, dark_primary_color=mix(primary, "#ffffff", 0.18),
                   font_family=brand.get("font") or current.font_family,
                   heading_font=brand.get("heading_font") or current.heading_font,
                   accent_color=brand.get("accent_color") or current.accent_color,
                   border_radius=brand.get("radius") or current.border_radius,
                   style=brand.get("style") or current.style)
