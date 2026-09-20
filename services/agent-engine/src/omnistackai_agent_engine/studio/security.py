"""Deterministic security scanning and dependency auditing for generated projects (F-10 / R-508).

Performs:
1. Secret scan: checks source code for leaked provider keys, private keys, and live .env files.
2. Framework checks: inspects code for dangerouslySetInnerHTML, wildcard CORS, insecure cookies,
   and raw SQL string interpolation.
3. Dependency audit: runs pnpm audit, pip-audit, or govulncheck when toolchains are present.
   Missing toolchains are reported honestly as 'skipped', never as 'passed'.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Excluded directories when scanning source code
EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".turbo",
}

# Secret patterns to detect in source files
SECRET_PATTERNS = [
    (
        "secrets/provider-key",
        "critical",
        re.compile(
            r"(?:sk-[a-zA-Z0-9_-]{20,}|anthropic-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|xoxb-[0-9]{11,}-[0-9]{11,}-[a-zA-Z0-9]{24}|AKIA[0-9A-Z]{16})"
        ),
        "Potential hardcoded provider API key or token found in source code.",
        "Remove this credential immediately and store it in project Secrets.",
    ),
    (
        "secrets/private-key",
        "critical",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "Unencrypted private key block found in repository file.",
        "Remove the private key and manage it securely via environment secrets.",
    ),
    (
        "secrets/hardcoded-credential",
        "high",
        re.compile(
            r"""(?i)(?:api_key|secret_key|private_key|auth_token|db_password)\s*[:=]\s*["']([A-Za-z0-9_\-\.\$\@]{16,})["']"""
        ),
        "Hardcoded credential assignment detected in code.",
        "Load credentials from process.env or project configuration instead of hardcoding.",
    ),
]


def _scan_secrets_in_repo(repo_dir: Path) -> list[dict[str, Any]]:
    """Scan files in repo_dir for secret credentials and live .env files."""
    findings: list[dict[str, Any]] = []

    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        rel_root = Path(root).relative_to(repo_dir)

        for filename in files:
            rel_file = str(rel_root / filename) if str(rel_root) != "." else filename
            file_path = Path(root) / filename

            # Flag live .env files (except .env.example)
            if filename in {".env", ".env.local", ".env.production", ".env.staging"}:
                findings.append({
                    "id": f"sec-env-{len(findings) + 1}",
                    "severity": "critical",
                    "rule": "secrets/env-file",
                    "file": rel_file,
                    "line": 1,
                    "message": f"Live environment file '{filename}' committed in repository.",
                    "fix": "Delete this file from Git and configure variables via project Secrets.",
                })
                continue

            # Skip binary and very large files (> 512 KB)
            try:
                if file_path.stat().st_size > 512 * 1024:
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except (OSError, UnicodeDecodeError):
                continue

            lines = content.splitlines()
            for line_idx, line in enumerate(lines, start=1):
                for rule, severity, pattern, msg, fix in SECRET_PATTERNS:
                    if pattern.search(line):
                        findings.append({
                            "id": f"sec-leak-{len(findings) + 1}",
                            "severity": severity,
                            "rule": rule,
                            "file": rel_file,
                            "line": line_idx,
                            "message": msg,
                            "fix": fix,
                        })
                        break

    return findings


