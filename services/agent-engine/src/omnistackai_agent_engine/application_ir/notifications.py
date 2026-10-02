"""Notifications (PC-053): who hears of what happens to a record, and how.

"Tell the customer when their order ships", "email staff when a new order comes in", "notify the
courier when an order is assigned to them". Each is a *rule*:

    {"kind": "notifications", "name": "app_notifications", "config": {"rules": [
        {"name": "order_shipped", "entity": "Order", "when": {"field": "status", "becomes": "shipped"},
         "to": ["creator"], "title": "Your order is on its way", "body": "Order total: {total_amount}",
         "channels": ["in_app", "email"]}]}}

    when      "created", "changed", "deleted", "assigned" (to someone new), or {"field": ..., "becomes": value}
    to        "creator" (who made the record), "assignee" (its ownership assignee), a uuid field of the
              entity that holds a user's id ("customer_id"), or "role:<role>" (everyone with that role)
    title     text with {field} placeholders from the record; body likewise, optional
    channels  "in_app" (a bell, live through R-569), "email" (an outbox, through Resend) and/or "push" (the
              phone app, through Expo's push service - PC-121)

Reminders ("a day before the appointment") are scheduled jobs (R-568) whose action is to notify.

**The database writes the notifications.** A trigger on the entity inserts one row per recipient, so
a change made by any backend, a scheduled job or a script notifies the same people, and Python, Go
and Node only list them and send the emails.

**Each person decides.** Anyone can mute a rule, or every rule, on a channel; a muted channel is
left out when the notification is written, so nothing is sent and nothing is shown.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .errors import InvalidIRError

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,48}$")
_PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]{0,48})\}")
#: PC-121: "push" reaches the phone app's registered devices through Expo's push service.
CHANNELS = ("in_app", "email", "push")
#: "assigned": the record's ownership assignee (PC-111) became someone new - notify them, not on every change.
EVENTS = ("created", "changed", "deleted", "assigned")
MAX_RULES = 32
#: The notification tables and the API prefix; an app's entities and routes must not take them.
RESERVED_TABLES = ("notification", "notification_mute")
API_PREFIX = "/notifications"


def placeholders(text: str) -> tuple[str, ...]:
    return tuple(_PLACEHOLDER.findall(text or ""))


@dataclass(frozen=True, slots=True)
class Message:
    """Who hears, what they read, where - shared by rules and by reminders (a job's notify)."""

    to: tuple[str, ...]
    title: str
    body: str = ""
    channels: tuple[str, ...] = ("in_app",)

    def check(self, label: str) -> None:
        if not self.to:
            raise InvalidIRError(f"{label} needs someone to notify (to)")
        for who in self.to:
            if who in ("creator", "assignee"):
                continue
            if who.startswith("role:") and _IDENTIFIER.match(who[5:]):
                continue
            if not _IDENTIFIER.match(who):
                raise InvalidIRError(f"{label}: {who!r} is not creator, assignee, a user field or role:<role>")
        if not self.title or len(self.title) > 200:
            raise InvalidIRError(f"{label} needs a title of at most 200 characters")
        if len(self.body) > 2000:
            raise InvalidIRError(f"{label}: a body is at most 2000 characters")
        if not self.channels or any(c not in CHANNELS for c in self.channels) or len(set(self.channels)) != len(self.channels):
            raise InvalidIRError(f"{label}: channels are in_app, email and/or push")

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"to": list(self.to), "title": self.title, "channels": list(self.channels)}
        if self.body:
            out["body"] = self.body
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        to = data.get("to") or []
        channels = data.get("channels") or ["in_app"]
        if isinstance(to, str):
            to = [to]
        if isinstance(channels, str):
            channels = [channels]
        if not isinstance(to, list) or not isinstance(channels, list):
            raise InvalidIRError("to and channels are lists")
        return cls(to=tuple(str(t) for t in to), title=str(data.get("title") or ""),
                   body=str(data.get("body") or ""), channels=tuple(str(c) for c in channels))


