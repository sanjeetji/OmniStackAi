"""Background jobs and scheduling (R-568): what an app does on its own, on a clock.

"Cancel unpaid orders after 30 minutes", "mark invoices overdue once the due date passes", "delete
drafts older than 30 days". Each is a *schedule*: which rows of an entity (their state, their age),
how often to look, and what happens to them - a workflow transition, fields set, or the rows deleted.

    {"kind": "jobs", "name": "app_jobs", "config": {"schedules": [
        {"name": "cancel_unpaid_orders", "entity": "Order", "every": "5m",
         "where": {"paid": [false]}, "older_than": {"field": "created_at", "age": "30m"},
         "do": {"transition": "cancel"}}]}}

Three decisions are worth stating.

**A schedule is data, not code.** It compiles to one bounded SQL statement, worked out once by the
platform (`codegen/jobs_sql.py`) and run unchanged by every backend. The model never writes the query,
and a schedule can only touch the rows its conditions name, a batch at a time.

**A transition is the workflow's.** A schedule that cancels an order runs the workflow's `cancel`,
so it moves only orders the workflow allows to be cancelled; it cannot invent a state, and setting
the workflow's own field directly is refused.

**Jobs live in the app's own Postgres.** Runs are rows (`scheduler_run`): retried with backoff when
they fail, dead after the last attempt, retried by an admin. Rows are claimed with `SKIP LOCKED`, so
several API replicas share the work without running it twice. No Redis, no queue service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .errors import InvalidIRError

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]{0,48}$")
_DURATION = re.compile(r"^(\d{1,4})\s*([mhd])$")
_SECONDS = {"m": 60, "h": 3600, "d": 86400}
_UNITS = {"m": "minute", "h": "hour", "d": "day"}

_AT = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
#: PC-117: a weekly schedule's day, Monday first (Postgres's ISO week starts on Monday).
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

MAX_SCHEDULES = 16
MIN_EVERY = 60  # a minute: a schedule is a sweep, not a busy loop
MAX_EVERY = 7 * 86400
MAX_AGE = 365 * 86400
#: Columns every table has whether or not the plan lists them (schema_sql adds them).
AUDIT_FIELDS = ("created_at", "updated_at")
#: The scheduler's own tables and its API prefix; an app's entities and routes must not take them.
RESERVED_TABLES = ("scheduler_schedule", "scheduler_run")
API_PREFIX = "/scheduler"


def seconds(text: str) -> int:
    """'30m' -> 1800. Raises ValueError on anything else."""
    match = _DURATION.match(str(text).strip().lower())
    if not match:
        raise ValueError(f"a duration is a number and m, h or d (30m, 2h, 7d): {text!r}")
    return int(match.group(1)) * _SECONDS[match.group(2)]


def say_duration(text: str) -> str:
    """'30m' -> '30 minutes', '1d' -> 'day' (as in 'every day')."""
    match = _DURATION.match(str(text).strip().lower())
    if not match:
        return str(text)
    count, unit = int(match.group(1)), _UNITS[match.group(2)]
    return unit if count == 1 else f"{count} {unit}s"


Scalar = str | int | float | bool


@dataclass(frozen=True, slots=True)
class Schedule:
    """One rule the app runs on its own."""

    name: str
    entity: str
    every: str
    where: tuple[tuple[str, tuple[Scalar, ...]], ...] = ()
    older_than: tuple[str, str] | None = None  # (field, age); age "0m" means the time has passed
    transition: str | None = None
    set: tuple[tuple[str, Scalar], ...] = ()
    delete: bool = False
    #: PC-117: run at this local time ("02:00") rather than every N from the last run; `every` is then
    #: a whole number of days, and `on` (a weekday) pins a weekly schedule's day.
    at: str | None = None
    on: str | None = None

    def __post_init__(self) -> None:
        if not _IDENTIFIER.match(self.name or ""):
            raise InvalidIRError(f"a schedule's name must be lower_snake_case: {self.name!r}")
        if not self.entity:
            raise InvalidIRError(f"schedule {self.name!r} must name an entity")
        try:
            every = seconds(self.every)
        except ValueError as error:
            raise InvalidIRError(f"schedule {self.name!r}: {error}") from error
        if not MIN_EVERY <= every <= MAX_EVERY:
            raise InvalidIRError(f"schedule {self.name!r} runs every 1m to 7d, not {self.every!r}")
        for name, values in self.where:
            if not _IDENTIFIER.match(name):
                raise InvalidIRError(f"schedule {self.name!r}: where-field must be lower_snake_case: {name!r}")
            if not values or len(values) > 16:
                raise InvalidIRError(f"schedule {self.name!r}: where {name} needs 1 to 16 values")
            for value in values:
                _check_scalar(self.name, name, value)
        if self.older_than is not None:
            column, age = self.older_than
            if not _IDENTIFIER.match(column or ""):
                raise InvalidIRError(f"schedule {self.name!r}: older_than needs a field")
            try:
                if seconds(age) > MAX_AGE:
                    raise InvalidIRError(f"schedule {self.name!r}: an age is at most 365d")
            except ValueError as error:
                raise InvalidIRError(f"schedule {self.name!r}: {error}") from error
        actions = (self.transition is not None) + bool(self.set) + self.delete
        if actions != 1:
            raise InvalidIRError(f"schedule {self.name!r} does one thing: a transition, set or delete")
        if self.transition is not None and not _IDENTIFIER.match(self.transition):
            raise InvalidIRError(f"schedule {self.name!r}: transition must be lower_snake_case")
        if len(self.set) > 8:
            raise InvalidIRError(f"schedule {self.name!r} sets at most 8 fields")
        for name, value in self.set:
            if not _IDENTIFIER.match(name) or name in ("id", *AUDIT_FIELDS, "created_by"):
                raise InvalidIRError(f"schedule {self.name!r} cannot set {name!r}")
            _check_scalar(self.name, name, value)
        if self.at is not None:
            if not _AT.match(self.at):
                raise InvalidIRError(f"schedule {self.name!r}: at is a 24-hour time like 02:00, not {self.at!r}")
            if every % 86400:
                raise InvalidIRError(f"schedule {self.name!r}: a schedule at a time of day runs every whole day(s)")
        if self.on is not None:
            if self.on not in WEEKDAYS:
                raise InvalidIRError(f"schedule {self.name!r}: on is a weekday, not {self.on!r}")
            if self.at is None or every != 7 * 86400:
                raise InvalidIRError(f"schedule {self.name!r}: on (a weekday) needs at and every 7d")
        # A rule over every row of a table, every few minutes, is a mistake waiting to happen.
        if not self.where and self.older_than is None:
            raise InvalidIRError(f"schedule {self.name!r} needs a condition: where or older_than")

    @property
    def every_seconds(self) -> int:
        return seconds(self.every)

    @property
    def at_minutes(self) -> int | None:
        """'02:30' -> 150, minutes after local midnight."""
        if self.at is None:
            return None
        hours, minutes = self.at.split(":")
        return int(hours) * 60 + int(minutes)

    @property
    def on_day(self) -> int | None:
        return WEEKDAYS.index(self.on) if self.on is not None else None

    @property
    def action(self) -> str:
        return "transition" if self.transition is not None else "set" if self.set else "delete"

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name, "entity": self.entity, "every": self.every}
        if self.at is not None:
            out["at"] = self.at
        if self.on is not None:
            out["on"] = self.on
        if self.where:
            out["where"] = {name: list(values) for name, values in self.where}
        if self.older_than is not None:
            out["older_than"] = {"field": self.older_than[0], "age": self.older_than[1]}
        if self.transition is not None:
            out["do"] = {"transition": self.transition}
        elif self.set:
            out["do"] = {"set": dict(self.set)}
        else:
            out["do"] = {"delete": True}
        return out

    @classmethod
    def from_dict(cls, data: Any) -> "Schedule":
        if not isinstance(data, dict):
            raise InvalidIRError("a schedule is an object")
        unknown = set(data) - {"name", "entity", "every", "where", "older_than", "do", "at", "on"}
        if unknown:
            raise InvalidIRError(f"unknown schedule keys: {', '.join(sorted(unknown))}")
        where_raw = data.get("where") or {}
        if not isinstance(where_raw, dict):
            raise InvalidIRError("a schedule's where maps a field to its values")
        where = tuple((str(k), tuple(v if isinstance(v, list) else [v])) for k, v in where_raw.items())
        older = data.get("older_than")
        older_than = None
        if older is not None:
            if not isinstance(older, dict) or set(older) - {"field", "age"}:
                raise InvalidIRError('older_than is {"field": ..., "age": "30m"}')
            older_than = (str(older.get("field") or "created_at"), str(older.get("age") or ""))
        do = data.get("do")
        if not isinstance(do, dict) or len(do) != 1 or next(iter(do)) not in ("transition", "set", "delete"):
            raise InvalidIRError('a schedule\'s do is one of {"transition": ...}, {"set": {...}}, {"delete": true}')
        transition, sets, delete = None, (), False
        if "transition" in do:
            transition = str(do["transition"])
        elif "set" in do:
            if not isinstance(do["set"], dict) or not do["set"]:
                raise InvalidIRError("a schedule's set maps fields to values")
            sets = tuple((str(k), v) for k, v in do["set"].items())
        else:
            if do["delete"] is not True:
                raise InvalidIRError('delete is {"delete": true}')
            delete = True
        return cls(
            name=str(data.get("name", "")),
            entity=str(data.get("entity", "")),
            every=str(data.get("every", "")),
            where=where,
            older_than=older_than,
            transition=transition,
            set=sets,
            delete=delete,
            at=str(data["at"]) if data.get("at") else None,
            on=str(data["on"]).lower() if data.get("on") else None,
        )


def _check_scalar(schedule: str, name: str, value: Any) -> None:
    if isinstance(value, str):
        if len(value) > 200:
            raise InvalidIRError(f"schedule {schedule!r}: {name}'s value is too long")
    elif not isinstance(value, (bool, int, float)) or value is None:
        raise InvalidIRError(f"schedule {schedule!r}: {name} takes text, a number or true/false")


@dataclass(frozen=True, slots=True)
class Jobs:
    """An app's schedules (one `jobs` capability per app)."""

    schedules: tuple[Schedule, ...] = field(default_factory=tuple)
    #: PC-117: the time zone a schedule's `at` is in (IANA, e.g. "Asia/Kolkata").
    timezone: str = "UTC"

    def __post_init__(self) -> None:
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(self.timezone)
        except (ValueError, KeyError, OSError) as error:
            raise InvalidIRError(f"unknown time zone {self.timezone!r}") from error
        if not self.schedules:
            raise InvalidIRError("a jobs capability needs at least one schedule")
        if len(self.schedules) > MAX_SCHEDULES:
            raise InvalidIRError(f"an app has at most {MAX_SCHEDULES} schedules")
        names = [s.name for s in self.schedules]
        if len(set(names)) != len(names):
            raise InvalidIRError("schedule names must be unique")

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "Jobs":
        if not isinstance(config, dict):
            raise InvalidIRError("a jobs config must be a mapping")
        unknown = set(config) - {"schedules", "timezone"}
        if unknown:
            raise InvalidIRError(f"unknown jobs keys: {', '.join(sorted(unknown))}")
        raw = config.get("schedules") or []
        if not isinstance(raw, list):
            raise InvalidIRError("jobs schedules must be a list")
        return cls(schedules=tuple(Schedule.from_dict(item) for item in raw),
                   timezone=str(config.get("timezone") or "UTC"))

    def to_config(self) -> dict[str, Any]:
        out: dict[str, Any] = {"schedules": [s.to_dict() for s in self.schedules]}
        if self.timezone != "UTC":
            out["timezone"] = self.timezone
        return out