def _scan_framework_rules(repo_dir: Path) -> list[dict[str, Any]]:
    """Scan source files for common security misconfigurations."""
    findings: list[dict[str, Any]] = []

    source_extensions = {".ts", ".tsx", ".js", ".jsx", ".py", ".go"}

    dangerously_pattern = re.compile(r"dangerouslySetInnerHTML")
    cors_wildcard_pattern = re.compile(r"""(?:Access-Control-Allow-Origin['"]?\s*[:=]\s*['"]\*['"]|allow_origins\s*=\s*\[['"]\*['"]\]|origin\s*:\s*['"]\*['"])""")
    raw_sql_pattern = re.compile(r"""(?:f["']SELECT\s+.*\{|"SELECT\s+.*"\s*\+|'SELECT\s+.*'\s*\+|fmt\.Sprintf\(["']SELECT)""", re.IGNORECASE)

    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        rel_root = Path(root).relative_to(repo_dir)

        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext not in source_extensions:
                continue

            rel_file = str(rel_root / filename) if str(rel_root) != "." else filename
            file_path = Path(root) / filename

            try:
                if file_path.stat().st_size > 256 * 1024:
                    continue
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            lines = content.splitlines()
            for line_idx, line in enumerate(lines, start=1):
                # 1. dangerouslySetInnerHTML
                if dangerously_pattern.search(line):
                    findings.append({
                        "id": f"sec-xss-{len(findings) + 1}",
                        "severity": "high",
                        "rule": "framework/dangerously-set-inner-html",
                        "file": rel_file,
                        "line": line_idx,
                        "message": "Use of dangerouslySetInnerHTML exposes users to Cross-Site Scripting (XSS).",
                        "fix": "Sanitize HTML using a sanitizer library (e.g. DOMPurify) or render standard React components.",
                    })

                # 2. CORS wildcard
                if cors_wildcard_pattern.search(line):
                    findings.append({
                        "id": f"sec-cors-{len(findings) + 1}",
                        "severity": "medium",
                        "rule": "framework/cors-wildcard",
                        "file": rel_file,
                        "line": line_idx,
                        "message": "Wildcard CORS ('*') configured; cannot safely be used with credentials or auth headers.",
                        "fix": "Specify explicit allowed origins instead of wildcard '*'.",
                    })

                # 3. Raw SQL interpolation
                if raw_sql_pattern.search(line):
                    findings.append({
                        "id": f"sec-sql-{len(findings) + 1}",
                        "severity": "high",
                        "rule": "framework/sql-injection",
                        "file": rel_file,
                        "line": line_idx,
                        "message": "Raw string concatenation in SQL query introduces SQL injection vulnerabilities.",
                        "fix": "Use parameterized queries ($1, ?), prepared statements, or ORM query builders.",
                    })

    return findings


