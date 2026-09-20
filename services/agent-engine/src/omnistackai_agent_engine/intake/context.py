"""Context assembly and truncation for Knowledge & Skills (F-04 / R-502).

Enforces bounded context injection:
- Hard cap OMNISTACKAI_CONTEXT_MAX_CHARS (default 24 000).
- Order: knowledge first, then skills in order (mentions -> attached -> defaults).
- Truncation from the end, reporting context_truncated: true and tracking cut skills.
- Zero external dependencies (100% Python standard library).
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_CONTEXT_MAX_CHARS = 24_000


def get_context_max_chars() -> int:
    """Read context max characters from environment, falling back to default."""
    raw = os.environ.get("OMNISTACKAI_CONTEXT_MAX_CHARS", "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_CONTEXT_MAX_CHARS


def assemble_context(
    context_dict: dict[str, Any] | None,
    max_chars: int | None = None,
) -> tuple[str, bool, list[str], list[str]]:
    """Assemble formatted markdown context block from project knowledge and skills.

    Returns:
        (formatted_text, context_truncated, active_skills, truncated_skills)
    """
    if not context_dict or not isinstance(context_dict, dict):
        return "", False, [], []

    limit = max_chars if max_chars is not None else get_context_max_chars()
    if limit <= 0:
        return "", False, [], []

    knowledge = str(context_dict.get("knowledge", "") or "").strip()
    skills_raw = context_dict.get("skills", [])
    if not isinstance(skills_raw, list):
        skills_raw = []

    active_skills: list[str] = []
    truncated_skills: list[str] = []
    is_truncated = False

    sections: list[str] = []
    current_len = 0

    # 1. Project Knowledge
    if knowledge:
        k_header = "## Project knowledge\n"
        k_full = f"{k_header}{knowledge}"
        if len(k_full) > limit:
            is_truncated = True
            # Truncate knowledge to fit limit
            truncated_k = k_full[:limit]
            for s in skills_raw:
                if isinstance(s, dict) and s.get("name"):
                    truncated_skills.append(str(s["name"]))
            return truncated_k, is_truncated, active_skills, truncated_skills

        sections.append(k_full)
        current_len = len(k_full)

    # 2. Active Skills
    valid_skills: list[tuple[str, str]] = []
    for s in skills_raw:
        if isinstance(s, dict):
            name = str(s.get("name", "")).strip()
            body = str(s.get("body", "")).strip()
            if name:
                valid_skills.append((name, body))

    if valid_skills:
        skills_header = "## Active skills"
        # Spacing separator before skills section if knowledge is present
        separator = "\n\n" if sections else ""
        header_with_sep = f"{separator}{skills_header}"

        if current_len + len(header_with_sep) > limit:
            is_truncated = True
            for name, _ in valid_skills:
                truncated_skills.append(name)
            final_text = "".join(sections)
            return final_text, is_truncated, active_skills, truncated_skills

        sections.append(header_with_sep)
        current_len += len(header_with_sep)

        for name, body in valid_skills:
            skill_block = f"\n\n### {name}\n{body}" if body else f"\n\n### {name}"
            if current_len + len(skill_block) <= limit:
                sections.append(skill_block)
                current_len += len(skill_block)
                active_skills.append(name)
            else:
                is_truncated = True
                truncated_skills.append(name)
                remaining = limit - current_len
                # If there's enough room for at least the header `\n\n### {name}`, include partial
                prefix = f"\n\n### {name}\n"
                if remaining > len(prefix):
                    partial_body = body[: remaining - len(prefix)]
                    partial_block = f"{prefix}{partial_body}"
                    sections.append(partial_block)
                    current_len += len(partial_block)
                    active_skills.append(name)
                # Mark remaining skills as truncated
                idx = valid_skills.index((name, body))
                for rem_name, _ in valid_skills[idx + 1 :]:
                    truncated_skills.append(rem_name)
                break

    final_text = "".join(sections).strip()
    return final_text, is_truncated, active_skills, truncated_skills
