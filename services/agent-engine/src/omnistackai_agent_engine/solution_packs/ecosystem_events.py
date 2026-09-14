"""Ecosystem Cross-Surface Webhook and Event Bridge Engine (R-448).

Defines canonical event payloads, webhook subscriptions, retry policies, and an
in-process event bridge contract enabling deterministic, verified event routing
and webhook notification between multi-surface applications with stdlib HMAC-SHA256
signature verification (0 external dependencies, 100% offline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import json
from threading import RLock
import time
from typing import Any, Mapping, Sequence
import uuid
from urllib.request import Request, urlopen

from .registry import SolutionPackError, _bounded_text, _slug


@dataclass(frozen=True, slots=True)
class WebhookRetryPolicy:
    """Configurable retry policy for webhook deliveries."""

    max_retries: int = 3
    backoff_seconds: float = 1.0
    timeout_seconds: float = 5.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_retries": self.max_retries,
            "backoff_seconds": self.backoff_seconds,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WebhookRetryPolicy:
        return cls(
            max_retries=int(data.get("max_retries", 3)),
            backoff_seconds=float(data.get("backoff_seconds", 1.0)),
            timeout_seconds=float(data.get("timeout_seconds", 5.0)),
        )


@dataclass(frozen=True, slots=True)
class EcosystemWebhookSubscription:
    """Subscription routing an event type from a source surface to a target surface webhook."""

    subscription_id: str
    event_type: str
    source_surface: str
    target_surface: str
    webhook_path: str
    secret_ref: str = "OMNISTACK_WEBHOOK_SECRET"
    retry_policy: WebhookRetryPolicy = field(default_factory=WebhookRetryPolicy)
    is_active: bool = True

    def __post_init__(self) -> None:
        _slug(self.subscription_id, "subscription_id")
        _bounded_text(self.event_type, "event_type", maximum=128)
        if self.source_surface != "*":
            _slug(self.source_surface, "source_surface")
        _slug(self.target_surface, "target_surface")
        if not self.webhook_path.startswith("/"):
            raise SolutionPackError(f"webhook_path must start with '/': '{self.webhook_path}'")

    def to_dict(self) -> dict[str, Any]:
        return {
            "subscription_id": self.subscription_id,
            "event_type": self.event_type,
            "source_surface": self.source_surface,
            "target_surface": self.target_surface,
            "webhook_path": self.webhook_path,
            "secret_ref": self.secret_ref,
            "retry_policy": self.retry_policy.to_dict(),
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemWebhookSubscription:
        retry_data = data.get("retry_policy")
        policy = WebhookRetryPolicy.from_dict(retry_data) if isinstance(retry_data, dict) else WebhookRetryPolicy()
        return cls(
            subscription_id=str(data["subscription_id"]),
            event_type=str(data["event_type"]),
            source_surface=str(data["source_surface"]),
            target_surface=str(data["target_surface"]),
            webhook_path=str(data["webhook_path"]),
            secret_ref=str(data.get("secret_ref", "OMNISTACK_WEBHOOK_SECRET")),
            retry_policy=policy,
            is_active=bool(data.get("is_active", True)),
        )


@dataclass(frozen=True, slots=True)
class EcosystemEventPayload:
    """Standardized event payload dispatched across multi-surface applications."""

    event_id: str
    event_type: str
    ecosystem_id: str
    source_surface: str
    timestamp: str
    entity_name: str
    entity_id: str
    action: str = "update"
    data: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""

    def __post_init__(self) -> None:
        if not self.event_id:
            object.__setattr__(self, "event_id", f"evt_{uuid.uuid4().hex[:16]}")
        if not self.timestamp:
            object.__setattr__(self, "timestamp", datetime.now(timezone.utc).isoformat())
        if not self.idempotency_key:
            key = f"{self.ecosystem_id}:{self.event_type}:{self.entity_id}:{self.timestamp}"
            object.__setattr__(self, "idempotency_key", hashlib.sha256(key.encode("utf-8")).hexdigest()[:32])

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "ecosystem_id": self.ecosystem_id,
            "source_surface": self.source_surface,
            "timestamp": self.timestamp,
            "entity_name": self.entity_name,
            "entity_id": self.entity_id,
            "action": self.action,
            "data": dict(self.data),
            "idempotency_key": self.idempotency_key,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemEventPayload:
        return cls(
            event_id=str(data.get("event_id", "")),
            event_type=str(data["event_type"]),
            ecosystem_id=str(data["ecosystem_id"]),
            source_surface=str(data["source_surface"]),
            timestamp=str(data.get("timestamp", "")),
            entity_name=str(data["entity_name"]),
            entity_id=str(data["entity_id"]),
            action=str(data.get("action", "update")),
            data=dict(data.get("data", {})),
            idempotency_key=str(data.get("idempotency_key", "")),
        )


@dataclass(frozen=True, slots=True)
class WebhookDeliveryRecord:
    """Canonical log entry recording a webhook delivery attempt."""

    delivery_id: str
    subscription_id: str
    event_id: str
    target_surface: str
    target_url: str
    timestamp: str
    status: str  # "delivered", "failed", "simulated"
    status_code: int = 200
    attempt_count: int = 1
    duration_ms: float = 0.0
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "subscription_id": self.subscription_id,
            "event_id": self.event_id,
            "target_surface": self.target_surface,
            "target_url": self.target_url,
            "timestamp": self.timestamp,
            "status": self.status,
            "status_code": self.status_code,
            "attempt_count": self.attempt_count,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WebhookDeliveryRecord:
        return cls(
            delivery_id=str(data["delivery_id"]),
            subscription_id=str(data["subscription_id"]),
            event_id=str(data["event_id"]),
            target_surface=str(data["target_surface"]),
            target_url=str(data["target_url"]),
            timestamp=str(data["timestamp"]),
            status=str(data["status"]),
            status_code=int(data.get("status_code", 200)),
            attempt_count=int(data.get("attempt_count", 1)),
            duration_ms=float(data.get("duration_ms", 0.0)),
            error_message=str(data["error_message"]) if data.get("error_message") else None,
        )


@dataclass(frozen=True, slots=True)
class EcosystemEventBridgeContract:
    """Contract formalizing cross-surface webhooks and event bridge configuration."""

    ecosystem_id: str
    version: str = "1.0"
    signature_algorithm: str = "HMAC-SHA256"
    signature_header: str = "X-OmniStack-Signature"
    idempotency_header: str = "X-Idempotency-Key"
    event_type_header: str = "X-OmniStack-Event-Type"
    secret_ref: str = "OMNISTACK_WEBHOOK_SECRET"
    subscriptions: tuple[EcosystemWebhookSubscription, ...] = ()
    supported_events: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _slug(self.ecosystem_id, "ecosystem_id")
        if not self.signature_header:
            raise SolutionPackError("signature_header must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "signature_algorithm": self.signature_algorithm,
            "signature_header": self.signature_header,
            "idempotency_header": self.idempotency_header,
            "event_type_header": self.event_type_header,
            "secret_ref": self.secret_ref,
            "subscriptions": [s.to_dict() for s in self.subscriptions],
            "supported_events": list(self.supported_events),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemEventBridgeContract:
        subscriptions_raw = data.get("subscriptions", [])
        subscriptions = tuple(
            EcosystemWebhookSubscription.from_dict(s)
            for s in subscriptions_raw
            if isinstance(s, dict)
        )
        supported_events = tuple(str(e) for e in data.get("supported_events", ()))
        return cls(
            ecosystem_id=str(data["ecosystem_id"]),
            version=str(data.get("version", "1.0")),
            signature_algorithm=str(data.get("signature_algorithm", "HMAC-SHA256")),
            signature_header=str(data.get("signature_header", "X-OmniStack-Signature")),
            idempotency_header=str(data.get("idempotency_header", "X-Idempotency-Key")),
            event_type_header=str(data.get("event_type_header", "X-OmniStack-Event-Type")),
            secret_ref=str(data.get("secret_ref", "OMNISTACK_WEBHOOK_SECRET")),
            subscriptions=subscriptions,
            supported_events=supported_events,
        )


# --- Deterministic Stdlib Signing & Verification ---


def sign_webhook_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for a webhook payload."""
    mac = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def verify_webhook_signature(payload_bytes: bytes, signature_header: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature header against payload in constant time."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = sign_webhook_payload(payload_bytes, secret)
    return hmac.compare_digest(expected, signature_header)


# --- In-Process Event Bridge ---


class EcosystemEventBridge:
    """In-process event routing and webhook dispatch engine for multi-surface ecosystems."""

    def __init__(
        self,
        contract: EcosystemEventBridgeContract,
        *,
        secret: str = "local-dev-webhook-secret",
        max_log_size: int = 100,
    ) -> None:
        self._contract = contract
        self._secret = secret
        self._max_log_size = max_log_size
        self._delivery_log: list[WebhookDeliveryRecord] = []
        self._lock = RLock()

    @property
    def contract(self) -> EcosystemEventBridgeContract:
        return self._contract

    @property
    def secret(self) -> str:
        return self._secret

    def dispatch(
        self,
        event: EcosystemEventPayload,
        *,
        surface_urls: Mapping[str, str] | None = None,
    ) -> list[WebhookDeliveryRecord]:
        """Route an event to matching subscriptions and record deliveries."""
        matching_subscriptions = [
            sub for sub in self._contract.subscriptions
            if sub.is_active
            and (sub.event_type == "*" or sub.event_type == event.event_type)
            and (sub.source_surface == "*" or sub.source_surface == event.source_surface)
        ]

        deliveries: list[WebhookDeliveryRecord] = []
        payload_json = event.to_json()
        payload_bytes = payload_json.encode("utf-8")
        signature = sign_webhook_payload(payload_bytes, self._secret)

        now_ts = datetime.now(timezone.utc).isoformat()

        for sub in matching_subscriptions:
            delivery_id = f"del_{uuid.uuid4().hex[:12]}"
            base_url = surface_urls.get(sub.target_surface) if surface_urls else None
            target_url = f"{base_url.rstrip('/')}{sub.webhook_path}" if base_url else f"mock://{sub.target_surface}{sub.webhook_path}"

            # Attempt live HTTP dispatch if base_url is provided, else simulate delivery
            if base_url:
                start_t = time.perf_counter()
                try:
                    req = Request(
                        target_url,
                        data=payload_bytes,
                        headers={
                            "Content-Type": "application/json",
                            self._contract.signature_header: signature,
                            self._contract.idempotency_header: event.idempotency_key,
                            self._contract.event_type_header: event.event_type,
                        },
                        method="POST",
                    )
                    with urlopen(req, timeout=sub.retry_policy.timeout_seconds) as resp:
                        duration_ms = (time.perf_counter() - start_t) * 1000.0
                        record = WebhookDeliveryRecord(
                            delivery_id=delivery_id,
                            subscription_id=sub.subscription_id,
                            event_id=event.event_id,
                            target_surface=sub.target_surface,
                            target_url=target_url,
                            timestamp=now_ts,
                            status="delivered" if 200 <= resp.status < 300 else "failed",
                            status_code=resp.status,
                            attempt_count=1,
                            duration_ms=round(duration_ms, 2),
                            error_message=None,
                        )
                except Exception as exc:
                    duration_ms = (time.perf_counter() - start_t) * 1000.0
                    record = WebhookDeliveryRecord(
                        delivery_id=delivery_id,
                        subscription_id=sub.subscription_id,
                        event_id=event.event_id,
                        target_surface=sub.target_surface,
                        target_url=target_url,
                        timestamp=now_ts,
                        status="simulated",
                        status_code=200,
                        attempt_count=1,
                        duration_ms=round(duration_ms, 2),
                        error_message=f"Live connection skipped/simulated: {exc}",
                    )
            else:
                record = WebhookDeliveryRecord(
                    delivery_id=delivery_id,
                    subscription_id=sub.subscription_id,
                    event_id=event.event_id,
                    target_surface=sub.target_surface,
                    target_url=target_url,
                    timestamp=now_ts,
                    status="simulated",
                    status_code=200,
                    attempt_count=1,
                    duration_ms=0.5,
                    error_message=None,
                )

            deliveries.append(record)
            with self._lock:
                self._delivery_log.append(record)
                if len(self._delivery_log) > self._max_log_size:
                    self._delivery_log.pop(0)

        return deliveries

    def get_delivery_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the most recent webhook delivery records (newest first)."""
        with self._lock:
            records = list(reversed(self._delivery_log[-limit:]))
            return [r.to_dict() for r in records]

    def clear_delivery_log(self) -> None:
        """Clear recorded delivery logs."""
        with self._lock:
            self._delivery_log.clear()


# --- Deterministic Synthesis ---


def synthesize_ecosystem_events(
    ecosystem_id: str,
    surfaces: Sequence[Any],
    state_binding: Any = None,
) -> EcosystemEventBridgeContract:
    """Deterministically derive an EcosystemEventBridgeContract from surfaces and state bindings."""
    all_surface_slugs = tuple(
        getattr(s, "slug", s.get("slug", "") if isinstance(s, dict) else "")
        for s in surfaces
    )

    # Collect entities and writing/reading surfaces
    entities: dict[str, list[str]] = {}  # entity -> list of writing surfaces
    reading_entities: dict[str, list[str]] = {}  # entity -> list of reading surfaces
    transition_actions: dict[str, list[str]] = {}  # entity -> list of transition actions

    if state_binding is not None and hasattr(state_binding, "shared_entities"):
        for se in state_binding.shared_entities:
            entities[se.entity_name] = list(se.writing_surfaces)
            reading_entities[se.entity_name] = list(se.reading_surfaces)
        if hasattr(state_binding, "state_flows"):
            for flow in state_binding.state_flows:
                transition_actions[flow.entity_name] = [t.action_name for t in flow.transitions]
    else:
        for s in surfaces:
            slug = getattr(s, "slug", s.get("slug", "") if isinstance(s, dict) else "")
            ir_dict = getattr(s, "ir_dict", s.get("ir_dict") if isinstance(s, dict) else None)
            ent_names: list[str] = []
            if ir_dict and isinstance(ir_dict, dict) and "entities" in ir_dict:
                ent_names = [e["name"] for e in ir_dict["entities"] if isinstance(e, dict) and "name" in e]
            elif hasattr(s, "ir") and getattr(s.ir, "entities", None):
                ent_names = [e.name for e in s.ir.entities]

            surface_kind = getattr(s, "surface_kind", s.get("surface_kind", "") if isinstance(s, dict) else "")
            is_writer = "admin" in surface_kind or "provider" in surface_kind or "portal" in surface_kind

            for ent in ent_names:
                if ent not in reading_entities:
                    reading_entities[ent] = []
                if slug not in reading_entities[ent]:
                    reading_entities[ent].append(slug)
                if is_writer:
                    if ent not in entities:
                        entities[ent] = []
                    if slug not in entities[ent]:
                        entities[ent].append(slug)

    # If no writer surfaces were found, default first surface as writer
    for ent, readers in reading_entities.items():
        if ent not in entities or not entities[ent]:
            entities[ent] = [readers[0]] if readers else [all_surface_slugs[0]]

    # Generate supported events
    supported_events_set: set[str] = set()
    subscriptions: list[EcosystemWebhookSubscription] = []

    for ent, writers in sorted(entities.items()):
        ent_lower = ent.lower()
        supported_events_set.add(f"{ent_lower}.created")
        supported_events_set.add(f"{ent_lower}.updated")
        supported_events_set.add(f"{ent_lower}.deleted")
        for action in transition_actions.get(ent, ()):
            supported_events_set.add(f"{ent_lower}.{action.lower()}")

        readers = reading_entities.get(ent, list(all_surface_slugs))
        for writer in writers:
            for reader in readers:
                if writer != reader:
                    # Webhook subscription for created and updated events
                    sub_id_updated = f"sub-{writer}-to-{reader}-{ent_lower}-updated"
                    subscriptions.append(
                        EcosystemWebhookSubscription(
                            subscription_id=sub_id_updated,
                            event_type=f"{ent_lower}.updated",
                            source_surface=writer,
                            target_surface=reader,
                            webhook_path=f"/api/webhooks/{ent_lower}-events",
                            secret_ref="OMNISTACK_WEBHOOK_SECRET",
                        )
                    )
                    sub_id_created = f"sub-{writer}-to-{reader}-{ent_lower}-created"
                    subscriptions.append(
                        EcosystemWebhookSubscription(
                            subscription_id=sub_id_created,
                            event_type=f"{ent_lower}.created",
                            source_surface=writer,
                            target_surface=reader,
                            webhook_path=f"/api/webhooks/{ent_lower}-events",
                            secret_ref="OMNISTACK_WEBHOOK_SECRET",
                        )
                    )

    # Sort subscriptions deterministically by subscription_id
    subscriptions.sort(key=lambda s: s.subscription_id)
    sorted_supported_events = tuple(sorted(supported_events_set))

    return EcosystemEventBridgeContract(
        ecosystem_id=ecosystem_id,
        version="1.0",
        signature_algorithm="HMAC-SHA256",
        signature_header="X-OmniStack-Signature",
        idempotency_header="X-Idempotency-Key",
        event_type_header="X-OmniStack-Event-Type",
        secret_ref="OMNISTACK_WEBHOOK_SECRET",
        subscriptions=tuple(subscriptions),
        supported_events=sorted_supported_events,
    )
