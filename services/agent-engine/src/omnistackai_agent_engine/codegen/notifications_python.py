"""PC-053: notifications in a generated FastAPI backend (`app/notifications.py`).

The database writes the notifications (see `notifications_sql.py`); this lists a person's own, marks
them read, keeps their preferences, and sends the emails in the outbox through Resend - or marks them
skipped, with the reason, while the app has no email keys.
"""

from __future__ import annotations

from ..application_ir import ApplicationIR
from . import notifications_sql as q
from .jobs_sql import python_placeholders as p

NOTIFICATIONS_ENV_EXAMPLE = (
    "# Notifications (PC-053): emails go through Resend with RESEND_API_KEY and EMAIL_FROM (above).\n"
    "# EMAIL_API_URL points the sender elsewhere (a test double); NOTIFICATIONS_EMAIL_DISABLED=1 stops it here.\n"
    "EMAIL_API_URL=\nNOTIFICATIONS_EMAIL_DISABLED=\n"
)


def python_notifications_file(ir: ApplicationIR) -> str:
    catalogue = "\n".join(
        f"    {{\"rule\": {r.rule!r}, \"label\": {r.label!r}, \"channels\": {list(r.channels)!r}, \"only_roles\": {list(r.only_roles)!r}}},"
        for r in q.rule_catalogue(ir)
    )
    return (
        '"""Notifications (OmniStackAI PC-053): a person\'s own, their preferences, and the email outbox.\n\n'
        "The database writes each notification (a trigger per entity, a reminder per schedule), leaving out the\n"
        "channels its recipient muted. In-app ones reach the bell live (R-569); emails wait in the outbox here.\n"
        '"""\n'
        "from __future__ import annotations\n\n"
        "import asyncio\n"
        "import json\n"
        "import logging\n"
        "import os\n"
        "import urllib.error\n"
        "import urllib.request\n"
        "from typing import Any\n\n"
        "from fastapi import APIRouter, Depends, HTTPException\n"
        "from pydantic import BaseModel\n\n"
        "from app.auth import owner_of, require_auth\n"
        "from app.db import connect\n\n"
        "log = logging.getLogger(\"app.notifications\")\n\n"
        "RULES: list[dict[str, Any]] = [\n" + catalogue + "\n]\n"
        f"CLAIM_EMAILS = {q.CLAIM_EMAILS!r}\n"
        f"EMAIL_SENT = {p(q.EMAIL_SENT)!r}\n"
        f"EMAIL_SKIPPED = {p(q.EMAIL_SKIPPED)!r}\n"
        f"EMAIL_FAILED = {p(q.EMAIL_FAILED)!r}\n"
        f"INBOX = {p(q.INBOX)!r}\n"
        f"INBOX_UNREAD = {p(q.INBOX_UNREAD)!r}\n"
        f"UNREAD_COUNT = {p(q.UNREAD_COUNT)!r}\n"
        f"MARK_READ = {p(q.MARK_READ)!r}\n"
        f"MARK_ALL_READ = {p(q.MARK_ALL_READ)!r}\n"
        f"MUTES = {p(q.MUTES)!r}\n"
        f"MUTE = {p(q.MUTE)!r}\n"
        f"UNMUTE = {p(q.UNMUTE)!r}\n\n"
        "router = APIRouter(tags=[\"notifications\"])\n\n\n"
        + _BODY
    )


