"""R-568: the scheduler of a generated FastAPI backend (`app/jobs.py`).

A loop started with the app: every few seconds it turns due schedules into runs, claims runs one at
a time (SKIP LOCKED, so replicas share them) and runs each schedule's statement from `jobs_sql`.
The admin's endpoints list schedules and runs, run a schedule now, pause it, and retry a dead run.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from . import jobs_sql as q

JOBS_ENV_EXAMPLE = (
    "# Scheduled jobs (R-568): how often the scheduler looks for due work; 1 turns it off here\n"
    "# (another replica, or a dedicated worker, runs them instead).\n"
    "SCHEDULER_TICK_SECONDS=\nSCHEDULER_DISABLED=\n"
)


def python_jobs_file(ir: ApplicationIR) -> str:
    compiled = q.compiled_schedules(ir)
    table = "\n".join(
        f"    {c.name!r}: {{\"entity\": {c.entity!r}, \"every_seconds\": {c.every_seconds}, "
        f"\"action\": {c.action!r}, \"description\": {c.description!r},\n"
        f"        \"sql\": {c.sql!r}}},"
        for c in compiled
    )
    p = q.python_placeholders
    return (
        '"""Scheduled jobs (OmniStackAI R-568): rules the app runs on its own, on a clock.\n\n'
        "Each schedule is one bounded statement over its rows. Runs are rows in `scheduler_run`: a failed\n"
        "run is retried with backoff and is dead after its last attempt; an admin can retry it. Rows are\n"
        "claimed with SKIP LOCKED, so several replicas share the work without running it twice.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "import asyncio\n"
        "import logging\n"
        "import os\n"
        "from typing import Any\n\n"
        "from fastapi import APIRouter, Depends, HTTPException\n\n"
        "from app.auth import require_auth, sees_all\n"
        "from app.db import connect\n\n"
        "log = logging.getLogger(\"app.jobs\")\n\n"
        "SCHEDULES: dict[str, dict[str, Any]] = {\n" + table + "\n}\n"
        f"SYNC = {q.sync_statements(ir)!r}\n"
        f"BATCH = {q.BATCH}\n"
        f"MAX_BATCHES = {q.MAX_BATCHES}\n"
        f"ENQUEUE_DUE = {q.ENQUEUE_DUE!r}\n"
        f"CLAIM = {q.CLAIM!r}\n"
        f"MANUAL = {p(q.MANUAL)!r}\n"
        f"DONE = {p(q.DONE)!r}\n"
        f"FAILED = {p(q.FAILED)!r}\n"
        f"RECORD = {p(q.RECORD)!r}\n"
        f"PRUNE = {q.PRUNE!r}\n"
        f"LIST_SCHEDULES = {q.SCHEDULES!r}\n"
        f"RUNS = {q.RUNS!r}\n"
        f"RUNS_WITH_STATUS = {p(q.RUNS_WITH_STATUS)!r}\n"
        f"RETRY = {p(q.RETRY)!r}\n"
        f"PAUSE = {p(q.PAUSE)!r}\n\n"
        "router = APIRouter(tags=[\"jobs\"])\n\n\n"
        + _BODY
    )


