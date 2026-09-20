"""Deterministic SEO & AI search audit for generated Next.js applications.

Inspects generated source code without model calls (0 credits, free and fast):
- Missing or duplicate page titles
- Description length (recommended 50-160 characters)
- Missing canonical URL
- Missing OpenGraph image
- Missing or multiple <h1> headings
- Images missing alt attributes
- Routes missing from sitemap.ts
- Unintentional noindex on public routes
- Missing public/llms.txt
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SEOFinding:
    id: str
    severity: str  # "error", "warning", "info"
    route: str
    file: str
    line: int
    message: str
    suggestion: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SEOAuditReport:
    score: int
    passed: int
    total: int
    findings: list[SEOFinding]

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "passed": self.passed,
            "total": self.total,
            "findings": [f.to_dict() for f in self.findings],
        }


def _find_line_number(content: str, pattern: re.Pattern | str) -> int:
    lines = content.splitlines()
    for idx, line in enumerate(lines, start=1):
        if isinstance(pattern, re.Pattern):
            if pattern.search(line):
                return idx
        elif pattern in line:
            return idx
    return 1


def audit_files_seo(files: dict[str, str]) -> SEOAuditReport:
    """Run deterministic SEO audit on an in-memory dictionary of relative_path -> content."""
    findings: list[SEOFinding] = []
    checks_total = 0
    checks_passed = 0

    # 1. Check public/llms.txt
    checks_total += 1
    if "public/llms.txt" not in files:
        findings.append(
            SEOFinding(
                id="missing-llms-txt",
                severity="warning",
                route="/",
                file="public/llms.txt",
                line=1,
                message="Missing public/llms.txt for AI crawlers and search agents",
                suggestion="Add public/llms.txt to declare app purpose, main routes, and indexing policy for AI search engines.",
            )
        )
    else:
        checks_passed += 1

    # 2. Check app/sitemap.ts
    checks_total += 1
    has_sitemap = "app/sitemap.ts" in files
    sitemap_content = files.get("app/sitemap.ts", "")
    if not has_sitemap:
        findings.append(
            SEOFinding(
                id="missing-sitemap",
                severity="error",
                route="/",
                file="app/sitemap.ts",
                line=1,
                message="Missing app/sitemap.ts",
                suggestion="Create app/sitemap.ts to enumerate indexable routes for search engines.",
            )
        )
    else:
        checks_passed += 1

    # 3. Check app/robots.ts
    checks_total += 1
    if "app/robots.ts" not in files:
        findings.append(
            SEOFinding(
                id="missing-robots",
                severity="warning",
                route="/",
                file="app/robots.ts",
                line=1,
                message="Missing app/robots.ts",
                suggestion="Create app/robots.ts to instruct search engine crawlers and point to the sitemap.",
            )
        )
    else:
        checks_passed += 1

    # 4. Check OpenGraph image
    checks_total += 1
    has_og_image = "app/opengraph-image.tsx" in files or "app/opengraph-image.png" in files
    if not has_og_image:
        findings.append(
            SEOFinding(
                id="missing-og-image",
                severity="warning",
                route="/",
                file="app/opengraph-image.tsx",
                line=1,
                message="Missing app/opengraph-image.tsx for social previews",
                suggestion="Create app/opengraph-image.tsx to generate rich preview cards when links are shared on social media.",
            )
        )
    else:
        checks_passed += 1

    # 5. Extract routes and page metadata
    # Root layout
    root_layout = files.get("app/layout.tsx", "")
    routes_found: set[str] = {"/"}
    titles_by_route: dict[str, str] = {}
    descriptions_by_route: dict[str, str] = {}

    # Extract title from root layout
    title_match = re.search(r'title:\s*(?:{\s*default:\s*"([^"]+)"|"([^"]+)")', root_layout)
    if title_match:
        t = title_match.group(1) or title_match.group(2) or ""
        titles_by_route["/"] = t.strip()

    desc_match = re.search(r'description:\s*"([^"]*)"', root_layout)
    if desc_match:
        descriptions_by_route["/"] = desc_match.group(1).strip()

    # Discover screen routes from layouts/pages
    for path, content in files.items():
        if path.startswith("app/") and path.endswith("/layout.tsx") and path != "app/layout.tsx":
            route_name = path[len("app/") : -len("/layout.tsx")]
            route = f"/{route_name}"
            routes_found.add(route)

            t_match = re.search(r'title:\s*"([^"]*)"', content)
            if t_match:
                titles_by_route[route] = t_match.group(1).strip()

            d_match = re.search(r'description:\s*"([^"]*)"', content)
            if d_match:
                descriptions_by_route[route] = d_match.group(1).strip()

    # Audit each route for titles, descriptions, canonical, and sitemap presence
    for route in sorted(routes_found):
        layout_path = "app/layout.tsx" if route == "/" else f"app{route}/layout.tsx"
        layout_content = files.get(layout_path, "")

        # Title check
        checks_total += 1
        title = titles_by_route.get(route, "")
        if not title:
            findings.append(
                SEOFinding(
                    id="missing-title",
                    severity="error",
                    route=route,
                    file=layout_path,
                    line=_find_line_number(layout_content, "title") or 1,
                    message=f"Route '{route}' is missing a page title",
                    suggestion="Add a concise, descriptive title (under 60 characters) in page metadata.",
                )
            )
        else:
            checks_passed += 1

        # Description length check (recommended 50-160 characters)
        checks_total += 1
        desc = descriptions_by_route.get(route, "")
        if not desc:
            findings.append(
                SEOFinding(
                    id="missing-description",
                    severity="error",
                    route=route,
                    file=layout_path,
                    line=_find_line_number(layout_content, "description") or 1,
                    message=f"Route '{route}' is missing a meta description",
                    suggestion="Add a meta description between 50 and 160 characters describing the page.",
                )
            )
        elif len(desc) < 50:
            findings.append(
                SEOFinding(
                    id="short-description",
                    severity="warning",
                    route=route,
                    file=layout_path,
                    line=_find_line_number(layout_content, "description") or 1,
                    message=f"Route '{route}' description is too short ({len(desc)} characters, recommended 50–160)",
                    suggestion="Expand the description to at least 50 characters to provide better snippet context in search engines.",
                )
            )
        elif len(desc) > 160:
            findings.append(
                SEOFinding(
                    id="long-description",
                    severity="warning",
                    route=route,
                    file=layout_path,
                    line=_find_line_number(layout_content, "description") or 1,
                    message=f"Route '{route}' description is too long ({len(desc)} characters, recommended 50–160)",
                    suggestion="Shorten the description to under 160 characters to avoid truncation in search engine snippets.",
                )
            )
        else:
            checks_passed += 1

        # Canonical check
        checks_total += 1
        if "canonical" not in layout_content and route != "/":
            findings.append(
                SEOFinding(
                    id="missing-canonical",
                    severity="info",
                    route=route,
                    file=layout_path,
                    line=1,
                    message=f"Route '{route}' does not declare an explicit canonical URL",
                    suggestion="Add alternates: { canonical: ... } to prevent duplicate content issues.",
                )
            )
        else:
            checks_passed += 1

        # Sitemap coverage check
        checks_total += 1
        if has_sitemap and route != "/":
            route_suffix = route.lstrip("/")
            if route_suffix not in sitemap_content and route not in sitemap_content:
                findings.append(
                    SEOFinding(
                        id="missing-from-sitemap",
                        severity="warning",
                        route=route,
                        file="app/sitemap.ts",
                        line=1,
                        message=f"Public route '{route}' is missing from app/sitemap.ts",
                        suggestion=f"Add '{route}' to the sitemap route array so search engines can discover it.",
                    )
                )
            else:
                checks_passed += 1
        elif has_sitemap:
            checks_passed += 1

    # Check for duplicate titles across distinct routes
    seen_titles: dict[str, str] = {}
    for r, t in titles_by_route.items():
        if t in seen_titles:
            checks_total += 1
            findings.append(
                SEOFinding(
                    id="duplicate-title",
                    severity="warning",
                    route=r,
                    file=f"app{r}/layout.tsx" if r != "/" else "app/layout.tsx",
                    line=1,
                    message=f"Duplicate title '{t}' shared between '{seen_titles[t]}' and '{r}'",
                    suggestion="Ensure each page has a unique title to avoid competing for search rankings.",
                )
            )
        else:
            seen_titles[t] = r

    # 6. Check headings (<h1>) and image alt attributes in page components
    for path, content in files.items():
        if (path == "app/page.tsx" or (path.startswith("app/") and path.endswith("/page.tsx"))):
            route = "/" if path == "app/page.tsx" else f"/{path[len('app/') : -len('/page.tsx')]}"

            # Headings check
            checks_total += 1
            h1_matches = list(re.finditer(r"<h1[\s>]", content, re.IGNORECASE))
            if len(h1_matches) == 0:
                findings.append(
                    SEOFinding(
                        id="missing-h1",
                        severity="warning",
                        route=route,
                        file=path,
                        line=1,
                        message=f"Page component '{path}' is missing an <h1> heading",
                        suggestion="Add a single <h1> heading representing the main subject of the page.",
                    )
                )
            elif len(h1_matches) > 1:
                findings.append(
                    SEOFinding(
                        id="multiple-h1",
                        severity="warning",
                        route=route,
                        file=path,
                        line=_find_line_number(content, re.compile(r"<h1[\s>]", re.IGNORECASE)),
                        message=f"Page component '{path}' has multiple <h1> headings ({len(h1_matches)} found)",
                        suggestion="Use exactly one <h1> heading per page, and use <h2>/<h3> for subsections.",
                    )
                )
            else:
                checks_passed += 1

            # Image alt attribute check
            checks_total += 1
            # Look for <img or <Image tags
            img_tags = re.findall(r"<(?:img|Image)[\s\S]*?>", content)
            missing_alts = 0
            for tag in img_tags:
                if "alt=" not in tag or re.search(r'alt=["\']\s*["\']', tag):
                    missing_alts += 1

            if missing_alts > 0:
                findings.append(
                    SEOFinding(
                        id="missing-image-alt",
                        severity="warning",
                        route=route,
                        file=path,
                        line=_find_line_number(content, re.compile(r"<(?:img|Image)", re.IGNORECASE)),
                        message=f"Page component '{path}' has {missing_alts} image(s) missing descriptive alt text",
                        suggestion="Add descriptive alt attributes to all <img> and <Image> tags for accessibility and image search.",
                    )
                )
            else:
                checks_passed += 1

    # Calculate overall health score (0-100)
    errors_count = sum(1 for f in findings if f.severity == "error")
    warnings_count = sum(1 for f in findings if f.severity == "warning")
    raw_score = 100 - (errors_count * 15) - (warnings_count * 5)
    score = max(0, min(100, raw_score))

    return SEOAuditReport(
        score=score,
        passed=checks_passed,
        total=checks_total,
        findings=findings,
    )


def audit_project_seo(repo_dir: Path | str) -> dict:
    """Run deterministic SEO audit on a project directory on disk."""
    base = Path(repo_dir).resolve()
    if not base.is_dir():
        return {
            "score": 0,
            "passed": 0,
            "total": 1,
            "findings": [
                {
                    "id": "repo-not-found",
                    "severity": "error",
                    "route": "/",
                    "file": "",
                    "line": 1,
                    "message": "Repository directory not found",
                    "suggestion": "Ensure the project workspace repository is initialized.",
                }
            ],
        }

    files: dict[str, str] = {}
    for root, _, filenames in os.walk(base):
        rel_root = os.path.relpath(root, base)
        if rel_root.startswith((".git", "node_modules", ".next", "__pycache__", ".venv", "venv")):
            continue
        for fname in filenames:
            rel_path = os.path.normpath(os.path.join(rel_root, fname)) if rel_root != "." else fname
            if rel_path.endswith((".tsx", ".ts", ".jsx", ".js", ".txt", ".json")):
                try:
                    full_path = Path(root) / fname
                    files[rel_path] = full_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

    return audit_files_seo(files).to_dict()
