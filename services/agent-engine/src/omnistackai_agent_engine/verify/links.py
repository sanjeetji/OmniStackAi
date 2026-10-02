"""PC-125 (with PC-116): every link in a generated app goes to a page that exists in that app.

A model writing a page invents plausible addresses: the PC-122 benchmark's clinic home page linked to
`/appointment_list` (the app's records are bookings), `/terms` and `/privacy` (no such pages), and
PC-116's storefront linked to `/listings/new`, which only the seller portal has. The type check
cannot see any of this: an address is just a string. So:

* **check** - every internal address a page links or navigates to (`href`, `router.push`,
  `router.replace`, `redirect`) is matched against the app's own pages (`app/**/page.tsx`, with
  `[id]` segments matching anything). An address that is a data route (`app/**/route.ts`, which
  answers JSON) is not a page either. Each miss is reported like a compiler error, with the pages
  that do exist, so the model's repair gets the exact problem and the answer;
* **fix** - when the model cannot, the address is pointed at the closest page that exists (the
  same kind of page for the same or a similar record, else the home page). A working link to the
  wrong-ish page beats a 404, and nothing else on the page is lost.

Pure file reading - no toolchain, no model - so `task verify` covers all of it.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from .compile import CompileError

CODE = "OSA404"
_SKIP_DIRS = {"node_modules", ".next", "api"}
#: The address after href= / push( / replace( / redirect( - quoted, braced or a template literal.
_LINK = re.compile(
    r"""(?:\bhref\s*=\s*\{?\s*|\b(?:router\.(?:push|replace|prefetch)|redirect|permanentRedirect)\(\s*)"""
    r"""(?P<quote>["'`])(?P<target>/[^"'`\s]*)(?P=quote)"""
)
_KINDS = ("_list", "_detail", "_editor", "_new", "_edit", "s")


@dataclass(frozen=True)
class Link:
    path: str  # web-app-relative file
    line: int
    column: int
    target: str  # as written
    route: str  # without query, hash, or ${...}


def _route_of(directory: Path, app: Path) -> str:
    parts = [p for p in directory.relative_to(app).parts if not (p.startswith("(") and p.endswith(")")) and not p.startswith("@")]
    return "/" + "/".join(parts) if parts else "/"


def page_routes(web_dir: str | Path) -> list[str]:
    app = Path(web_dir) / "app"
    if not app.is_dir():
        return []
    return sorted({_route_of(p.parent, app) for p in app.rglob("page.tsx") if not _skipped(p, app)}
                  | {_route_of(p.parent, app) for p in app.rglob("page.jsx") if not _skipped(p, app)})


def data_routes(web_dir: str | Path) -> list[str]:
    app = Path(web_dir) / "app"
    if not app.is_dir():
        return []
    return sorted({_route_of(p.parent, app) for p in app.rglob("route.ts") if "node_modules" not in p.parts})


def _skipped(path: Path, app: Path) -> bool:
    return any(part in ("node_modules", ".next") for part in path.relative_to(app).parts)


def _normalise(target: str) -> str:
    route = re.sub(r"\$\{[^}]*\}", "__any__", target)
    route = re.split(r"[?#]", route, maxsplit=1)[0].rstrip("/") or "/"
    return route


def _matches(route: str, pattern: str) -> bool:
    if pattern == "/":
        return route == "/"
    want, have = pattern.strip("/").split("/"), route.strip("/").split("/")
    for index, part in enumerate(want):
        if part.startswith("[[...") or part.startswith("[..."):
            return len(have) >= index + (0 if part.startswith("[[") else 1)
        if index >= len(have):
            return False
        if part.startswith("[") or have[index] == "__any__":
            continue
        if "__any__" in have[index]:
            if not re.fullmatch(re.escape(have[index]).replace("__any__", ".*"), part):
                return False
            continue
        if part != have[index]:
            return False
    return len(have) == len(want)


def find_links(text: str, path: str = "") -> list[Link]:
    links = []
    for match in _LINK.finditer(text):
        target = match.group("target")
        if target.startswith("//"):  # protocol-relative: another site
            continue
        line = text.count("\n", 0, match.start("target")) + 1
        column = match.start("target") - (text.rfind("\n", 0, match.start("target")) + 1) + 1
        links.append(Link(path, line, column, target, _normalise(target)))
    return links


def _source_files(web_dir: Path) -> list[Path]:
    files = []
    for folder in ("app", "components", "src", "lib"):
        root = web_dir / folder
        if not root.is_dir():
            continue
        for file in root.rglob("*"):
            if file.suffix not in (".tsx", ".ts", ".jsx") or file.name.startswith("route."):
                continue
            rel = file.relative_to(web_dir).parts
            if any(part in ("node_modules", ".next") for part in rel) or (len(rel) > 1 and rel[0] == "app" and rel[1] == "api"):
                continue
            files.append(file)
    return sorted(files)


def is_page(route: str, pages: list[str]) -> bool:
    return any(_matches(route, pattern) for pattern in pages)


def check_links(web_dir: str | Path) -> tuple[CompileError, ...]:
    """Every link to an address that is not a page of this app, as compiler-style errors."""
    web = Path(web_dir)
    pages = page_routes(web)
    if not pages:
        return ()
    data = data_routes(web)
    errors = []
    listed = ", ".join(pages[:40])
    for file in _source_files(web):
        rel = file.relative_to(web).as_posix()
        for link in find_links(file.read_text(encoding="utf-8", errors="replace"), rel):
            if is_page(link.route, pages):
                continue
            what = ("is a data route (it answers JSON), not a page" if any(_matches(link.route, d) for d in data)
                    else "goes to no page in this app")
            errors.append(CompileError(rel, link.line, link.column, CODE,
                                       f'link "{link.target}" {what}. Link only to pages that exist: {listed}'))
    return tuple(errors)


def _stem(route: str) -> tuple[str, str]:
    """('/appointment_list') -> ('appointment', '_list')."""
    last = route.rstrip("/").rsplit("/", 1)[-1]
    for kind in _KINDS[:-1]:
        if last.endswith(kind):
            return last[: -len(kind)], kind
    return last, ""


#: Records people call by different names. A model asked for "appointments" links to an
#: appointment page in an app whose records are bookings (found in the PC-122 benchmark).
_SAME_THING = (
    {"appointment", "booking", "reservation", "visit", "session", "slot"},
    {"customer", "client", "member", "patient", "user", "account", "profile"},
    {"order", "purchase", "sale", "checkout"},
    {"product", "item", "listing", "offering"},
    {"provider", "doctor", "stylist", "trainer", "technician", "professional", "staff"},
    {"post", "article", "story", "entry"},
    {"message", "conversation", "chat", "thread"},
    {"review", "rating", "feedback", "testimonial"},
    {"invoice", "bill", "payment"},
    {"ticket", "issue", "request", "case"},
)


def _same_record(a: str, b: str) -> bool:
    return any(a in group and b in group for group in _SAME_THING)


def nearest_page(route: str, pages: list[str]) -> str:
    """The closest page that exists: same kind of page for a similar record, else a similar address, else home."""
    static = [p for p in pages if "[" not in p]
    if not static or route == "/":
        return "/"
    stem, kind = _stem(route)
    if kind:
        same_kind = [p for p in static if _stem(p)[1] == kind]
        best = difflib.get_close_matches(stem, [_stem(p)[0] for p in same_kind], n=1, cutoff=0.5)
        if best:
            return next(p for p in same_kind if _stem(p)[0] == best[0])
        synonym = [p for p in same_kind if _same_record(_singular(stem), _stem(p)[0])]
        if synonym:
            return synonym[0]
    close = difflib.get_close_matches(route, static, n=1, cutoff=0.75)
    if close:
        return close[0]
    if kind == "_list":
        lists = [p for p in static if p.endswith("_list")]
        if len(lists) == 1:
            return lists[0]
    return "/"


def _singular(word: str) -> str:
    word = word.replace("-", "_")
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("ses") or word.endswith("xes"):
        return word[:-2]
    return word[:-1] if word.endswith("s") and not word.endswith("ss") else word


def record_page(target: str, pages: list[str]) -> str | None:
    """A link to a record's data route, as the page that shows it.

    `/posts/${post.id}` -> `/post_detail?id=${post.id}` and `/posts` -> `/post_list`, when those pages
    exist - the generated apps address a record's page by `?id=`.
    """
    bare = re.split(r"[?#]", target, maxsplit=1)[0].strip("/")
    parts = bare.split("/") if bare else []
    if not parts or len(parts) > 2:
        return None
    singular = _singular(parts[-2] if len(parts) == 2 else parts[0])
    if len(parts) == 2 and f"/{singular}_detail" in pages:
        return f"/{singular}_detail?id={parts[1]}"
    if len(parts) == 1 and f"/{singular}_list" in pages:
        return f"/{singular}_list"
    return None


def fix_links(text: str, pages: list[str]) -> tuple[str, list[tuple[str, str]]]:
    """Point every link that goes nowhere at the nearest page that exists. Returns (text, [(from, to)])."""
    changes: list[tuple[str, str]] = []

    def _replace(match: re.Match) -> str:
        target = match.group("target")
        route = _normalise(target)
        if target.startswith("//") or is_page(route, pages):
            return match.group(0)
        new = record_page(target, pages) or nearest_page(route, pages)
        changes.append((target, new))
        start, end = match.start("target") - match.start(0), match.end("target") - match.start(0)
        return match.group(0)[:start] + new + match.group(0)[end:]

    return _LINK.sub(_replace, text), changes


def fix_links_in(web_dir: str | Path, paths: list[str] | None = None) -> dict[str, list[tuple[str, str]]]:
    """Fix the dead links in these files (web-app-relative), or in every source file. Returns what changed."""
    web = Path(web_dir)
    pages = page_routes(web)
    changed: dict[str, list[tuple[str, str]]] = {}
    files = [web / p for p in paths] if paths is not None else _source_files(web)
    for file in files:
        if not file.is_file():
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        fixed, changes = fix_links(text, pages)
        if changes:
            file.write_text(fixed, encoding="utf-8")
            changed[file.relative_to(web).as_posix()] = changes
    return changed
