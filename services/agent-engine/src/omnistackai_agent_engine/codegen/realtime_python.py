"""R-569: live updates in a generated FastAPI backend (`app/realtime.py`).

One LISTEN connection per process fans changes out to the open streams. A browser cannot send an
Authorization header on an EventSource, so it first trades its token for a ticket (signed with
JWT_SECRET, valid for a minute) and opens `/realtime/stream?ticket=...`.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from . import realtime_sql as q


def python_realtime_file(ir: ApplicationIR) -> str:
    tables = "\n".join(
        f"    {t.table!r}: {{\"entity\": {t.entity!r}, \"owned\": {t.owned!r}, \"see_all\": {t.see_all!r}, \"strict\": {t.strict!r}}},"
        for t in q.live_tables(ir)
    )
    return (
        '"""Live updates (OmniStackAI R-569): changes to live entities, streamed as they happen.\n\n'
        "A trigger publishes each change on the `app_changes` channel; this process listens once and sends\n"
        "each change to the open streams of the people who may see that record. An event names the entity,\n"
        "the operation and the id - the page fetches the record through the API, as it always does.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "import asyncio\n"
        "import base64\n"
        "import hashlib\n"
        "import hmac\n"
        "import json\n"
        "import logging\n"
        "import time\n"
        "from typing import Any\n\n"
        "from fastapi import APIRouter, Depends, HTTPException, Request\n"
        "from fastapi.responses import StreamingResponse\n\n"
        "from app.auth import _secret, owner_of, require_auth\n"
        "from app.db import connect\n\n"
        "log = logging.getLogger(\"app.realtime\")\n\n"
        f"CHANNEL = {q.CHANNEL!r}\n"
        f"TICKET_SECONDS = {q.TICKET_SECONDS}\n"
        f"PING_SECONDS = {q.PING_SECONDS}\n"
        "LIVE: dict[str, dict[str, Any]] = {\n" + tables + "\n}\n\n"
        "router = APIRouter(tags=[\"realtime\"])\n\n\n"
        + _BODY
    )


_BODY = r'''def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _sign(payload: str) -> str:
    return hmac.new(_secret().encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_ticket(claims: dict, now: float | None = None) -> str:
    roles = claims.get("roles") if isinstance(claims.get("roles"), list) else []
    body = {"sub": owner_of(claims) or "", "roles": [str(r) for r in roles],
            "exp": int((now or time.time()) + TICKET_SECONDS)}
    payload = _b64(json.dumps(body, separators=(",", ":")).encode())
    return f"{payload}.{_sign(payload)}"


def read_ticket(ticket: str, now: float | None = None) -> dict | None:
    """The ticket's holder, or None when it is forged, malformed or more than a minute old."""
    payload, _, signature = (ticket or "").partition(".")
    if not payload or not hmac.compare_digest(signature, _sign(payload)):
        return None
    try:
        body = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except ValueError:
        return None
    if not isinstance(body, dict) or int(body.get("exp", 0)) < (now or time.time()):
        return None
    return body


def may_hear(holder: dict, change: dict) -> bool:
    """Whether this person may learn of this change: the entity is live, and they may see the row."""
    live = LIVE.get(change.get("t"))
    if live is None:
        return False
    if not live["owned"]:
        return True
    me = holder.get("sub")
    if live.get("strict"):  # a notification is its recipient's alone
        return bool(me) and me == change.get("a")
    roles = set(holder.get("roles") or [])
    if roles & (set(live["see_all"]) | {"admin"}):
        return True
    return bool(me) and me in (change.get("o"), change.get("a"))


class _Stream:
    def __init__(self, holder: dict, entities: set[str] | None) -> None:
        self.holder = holder
        self.entities = entities
        self.queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=256)


_streams: set[_Stream] = set()
_task: asyncio.Task | None = None


def _fan_out(raw: str) -> None:
    try:
        change = json.loads(raw)
    except ValueError:
        return
    entity = (LIVE.get(change.get("t")) or {}).get("entity")
    for stream in list(_streams):
        if stream.entities is not None and entity not in stream.entities:
            continue
        if may_hear(stream.holder, change):
            event = {"entity": entity, "op": change.get("op"), "id": change.get("id")}
            try:
                stream.queue.put_nowait(event)
            except asyncio.QueueFull:  # a stream that cannot keep up is closed; its page reconnects
                stream.queue = asyncio.Queue(maxsize=1)
                stream.queue.put_nowait({"close": True})


async def _listen() -> None:
    while True:
        try:
            conn = await connect()
            async with conn:
                await conn.execute(f"LISTEN {CHANNEL}")
                async for note in conn.notifies():
                    _fan_out(note.payload)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 - the database went away; listen again shortly
            log.warning("realtime: %s", error)
            await asyncio.sleep(2)


async def start() -> None:
    global _task
    _task = asyncio.create_task(_listen())


async def stop() -> None:
    if _task is not None:
        _task.cancel()


@router.post("/realtime/ticket")
async def ticket(claims: dict = Depends(require_auth)) -> dict:
    """Trade the bearer token for a one-minute ticket to open the stream with."""
    return {"ticket": make_ticket(claims), "expires_in": TICKET_SECONDS}


@router.get("/realtime/stream")
async def stream(request: Request, ticket: str = "", entities: str = "") -> StreamingResponse:
    holder = read_ticket(ticket)
    if holder is None:
        raise HTTPException(status_code=401, detail="invalid_ticket")
    wanted = {e for e in entities.split(",") if e} or None
    live = _Stream(holder, wanted)

    async def events():
        _streams.add(live)
        try:
            yield "event: ready\ndata: {}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(live.queue.get(), timeout=PING_SECONDS)
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        return
                    yield ": ping\n\n"
                    continue
                if event.get("close"):
                    return
                yield f"event: change\ndata: {json.dumps(event)}\n\n"
        finally:
            _streams.discard(live)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
'''
