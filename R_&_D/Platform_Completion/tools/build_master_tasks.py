"""Build the master task list: OmniStackAI_Master_Tasks.xlsx and MASTER_TASKS.md.

    python3 "R_&_D/Platform_Completion/tools/build_master_tasks.py"

Reads the v6 tracker, CHANGELOG.md and tasks_data.py. A task with a CHANGELOG entry is Completed
whatever tasks_data.py says, so marking work done means writing its CHANGELOG entry and re-running
this. The Markdown is always written; the spreadsheet needs openpyxl (`pip install openpyxl`).
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
RND = FOLDER.parent
REPO = RND.parent
sys.path.insert(0, str(HERE))

import tasks_data as data  # noqa: E402

TRACKER_XLSX = RND / "OmniStackAI_Execution_Tracker_v6.xlsx"
CHANGELOG = REPO / "CHANGELOG.md"
OUT_XLSX = FOLDER / "OmniStackAI_Master_Tasks.xlsx"
OUT_MD = FOLDER / "MASTER_TASKS.md"

STATUS_ORDER = list(data.STATUSES)
PHASE_ORDER = list(data.PHASES)
OPEN = {"In Progress", "Pending", "Not Started"}
LIVE = "Completed - needs live proof"


@dataclass
class Task:
    id: str
    title: str
    source: str
    area: str
    phase: str
    status: str
    priority: str
    tracked_in: str = ""
    done_on: str = ""
    notes: str = ""
    mode: str = ""
    depends: str = ""
    order: int = 0


def natural(task_id: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"(\d+)", task_id))


def read_changelog() -> dict[str, tuple[str, str]]:
    """id -> (date, first sentence). Both entry styles CHANGELOG.md uses are read."""
    done: dict[str, tuple[str, str]] = {}
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(\d{4}-\d{2}-\d{2})\s+([A-Z]+-[\w-]+)\s+(.*)$", line)
        if m:
            done.setdefault(m.group(2), (m.group(1), m.group(3)))
            continue
        m = re.match(r"^## \[([A-Z]+-[\w-]+)\]\s+(.*?)\s+[–-]\s+(\d{4}-\d{2}-\d{2})\s*$", line)
        if m:
            done.setdefault(m.group(1), (m.group(3), m.group(2)))
    return done


def short(text: str, limit: int = 110) -> str:
    text = re.sub(r"`", "", text).strip()
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


def read_tracker() -> dict[str, dict]:
    try:
        import openpyxl
    except ImportError:
        return read_tracker_stdlib()
    wb = openpyxl.load_workbook(TRACKER_XLSX, read_only=True)
    out = {}
    for row in wb["Phase_Roadmap"].iter_rows(values_only=True):
        if isinstance(row[0], str) and re.match(r"^R-\d{3}$", row[0]):
            out[row[0]] = {"area": row[2] or "", "title": row[3] or "", "status": row[7] or ""}
    return out


def read_tracker_stdlib() -> dict[str, dict]:
    """The same read without openpyxl, so the Markdown can be rebuilt on any machine."""
    import xml.etree.ElementTree as ET
    import zipfile

    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    z = zipfile.ZipFile(TRACKER_XLSX)
    shared = [
        "".join(t.text or "" for t in si.iter(ns + "t"))
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(ns + "si")
    ] if "xl/sharedStrings.xml" in z.namelist() else []
    book = ET.fromstring(z.read("xl/workbook.xml"))
    names = [s.get("name") for s in book.iter(ns + "sheet")]
    sheet = f"xl/worksheets/sheet{names.index('Phase_Roadmap') + 1}.xml"
    out = {}
    for r in ET.fromstring(z.read(sheet)).iter(ns + "row"):
        vals = {}
        for c in r.findall(ns + "c"):
            col = re.match(r"[A-Z]+", c.get("r")).group(0)
            v = c.find(ns + "v")
            if v is not None:
                vals[col] = shared[int(v.text)] if c.get("t") == "s" else v.text
            elif c.find(ns + "is") is not None:
                vals[col] = "".join(t.text or "" for t in c.find(ns + "is").iter(ns + "t"))
        rid = vals.get("A", "")
        if re.match(r"^R-\d{3}$", rid):
            out[rid] = {"area": vals.get("C", ""), "title": vals.get("D", ""), "status": vals.get("H", "")}
    return out


def build() -> tuple[list[Task], list[Task]]:
    changelog = read_changelog()
    tracker = read_tracker()

    queue: list[Task] = []
    for order, (tid, title, phase, mode, status, prio, depends, notes) in enumerate(data.QUEUE, 1):
        done = changelog.get(tid)
        queue.append(Task(
            id=tid, title=title, source="Platform_Completion queue", area=mode, phase=phase,
            status="Completed" if done else status, priority=prio, done_on=done[0] if done else "",
            notes=re.sub(r"\s*Covers .*?\.(?=\s|$)", "", notes).strip(), mode=mode, depends=depends,
            order=order,
        ))
    queue_ids = {t.id for t in queue}
    phase_of = {t.id: t.phase for t in queue}
    phase_of.update({t.id: "Delivered" for t in queue if t.status == "Completed"})

    rows: dict[str, Task] = {t.id: t for t in queue}

    def phase_for(status: str, tracked_in: str) -> str:
        if status in ("Completed", "Superseded"):
            return "Delivered"
        if status in ("Deferred", "Dropped"):
            return "Post-launch"
        return phase_of.get(tracked_in, "Post-launch")

    missing = []
    for tid, t in tracker.items():
        if tid in rows:
            continue
        if t["status"] == "Done":
            status, prio, tracked, note = "Completed", "", "", ""
        elif tid in data.TRACKER:
            status, prio, tracked, note = data.TRACKER[tid]
        else:
            missing.append(tid)
            continue
        done = changelog.get(tid)
        if done and status not in ("Superseded", "Dropped"):
            status = LIVE if tid in data.NEEDS_LIVE_PROOF else "Completed"
        rows[tid] = Task(
            id=tid, title=t["title"], source="Execution_Tracker_v6", area=t["area"],
            phase=phase_for(status, tracked), status=status, priority=prio, tracked_in=tracked,
            done_on=done[0] if done else "", notes=note,
        )
    if missing:
        raise SystemExit(f"tracker items with no classification in tasks_data.py: {missing}")

    for tid, (date, text) in changelog.items():
        if tid in rows or not tid.startswith("R-"):
            continue
        status = LIVE if tid in data.NEEDS_LIVE_PROOF else "Completed"
        tracked = data.NEEDS_LIVE_PROOF.get(tid, "")
        rows[tid] = Task(
            id=tid, title=short(text), source="CHANGELOG", area="", phase="Delivered",
            status=status, priority="P0" if status == LIVE else "", tracked_in=tracked,
            done_on=date,
            notes="Built and tested offline; prove it with a real account." if status == LIVE else "",
        )

    # R-532 was delivered but its CHANGELOG line was never written; PROJECT_STATE records it.
    rows.setdefault("R-532", Task(
        id="R-532", title="Bazaar template part 2/4: shared library and storefront (apps/buyer)",
        source="PROJECT_STATE", area="", phase="Delivered", status="Completed", priority="",
        done_on="2026-09-23", notes="Recorded in PROJECT_STATE.md; no CHANGELOG line.",
    ))

    for tid, title, source, status, prio, tracked, note in data.OTHER:
        if tid in changelog:
            status = "Completed"
        rows[tid] = Task(
            id=tid, title=title, source=source, area="", phase=phase_for(status, tracked),
            status=status, priority=prio, tracked_in=tracked, notes=note,
        )

    for t in rows.values():
        if t.tracked_in and t.tracked_in not in rows and t.tracked_in not in queue_ids:
            raise SystemExit(f"{t.id} points at unknown task {t.tracked_in}")
        if t.status not in data.STATUSES:
            raise SystemExit(f"{t.id} has unknown status {t.status!r}")

    everything = sorted(
        rows.values(),
        key=lambda t: (STATUS_ORDER.index(t.status) if t.status not in ("Completed", LIVE) else 99,
                       t.order or 999, natural(t.id)),
    )
    return queue, everything


def covers(queue: list[Task], everything: list[Task]) -> dict[str, str]:
    by: dict[str, list[str]] = {}
    for t in everything:
        if t.tracked_in and t.id != t.tracked_in and t.status not in ("Completed", "Superseded", "Dropped"):
            by.setdefault(t.tracked_in, []).append(t.id)
    return {k: ", ".join(sorted(v, key=natural)) for k, v in by.items()}


# --- Markdown ------------------------------------------------------------------------------------

def md_cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def write_md(queue: list[Task], everything: list[Task]) -> None:
    g = data.GOAL
    cov = covers(queue, everything)
    counts = Counter(t.status for t in everything)
    open_queue = [t for t in queue if t.status in OPEN]
    lines = [
        f"# {g['title']}: master task list",
        "",
        "> Generated by `tools/build_master_tasks.py` from `tools/tasks_data.py`, the v6 tracker and "
        "`CHANGELOG.md`. Do not edit by hand; edit `tasks_data.py` and re-run. The spreadsheet "
        "`OmniStackAI_Master_Tasks.xlsx` holds the same data with filters.",
        "",
        "## Goal", "", g["vision"], "", f"- **{g['vibe']}**", f"- **{g['engineering']}**", "",
        "## Stack policy", "", *[f"- {s}" for s in g["stack"]], "",
        "## Focus rule", "", g["focus_rule"], "",
        "## Where we are", "",
        "| Status | Tasks |", "|---|---|",
        *[f"| {s} | {counts.get(s, 0)} |" for s in STATUS_ORDER],
        f"| **Total** | **{len(everything)}** |", "",
        f"Open work queue: **{len(open_queue)}** tasks "
        f"({', '.join(f'{p}: {sum(1 for t in open_queue if t.priority == p)}' for p in data.PRIORITIES)}).",
        "",
        "## Work queue (do these in order)", "",
        "| # | ID | Task | Status | Priority | Mode | Depends on | Covers | Notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    phase = None
    for t in queue:
        if t.phase != phase:
            phase = t.phase
            lines.append(f"| | | **Phase {phase}**: {md_cell(data.PHASES[phase])} | | | | | | |")
        lines.append(
            f"| {t.order} | {t.id} | {md_cell(t.title)} | {t.status} | {t.priority} | {t.mode} | "
            f"{md_cell(t.depends)} | {cov.get(t.id, '')} | {md_cell(t.notes)} |"
        )
    lines += [
        "", "## Founder decisions", "",
        "| ID | Question | Why | Blocks | Recommendation | Founder answer |", "|---|---|---|---|---|---|",
        *[f"| {d[0]} | {md_cell(d[1])} | {md_cell(d[2])} | {md_cell(d[3])} | {md_cell(d[4])} | {md_cell(d[5])} |"
          for d in data.DECISIONS],
        "", "## Strengthen the weak areas", "", "| Area | Where it is done |", "|---|---|",
        *[f"| {a} | {w} |" for a, w in g["strengthen"]],
        "", "## Every open, deferred and dropped item from R_&_D, and where it is tracked", "",
        "| ID | Task | Source | Status | Priority | Tracked in | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for t in everything:
        if t.source == "Platform_Completion queue" or t.status in ("Completed", LIVE):
            continue
        lines.append(
            f"| {t.id} | {md_cell(t.title)} | {md_cell(t.source)} | {t.status} | {t.priority} | "
            f"{t.tracked_in} | {md_cell(t.notes)} |"
        )
    lines += [
        "", "## Completed", "",
        "| ID | Task | Status | Done on | Notes |", "|---|---|---|---|---|",
    ]
    for t in sorted((t for t in everything if t.status in ("Completed", LIVE)), key=lambda t: natural(t.id)):
        lines.append(f"| {t.id} | {md_cell(t.title)} | {t.status} | {t.done_on} | {md_cell(t.notes)} |")
    lines += ["", "## Legend", "", "| Status | Meaning |", "|---|---|",
              *[f"| {k} | {v} |" for k, v in data.STATUSES.items()],
              "", "| Priority | Meaning |", "|---|---|",
              *[f"| {k} | {v} |" for k, v in data.PRIORITIES.items()], ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


# --- Spreadsheet ---------------------------------------------------------------------------------

FILLS = {
    "Completed": "C6EFCE", LIVE: "E2F0D9", "In Progress": "BDD7EE", "Pending": "FFE699",
    "Not Started": "F8CBAD", "Superseded": "D9D9D9", "Deferred": "EDEDED", "Dropped": "BFBFBF",
}
PRIO_FILLS = {"P0": "FF7C80", "P1": "FFC000", "P2": "9BC2E6", "P3": "D9D9D9"}


def write_xlsx(queue: list[Task], everything: list[Task]) -> bool:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        print("openpyxl is not installed: MASTER_TASKS.md written, spreadsheet skipped.")
        return False

    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F3864")
    wrap = Alignment(wrap_text=True, vertical="top")
    fill = lambda c: PatternFill("solid", fgColor=c)  # noqa: E731

    def table(ws, headers, rows, widths, status_col=None, prio_col=None):
        ws.append(headers)
        for cell in ws[1]:
            cell.font, cell.fill, cell.alignment = head_font, head_fill, wrap
        for r in rows:
            ws.append(r)
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = wrap
            if status_col is not None and row[status_col].value in FILLS:
                row[status_col].fill = fill(FILLS[row[status_col].value])
            if prio_col is not None and row[prio_col].value in PRIO_FILLS:
                row[prio_col].fill = fill(PRIO_FILLS[row[prio_col].value])
        ws.freeze_panes = "C2"
        ws.auto_filter.ref = ws.dimensions
        if status_col is not None and rows:
            dv = DataValidation(type="list", formula1='"' + ",".join(data.STATUSES) + '"')
            ws.add_data_validation(dv)
            col = get_column_letter(status_col + 1)
            dv.add(f"{col}2:{col}{len(rows) + 1}")

    wb = Workbook()
    g = data.GOAL
    ws = wb.active
    ws.title = "Start Here"
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 110
    lines = [
        (g["title"], ""), ("", ""), ("Vision", g["vision"]), ("Vibe Mode", g["vibe"]),
        ("Engineering Mode", g["engineering"]), ("", ""),
        *[("Stack policy" if i == 0 else "", s) for i, s in enumerate(g["stack"])], ("", ""),
        ("Focus rule", g["focus_rule"]), ("", ""),
        ("Strengthen", "Where it is done"), *g["strengthen"], ("", ""),
        ("How to update", "Edit tools/tasks_data.py (or write the task's CHANGELOG entry to mark it "
         "Completed) and run: python3 \"R_&_D/Platform_Completion/tools/build_master_tasks.py\""),
    ]
    for a, b in lines:
        ws.append([a, b])
    ws["A1"].font = Font(bold=True, size=16)
    for row in ws.iter_rows(min_row=2):
        row[0].font = Font(bold=True)
        row[1].alignment = Alignment(wrap_text=True, vertical="top")

    cov = covers(queue, everything)
    table(
        wb.create_sheet("Work Queue"),
        ["#", "ID", "Task", "Phase", "Mode", "Status", "Priority", "Depends on", "Covers", "Notes"],
        [[t.order, t.id, t.title, t.phase, t.mode, t.status, t.priority, t.depends,
          cov.get(t.id, ""), t.notes] for t in queue],
        [5, 13, 60, 22, 12, 16, 9, 22, 30, 60], status_col=5, prio_col=6,
    )
    table(
        wb.create_sheet("All Tasks"),
        ["ID", "Task", "Source", "Area / Mode", "Phase", "Status", "Priority", "Tracked in",
         "Done on", "Notes"],
        [[t.id, t.title, t.source, t.area, t.phase, t.status, t.priority, t.tracked_in, t.done_on,
          t.notes] for t in everything],
        [14, 60, 28, 20, 22, 18, 9, 12, 12, 50], status_col=5, prio_col=6,
    )

    ws = wb.create_sheet("Summary")
    ws.append(["Status", *PHASE_ORDER, "Total"])
    for s in STATUS_ORDER:
        counts = [sum(1 for t in everything if t.status == s and t.phase == p) for p in PHASE_ORDER]
        ws.append([s, *counts, sum(counts)])
    ws.append(["Total", *[sum(1 for t in everything if t.phase == p) for p in PHASE_ORDER],
               len(everything)])
    ws.append([])
    ws.append(["Open queue by priority", *PHASE_ORDER, "Total"])
    for p in data.PRIORITIES:
        counts = [sum(1 for t in queue if t.priority == p and t.status in OPEN and t.phase == ph)
                  for ph in PHASE_ORDER]
        ws.append([p, *counts, sum(counts)])
    for cell in (*ws[1], *ws[len(STATUS_ORDER) + 4]):
        cell.font, cell.fill = head_font, head_fill
    ws.column_dimensions["A"].width = 28
    for i in range(2, len(PHASE_ORDER) + 3):
        ws.column_dimensions[get_column_letter(i)].width = 16

    table(wb.create_sheet("Decisions"),
          ["ID", "Question", "Why it matters", "Blocks", "Recommendation", "Founder answer"],
          [list(d) for d in data.DECISIONS], [6, 50, 40, 22, 50, 40])
    table(wb.create_sheet("Legend"), ["Term", "Meaning"],
          [*data.STATUSES.items(), *data.PRIORITIES.items(), *data.PHASES.items()], [30, 100],
          status_col=0, prio_col=0)
    wb.save(OUT_XLSX)
    return True


def main() -> None:
    queue, everything = build()
    write_md(queue, everything)
    wrote = write_xlsx(queue, everything)
    counts = Counter(t.status for t in everything)
    print(f"{len(everything)} tasks: " + ", ".join(f"{s} {counts[s]}" for s in STATUS_ORDER if counts[s]))
    print(f"wrote {OUT_MD.relative_to(REPO)}" + (f" and {OUT_XLSX.relative_to(REPO)}" if wrote else ""))


if __name__ == "__main__":
    main()