def validate_jobs_config(name: str, config: dict[str, Any]) -> None:
    try:
        Jobs.from_config(config)
    except (InvalidIRError, ValueError, TypeError) as error:
        raise InvalidIRError(f"jobs {name!r}: {error}") from error


def jobs_of(ir: Any) -> "Jobs | None":
    """The app's schedules (one jobs capability per app), or None."""
    for capability in getattr(ir, "capabilities", ()):
        if capability.kind == "jobs":
            return Jobs.from_config(capability.config)
    return None


def describe(schedule: Schedule, workflow: Any = None, timezone: str = "UTC") -> str:
    """One sentence for the admin: 'Every 5 minutes: cancel Orders where paid is false, 30 minutes after created_at.'"""
    every = say_duration(schedule.every)
    if schedule.on is not None:
        every = f"{schedule.on.title()} at {schedule.at} ({timezone})"
    elif schedule.at is not None:
        every = f"{every} at {schedule.at} ({timezone})"
    noun = f"{schedule.entity}s" if not schedule.entity.endswith("s") else schedule.entity
    if schedule.transition is not None:
        verb = f"{schedule.transition.replace('_', ' ')} {noun}"
    elif schedule.set:
        verb = f"set {', '.join(f'{k} to {_say(v)}' for k, v in schedule.set)} on {noun}"
    else:
        verb = f"delete {noun}"
    parts = []
    for column, values in schedule.where:
        parts.append(f"{column} is {' or '.join(_say(v) for v in values)}")
    if schedule.transition is not None and workflow is not None:
        sources = next((t.sources for t in workflow.transitions if t.name == schedule.transition), ())
        if sources and not any(column == workflow.field for column, _ in schedule.where):
            parts.append(f"{workflow.field} is {' or '.join(sources)}")
    condition = f" where {' and '.join(parts)}" if parts else ""
    if schedule.older_than is not None:
        column, age = schedule.older_than
        condition += (f", once {column} has passed" if seconds(age) == 0
                      else f", {say_duration(age)} after {column}")
    return f"Every {every}: {verb}{condition}."


def _say(value: Scalar) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