_BODY = r'''def _me(claims: dict) -> str:
    me = owner_of(claims)
    if me is None:  # the development session has no account, so no notifications
        raise HTTPException(status_code=403, detail="sign in with an account")
    return me


def _row(row: dict) -> dict:
    return {**row, "id": str(row["id"]), "record_id": str(row["record_id"]) if row.get("record_id") else None}


@router.get("/notifications")
async def inbox(unread: bool = False, claims: dict = Depends(require_auth)) -> list[dict]:
    me = _me(claims)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(INBOX_UNREAD if unread else INBOX, (me,))
        return [_row(r) for r in await cur.fetchall()]


@router.get("/notifications/unread")
async def unread_count(claims: dict = Depends(require_auth)) -> dict:
    me = _me(claims)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(UNREAD_COUNT, (me,))
        return {"count": int((await cur.fetchone())["count"])}


@router.post("/notifications/read-all")
async def read_all(claims: dict = Depends(require_auth)) -> dict:
    me = _me(claims)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(MARK_ALL_READ, (me,))
        return {"updated": cur.rowcount or 0}


@router.post("/notifications/{notification_id}/read")
async def read_one(notification_id: str, claims: dict = Depends(require_auth)) -> dict:
    me = _me(claims)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(MARK_READ, (notification_id, me))
        if await cur.fetchone() is None:  # not theirs, or no such notification: the same answer
            raise HTTPException(status_code=404, detail="not_found")
    return {"id": notification_id, "read": True}


@router.get("/notifications/preferences")
async def preferences(claims: dict = Depends(require_auth)) -> dict:
    me = _me(claims)
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(MUTES, (me,))
        muted = {(r["rule"], r["channel"]) for r in await cur.fetchall()}
    held = set(claims.get("roles") or [])
    # A rule only for some roles (staff hear of new orders) is not offered to anyone else.
    mine = [rule for rule in RULES if not rule["only_roles"] or held & set(rule["only_roles"])]
    return {
        "all_muted": sorted(channel for rule, channel in muted if rule == "*"),
        "rules": [{"rule": r["rule"], "label": r["label"], "channels": r["channels"],
                   "muted": sorted(c for c in r["channels"] if (r["rule"], c) in muted)} for r in mine],
    }


class PreferenceIn(BaseModel):
    rule: str  # a rule's name, or "*" for every rule
    channel: str  # in_app | email
    muted: bool


@router.put("/notifications/preferences")
async def set_preference(body: PreferenceIn, claims: dict = Depends(require_auth)) -> dict:
    me = _me(claims)
    if body.channel not in ("in_app", "email") or (body.rule != "*" and body.rule not in {r["rule"] for r in RULES}):
        raise HTTPException(status_code=422, detail="unknown rule or channel")
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(MUTE if body.muted else UNMUTE, (me, body.rule, body.channel))
    return {"rule": body.rule, "channel": body.channel, "muted": body.muted}


# --- the email outbox ---------------------------------------------------------------------------

def _send_email(to: str, subject: str, text: str) -> None:
    url = os.environ.get("EMAIL_API_URL") or "https://api.resend.com/emails"
    body = json.dumps({"from": os.environ["EMAIL_FROM"], "to": [to], "subject": subject, "text": text or subject}).encode()
    request = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}", "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status >= 300:
            raise RuntimeError(f"email provider answered {response.status}")


async def send_due_emails() -> int:
    """Send what is due in the outbox; how many were sent."""
    async with await connect() as conn, conn.cursor() as cur:
        await cur.execute(CLAIM_EMAILS)
        due = await cur.fetchall()
    sent = 0
    configured = bool(os.environ.get("RESEND_API_KEY") and os.environ.get("EMAIL_FROM"))
    for row in due:
        async with await connect() as conn, conn.cursor() as cur:
            if not configured:
                await cur.execute(EMAIL_SKIPPED, ("email is not configured (RESEND_API_KEY, EMAIL_FROM)", row["id"]))
                continue
            try:
                await asyncio.to_thread(_send_email, row["email"], row["title"], row["body"])
            except (OSError, RuntimeError, urllib.error.URLError) as error:
                await cur.execute(EMAIL_FAILED, (f"{type(error).__name__}: {error}"[:500], row["id"]))
                log.warning("notification email to user failed: %s", error)
                continue
            await cur.execute(EMAIL_SENT, (row["id"],))
            sent += 1
    return sent


_task: asyncio.Task | None = None


async def _loop() -> None:
    interval = max(1.0, float(os.environ.get("NOTIFICATIONS_EMAIL_SECONDS") or 10))
    while True:
        try:
            await send_due_emails()
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001 - the database may not be up yet; try again
            log.warning("notifications: %s", error)
        await asyncio.sleep(interval)


async def start() -> None:
    global _task
    if os.environ.get("NOTIFICATIONS_EMAIL_DISABLED", "").strip() in ("1", "true", "yes"):
        return
    _task = asyncio.create_task(_loop())


async def stop() -> None:
    if _task is not None:
        _task.cancel()
'''