@dataclass(frozen=True, slots=True)
class Rule:
    name: str
    entity: str
    when: str  # created | changed | deleted | becomes
    message: Message
    field: str | None = None
    becomes: Any = None

    def __post_init__(self) -> None:
        if not _IDENTIFIER.match(self.name or ""):
            raise InvalidIRError(f"a notification rule's name must be lower_snake_case: {self.name!r}")
        if not self.entity:
            raise InvalidIRError(f"notification {self.name!r} must name an entity")
        if self.when not in (*EVENTS, "becomes"):
            raise InvalidIRError(f"notification {self.name!r}: when is created, changed, deleted, assigned "
                                 "or a field becoming a value")
        if self.when == "becomes":
            if not _IDENTIFIER.match(self.field or ""):
                raise InvalidIRError(f"notification {self.name!r}: becomes needs a field")
            if not isinstance(self.becomes, (str, int, float, bool)):
                raise InvalidIRError(f"notification {self.name!r}: becomes takes text, a number or true/false")
        self.message.check(f"notification {self.name!r}")

    def to_dict(self) -> dict[str, Any]:
        when: Any = {"field": self.field, "becomes": self.becomes} if self.when == "becomes" else self.when
        return {"name": self.name, "entity": self.entity, "when": when, **self.message.to_dict()}

    @classmethod
    def from_dict(cls, data: Any) -> "Rule":
        if not isinstance(data, dict):
            raise InvalidIRError("a notification rule is an object")
        unknown = set(data) - {"name", "entity", "when", "to", "title", "body", "channels"}
        if unknown:
            raise InvalidIRError(f"unknown notification keys: {', '.join(sorted(unknown))}")
        when = data.get("when") or "changed"
        field, becomes = None, None
        if isinstance(when, dict):
            if set(when) != {"field", "becomes"}:
                raise InvalidIRError('when is "created", "changed", "deleted" or {"field": ..., "becomes": ...}')
            field, becomes, when = str(when["field"]), when["becomes"], "becomes"
        return cls(name=str(data.get("name", "")), entity=str(data.get("entity", "")), when=str(when),
                   message=Message.from_dict(data), field=field, becomes=becomes)


@dataclass(frozen=True, slots=True)
class Notifications:
    rules: tuple[Rule, ...] = ()

    def __post_init__(self) -> None:
        if len(self.rules) > MAX_RULES:
            raise InvalidIRError(f"an app has at most {MAX_RULES} notification rules")
        names = [r.name for r in self.rules]
        if len(set(names)) != len(names):
            raise InvalidIRError("notification rule names must be unique")

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Notifications":
        if not isinstance(config, dict):
            raise InvalidIRError("a notifications config must be a mapping")
        unknown = set(config) - {"rules"}
        if unknown:
            raise InvalidIRError(f"unknown notifications keys: {', '.join(sorted(unknown))}")
        raw = config.get("rules") or []
        if not isinstance(raw, list):
            raise InvalidIRError("notification rules must be a list")
        return cls(rules=tuple(Rule.from_dict(r) for r in raw))

    def to_config(self) -> dict[str, Any]:
        return {"rules": [r.to_dict() for r in self.rules]}


def validate_notifications_config(name: str, config: dict[str, Any]) -> None:
    try:
        Notifications.from_config(config)
    except (InvalidIRError, ValueError, TypeError) as error:
        raise InvalidIRError(f"notifications {name!r}: {error}") from error


def notifications_of(ir: Any) -> "Notifications | None":
    """The app's notification rules (one capability per app), or None."""
    for capability in getattr(ir, "capabilities", ()):
        if capability.kind == "notifications":
            return Notifications.from_config(capability.config)
    return None


def has_notifications(ir: Any) -> bool:
    """Whether the app sends any notification - by a rule, or by a reminder (a job's notify)."""
    from .jobs import jobs_of

    rules = notifications_of(ir)
    jobs = jobs_of(ir)
    return bool(rules and rules.rules) or bool(jobs and any(s.notify is not None for s in jobs.schedules))


def uses_push(ir: Any) -> bool:
    """PC-121: whether any rule or reminder pushes to the phone app."""
    from .jobs import jobs_of

    rules = notifications_of(ir)
    jobs = jobs_of(ir)
    messages = [r.message for r in rules.rules] if rules else []
    messages += [s.notify for s in jobs.schedules if s.notify is not None] if jobs else []
    return any("push" in m.channels for m in messages)
