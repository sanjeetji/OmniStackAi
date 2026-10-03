"""PC-122: the benchmark report a person reads - one table, then each case with its screenshots."""

from __future__ import annotations

from pathlib import Path

PART_NAMES = {"build": "Build", "runs": "Runs", "api": "API", "pages": "Pages", "complete": "Complete",
              "designed": "Designed", "looks": "Looks"}


def _cell(value: float | None) -> str:
    return "-" if value is None else f"{round(100 * value)}%"


def markdown(report: dict, run_dir: Path) -> str:
    comparison = report.get("comparison") or {}
    lines = [
        f"# Benchmark {report['run']}",
        "",
        f"**Mean score {report['mean']}** across {len(report['cases'])} prompts. "
        f"Pages designed by the model: {'yes' if report.get('design') else 'no'}. "
        f"Previewed: {'yes' if report.get('preview') else 'no'}.",
        "",
    ]
    if comparison.get("baseline"):
        lines.append(f"Against {report.get('baseline_run')}: mean {comparison['mean_before']} -> {comparison['mean_now']} "
                     "on the prompts both ran.")
        if comparison["regressions"]:
            lines += ["", "**Regressions** (a case fell by more than 10 points):", ""]
            lines += [f"- {r}" for r in comparison["regressions"]]
        else:
            lines.append("No regressions.")
        lines.append("")
    lines += ["| Case | Score | Change | " + " | ".join(PART_NAMES.values()) + " | Missing |",
              "|---|---|---|" + "---|" * len(PART_NAMES) + "---|"]
    for case in report["cases"]:
        change = (comparison.get("changes") or {}).get(case["id"])
        lines.append(
            f"| {case['id']} | {case['score']} | {'' if change is None else f'{change:+}'} | "
            + " | ".join(_cell(case["parts"].get(k)) for k in PART_NAMES)
            + f" | {'; '.join(case['missing']) or ''} |")
    lines += ["", "A dash is a part that was not measured for that case; it is left out of the score, not counted as 0.", ""]
    for case in report["cases"]:
        lines += [f"## {case['id']} - {case['score']}", "", f"> {case['prompt']}", ""]
        lines.append(f"- Apps: {', '.join(case['apps']) or 'none'}")
        lines.append(f"- Things it stores: {', '.join(case['entities']) or 'none'}")
        lines.append(f"- Building blocks: {', '.join(case['capabilities']) or 'none'}")
        if case.get("endpoints"):
            bad = [f"{p} ({s})" for p, s in case["endpoints"].items() if not 200 <= s < 300]
            lines.append(f"- List endpoints: {len(case['endpoints']) - len(bad)}/{len(case['endpoints'])} answer"
                         + (f"; failing: {', '.join(bad[:8])}" if bad else ""))
        ui = case.get("ui") or {}
        if ui:
            lines.append(f"- UI check: {ui.get('status')}" + (f", {ui.get('failing')} of {ui.get('page_views')} page views with problems"
                                                            if ui.get("page_views") is not None else f" ({ui.get('reason', '')})"))
            for problem in (ui.get("problems") or [])[:3]:
                lines.append(f"  - {problem.get('app')}{problem.get('route')} ({problem.get('device')}): {problem.get('problem')}")
        design = case.get("design") or {}
        if "designed" in design:
            lines.append(f"- Pages: {design['designed']} designed by the model, {design['kept_template']} kept the template")
            reasons: dict[str, int] = {}
            for why in (design.get("kept_because") or {}).values():
                reasons[why] = reasons.get(why, 0) + 1
            for why, count in sorted(reasons.items(), key=lambda kv: -kv[1])[:3]:
                lines.append(f"  - {count} because {why or 'no reason given'}")
        review = case.get("review") or {}
        if review.get("mean") is not None:
            lines.append(f"- Design review: {review['mean']}/10 over {review['scored']} pages"
                         + (f"; below the bar: {', '.join(review['below_bar'][:6])}" if review.get("below_bar") else ""))
            for score, page, why in review.get("worst") or []:
                lines.append(f"  - {page} {score:g}: {why}")
        if case.get("timings"):
            lines.append("- Seconds: " + ", ".join(f"{k} {v}" for k, v in case["timings"].items() if v))
        for error in case.get("errors") or []:
            lines.append(f"- Error: {error}")
        shots = Path(case["repo"]).parent / "logs" / "ui-check" / "shots" if case.get("repo") else None
        if shots and shots.is_dir():
            images = sorted(p for p in shots.iterdir() if p.suffix == ".png")
            desktop = [p for p in images if "desktop" in p.name][:4] or images[:4]
            for image in desktop:
                lines.append(f"\n![{case['id']} {image.stem}]({image.relative_to(run_dir)})")
        lines.append("")
    return "\n".join(lines)