_BODY = r'''async def run_schedule(name: str) -> int:
    """Run one schedule's statement until a batch comes back short; the rows it changed."""
    schedule = SCHEDULES.get(name)
    if schedule is None:
        raise LookupError(f"no schedule named {name!r} in this version of the app")
    total = 0
    async with await connect() as conn:
        for _ in range(MAX_BATCHES):
            async with conn.transaction(), conn.cursor() as cur:
                await cur.execute(schedule["sql"])
                changed = cur.rowcount or 0
            total += changed
            if changed < BATCH:
                break
    return total


async def finish(run_id: str, name: str) -> dict[str, Any]:
    """Run a claimed run and record how it went, on the run and on its schedule."""
    try:
        affected = await run_schedule(name)
    except Exception as error:  # noqa: BLE001 - every failure is recorded on the run
        message = f"{type(error).__name__}: {error}"[:500]
        async with await connect() as conn, conn.cursor() as cur:
            await cur.execute(FAILED, (message, run_id))
            status = (await cur.fetchone())["status"]
            await cur.execute(RECORD, (status, None, message, name))
        log.warning("job %s %s: %s", name, status, message)
        return {"status": status, "error": message}
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(DONE, (affected, run_id))
        await cur.execute(RECORD, ("done", affected, None, name))
    return {"status": "done", "affected": affected}


async def tick() -> int:
    """Enqueue what is due and run what is claimable; how many runs this replica ran."""
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(ENQUEUE_DUE)
        await cur.execute(PRUNE)
    ran = 0
    for _ in range(20):
        async with await connect() as conn, conn.cursor() as cur:
            await cur.execute(CLAIM)
            claimed = await cur.fetchone()
        if claimed is None:
            break
        await finish(str(claimed["id"]), claimed["schedule"])
        ran += 1
    return ran


async def sync() -> None:
    """Make the schedule table match this version of the app."""
    async with await connect() as conn, conn.cursor() as cur:
        for statement in SYNC:
            await cur.execute(statement)


_task: asyncio.Task | None = None


async def _loop() -> None:
    interval = max(1.0, float(os.environ.get("SCHEDULER_TICK_SECONDS") or 10))
    synced = False
    while True:
        try:
            if not synced:
                await sync()
                synced = True
            await tick()
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 - the database may not be up yet; try again
            log.warning("scheduler: %s", error)
        await asyncio.sleep(interval)


async def start() -> None:
    global _task
    if os.environ.get("SCHEDULER_DISABLED", "").strip() in ("1", "true", "yes"):
        log.info("scheduler disabled here (SCHEDULER_DISABLED)")
        return
    _task = asyncio.create_task(_loop())


async def stop() -> None:
    if _task is not None:
        _task.cancel()


# --- the admin's view ---------------------------------------------------------------------------

def _admin(claims: dict) -> None:
    if not sees_all(claims, ()):
        raise HTTPException(status_code=403, detail="forbidden")


@router.get("/scheduler/schedules")
async def list_schedules(claims: dict = Depends(require_auth)) -> list[dict]:
    _admin(claims)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(LIST_SCHEDULES)
        rows = {r["name"]: r for r in await cur.fetchall()}
    out = []
    for name, schedule in SCHEDULES.items():
        row = rows.get(name) or {}
        out.append({"name": name, "entity": schedule["entity"], "action": schedule["action"],
                    "description": schedule["description"], "every_seconds": schedule["every_seconds"],
                    **{k: row.get(k) for k in ("paused", "next_run_at", "last_run_at", "last_status",
                                                "last_affected", "last_error")}})
    return out


@router.post("/scheduler/schedules/{name}/run")
async def run_now(name: str, claims: dict = Depends(require_auth)) -> dict:
    _admin(claims)
    if name not in SCHEDULES:
        raise HTTPException(status_code=404, detail="not_found")
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(MANUAL, (name,))
        run = await cur.fetchone()
    result = await finish(str(run["id"]), name)
    return {"id": str(run["id"]), "schedule": name, **result}


async def _pause(name: str, paused: bool) -> dict:
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(PAUSE, (paused, name))
        if await cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="not_found")
    return {"name": name, "paused": paused}


@router.post("/scheduler/schedules/{name}/pause")
async def pause(name: str, claims: dict = Depends(require_auth)) -> dict:
    _admin(claims)
    return await _pause(name, True)


@router.post("/scheduler/schedules/{name}/resume")
async def resume(name: str, claims: dict = Depends(require_auth)) -> dict:
    _admin(claims)
    return await _pause(name, False)


@router.get("/scheduler/runs")
async def list_runs(status: str | None = None, claims: dict = Depends(require_auth)) -> list[dict]:
    _admin(claims)
    async with await connect() as conn, conn.cursor() as cur:
        if status:
            await cur.execute(RUNS_WITH_STATUS, (status,))
        else:
            await cur.execute(RUNS)
        return [{**r, "id": str(r["id"])} for r in await cur.fetchall()]


@router.post("/scheduler/runs/{run_id}/retry")
async def retry(run_id: str, claims: dict = Depends(require_auth)) -> dict:
    """A failed or dead run, queued again with a fresh set of attempts."""
    _admin(claims)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(RETRY, (run_id,))
        row = await cur.fetchone()
    if row is None:
        raise HTTPException(status_code=409, detail="only a failed or dead run can be retried")
    return {**row, "id": str(row["id"])}
'''