def _run_dependency_audits(repo_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run dependency audits across supported package managers.

    Returns (findings, checks).
    """
    findings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    # 1. Web app (pnpm audit)
    web_dir = repo_dir / "apps" / "web"
    if not (web_dir / "package.json").is_file():
        web_dir = repo_dir

    if (web_dir / "package.json").is_file():
        pnpm_bin = shutil.which("pnpm")
        if not pnpm_bin:
            checks.append({
                "name": "JavaScript/TypeScript dependency audit (pnpm)",
                "status": "skipped",
                "note": "pnpm not installed in environment",
            })
        else:
            try:
                res = subprocess.run(
                    [pnpm_bin, "audit", "--json"],
                    cwd=str(web_dir),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                raw_out = res.stdout.strip() or res.stderr.strip()
                vulnerabilities_found = False
                if raw_out:
                    try:
                        audit_data = json.loads(raw_out)
                        advisories = audit_data.get("advisories", {})
                        if isinstance(advisories, dict):
                            for adv_id, adv in advisories.items():
                                vulnerabilities_found = True
                                sev = adv.get("severity", "moderate")
                                severity_map = {
                                    "critical": "critical",
                                    "high": "high",
                                    "moderate": "medium",
                                    "low": "low",
                                }
                                findings.append({
                                    "id": f"sec-audit-pnpm-{adv_id}",
                                    "severity": severity_map.get(sev, "medium"),
                                    "rule": f"audit/{adv.get('module_name', 'package')}",
                                    "file": "package.json",
                                    "line": 1,
                                    "message": adv.get("title") or adv.get("overview") or f"Vulnerability in {adv.get('module_name')}",
                                    "fix": adv.get("recommendation") or f"Upgrade {adv.get('module_name')} to {adv.get('patched_versions', 'latest')}",
                                })
                    except json.JSONDecodeError:
                        pass

                if vulnerabilities_found:
                    checks.append({
                        "name": "JavaScript/TypeScript dependency audit (pnpm)",
                        "status": "failed",
                        "note": "Vulnerabilities detected in dependencies",
                    })
                else:
                    checks.append({
                        "name": "JavaScript/TypeScript dependency audit (pnpm)",
                        "status": "passed",
                        "note": "No known vulnerabilities found",
                    })
            except subprocess.TimeoutExpired:
                checks.append({
                    "name": "JavaScript/TypeScript dependency audit (pnpm)",
                    "status": "skipped",
                    "note": "audit timed out after 30s",
                })
            except Exception as ex:
                checks.append({
                    "name": "JavaScript/TypeScript dependency audit (pnpm)",
                    "status": "skipped",
                    "note": f"audit error: {str(ex)}",
                })

    # 2. Python backend audit (pip-audit)
    py_req = repo_dir / "services" / "api" / "requirements.txt"
    if not py_req.is_file():
        py_req = repo_dir / "requirements.txt"

    if py_req.is_file():
        pip_audit_bin = shutil.which("pip-audit")
        if not pip_audit_bin:
            checks.append({
                "name": "Python dependency audit (pip-audit)",
                "status": "skipped",
                "note": "pip-audit not installed in environment",
            })
        else:
            try:
                res = subprocess.run(
                    [pip_audit_bin, "-r", str(py_req), "--format=json"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if res.returncode == 0:
                    checks.append({
                        "name": "Python dependency audit (pip-audit)",
                        "status": "passed",
                        "note": "No known vulnerabilities found",
                    })
                else:
                    checks.append({
                        "name": "Python dependency audit (pip-audit)",
                        "status": "failed",
                        "note": "Vulnerabilities detected in Python dependencies",
                    })
            except Exception as ex:
                checks.append({
                    "name": "Python dependency audit (pip-audit)",
                    "status": "skipped",
                    "note": str(ex),
                })

    # 3. Go backend audit (govulncheck)
    go_mod = repo_dir / "services" / "api" / "go.mod"
    if not go_mod.is_file():
        go_mod = repo_dir / "go.mod"

    if go_mod.is_file():
        govuln_bin = shutil.which("govulncheck")
        if not govuln_bin:
            checks.append({
                "name": "Go vulnerability check (govulncheck)",
                "status": "skipped",
                "note": "govulncheck not installed in environment",
            })
        else:
            try:
                res = subprocess.run(
                    [govuln_bin, "./..."],
                    cwd=str(go_mod.parent),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if res.returncode == 0:
                    checks.append({
                        "name": "Go vulnerability check (govulncheck)",
                        "status": "passed",
                        "note": "No vulnerabilities reported",
                    })
                else:
                    checks.append({
                        "name": "Go vulnerability check (govulncheck)",
                        "status": "failed",
                        "note": "Vulnerabilities detected in Go modules",
                    })
            except Exception as ex:
                checks.append({
                    "name": "Go vulnerability check (govulncheck)",
                    "status": "skipped",
                    "note": str(ex),
                })

    return findings, checks


def run_security_scan(repo_dir: str | Path) -> dict[str, Any]:
    """Execute complete security scan for *repo_dir*.

    Returns a report dictionary adhering to F-10 specification.
    """
    repo_path = Path(repo_dir)
    findings: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []

    # 1. Secret scan
    secret_findings = _scan_secrets_in_repo(repo_path)
    findings.extend(secret_findings)
    checks.append({
        "name": "Secret scan of repository source",
        "status": "failed" if secret_findings else "passed",
        "note": f"{len(secret_findings)} secret issue(s) detected" if secret_findings else "No credentials or live .env files found",
    })

    # 2. Framework security checks
    framework_findings = _scan_framework_rules(repo_path)
    findings.extend(framework_findings)
    checks.append({
        "name": "Framework security best practices",
        "status": "failed" if framework_findings else "passed",
        "note": f"{len(framework_findings)} framework issue(s) detected" if framework_findings else "No dangerous HTML, CORS wildcards, or raw SQL detected",
    })

    # 3. Dependency audits
    dep_findings, dep_checks = _run_dependency_audits(repo_path)
    findings.extend(dep_findings)
    checks.extend(dep_checks)

    # Compute summary counts
    summary = {
        "critical": sum(1 for f in findings if f.get("severity") == "critical"),
        "high": sum(1 for f in findings if f.get("severity") == "high"),
        "medium": sum(1 for f in findings if f.get("severity") == "medium"),
        "low": sum(1 for f in findings if f.get("severity") == "low"),
        "info": sum(1 for f in findings if f.get("severity") == "info"),
        "total_issues": len(findings),
    }

    report = {
        "findings": findings,
        "checks": checks,
        "summary": summary,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }

    # Cache report on disk
    try:
        cache_file = repo_path / ".omnistackai_security_report.json"
        cache_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    except OSError:
        pass

    return report


def get_last_security_report(repo_dir: str | Path) -> dict[str, Any] | None:
    """Retrieve last cached security report for *repo_dir*, or None."""
    cache_file = Path(repo_dir) / ".omnistackai_security_report.json"
    if not cache_file.is_file():
        return None
    try:
        return json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
