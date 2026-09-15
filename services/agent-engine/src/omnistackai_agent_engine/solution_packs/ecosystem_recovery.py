"""Ecosystem Multi-Surface Disaster Recovery, Snapshot Backup, and Rollback Orchestration (R-454).

Provides canonical backup targets, snapshot manifests, recovery plan steps, rollback triggers,
and a deterministic EcosystemDisasterRecoveryContract derived from ecosystem surfaces. An in-process
thread-safe EcosystemRecoveryEngine simulates disaster recovery exercises, snapshots, and rollbacks offline.

Zero external dependencies — Python 3.13 stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BackupTarget:
    """A backup target definition for a single surface or data store."""

    target_id: str
    surface_slug: str
    target_kind: str  # "database" | "state" | "configuration" | "assets"
    storage_uri: str = ""
    frequency: str = "daily"  # "hourly" | "daily" | "weekly" | "on_demand"
    retention_days: int = 7
    encryption_required: bool = True
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "surface_slug": self.surface_slug,
            "target_kind": self.target_kind,
            "storage_uri": self.storage_uri,
            "frequency": self.frequency,
            "retention_days": self.retention_days,
            "encryption_required": self.encryption_required,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BackupTarget:
        return cls(
            target_id=str(data.get("target_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            target_kind=str(data.get("target_kind", "configuration")),
            storage_uri=str(data.get("storage_uri", "")),
            frequency=str(data.get("frequency", "daily")),
            retention_days=int(data.get("retention_days", 7)),
            encryption_required=bool(data.get("encryption_required", True)),
            tags=tuple(str(t) for t in data.get("tags", ())),
        )


@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    """A point-in-time snapshot manifest capturing a backup state."""

    snapshot_id: str
    ecosystem_id: str
    surface_slug: str
    created_at_utc: str
    checksum_sha256: str
    size_bytes: int = 0
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "ecosystem_id": self.ecosystem_id,
            "surface_slug": self.surface_slug,
            "created_at_utc": self.created_at_utc,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SnapshotManifest:
        raw_meta = data.get("metadata", {})
        meta = {str(k): str(v) for k, v in raw_meta.items()} if isinstance(raw_meta, Mapping) else {}
        return cls(
            snapshot_id=str(data.get("snapshot_id", "")),
            ecosystem_id=str(data.get("ecosystem_id", "")),
            surface_slug=str(data.get("surface_slug", "")),
            created_at_utc=str(data.get("created_at_utc", "")),
            checksum_sha256=str(data.get("checksum_sha256", "")),
            size_bytes=int(data.get("size_bytes", 0)),
            metadata=meta,
        )


@dataclass(frozen=True, slots=True)
class RecoveryStep:
    """One sequential step in an automated multi-surface recovery plan."""

    step_id: str
    sequence_order: int
    surface_slug: str
    action: str  # "quiesce_traffic" | "stop_service" | "restore_data" | "run_migration" | "verify_health" | "resume_traffic"
    target: str = ""
    timeout_seconds: int = 60
    critical: bool = True
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "sequence_order": self.sequence_order,
            "surface_slug": self.surface_slug,
            "action": self.action,
            "target": self.target,
            "timeout_seconds": self.timeout_seconds,
            "critical": self.critical,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RecoveryStep:
        return cls(
            step_id=str(data.get("step_id", "")),
            sequence_order=int(data.get("sequence_order", 0)),
            surface_slug=str(data.get("surface_slug", "")),
            action=str(data.get("action", "")),
            target=str(data.get("target", "")),
            timeout_seconds=int(data.get("timeout_seconds", 60)),
            critical=bool(data.get("critical", True)),
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True, slots=True)
class RollbackTrigger:
    """An automated rollback trigger rule evaluated during or after recovery."""

    trigger_id: str
    condition: str  # "health_probe_failed" | "migration_error" | "timeout_exceeded" | "data_mismatch"
    threshold: str
    action: str  # "revert_to_last_known_good_snapshot" | "rollback_database_migration" | "abort_and_alert"
    severity: str = "critical"  # "critical" | "warning" | "info"

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "condition": self.condition,
            "threshold": self.threshold,
            "action": self.action,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RollbackTrigger:
        return cls(
            trigger_id=str(data.get("trigger_id", "")),
            condition=str(data.get("condition", "")),
            threshold=str(data.get("threshold", "")),
            action=str(data.get("action", "")),
            severity=str(data.get("severity", "critical")),
        )


@dataclass(frozen=True, slots=True)
class EcosystemDisasterRecoveryContract:
    """A complete multi-surface disaster recovery and snapshot backup contract."""

    ecosystem_id: str
    version: str
    backup_targets: tuple[BackupTarget, ...] = ()
    recovery_steps: tuple[RecoveryStep, ...] = ()
    rollback_triggers: tuple[RollbackTrigger, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "backup_targets": [t.to_dict() for t in self.backup_targets],
            "recovery_steps": [s.to_dict() for s in self.recovery_steps],
            "rollback_triggers": [r.to_dict() for r in self.rollback_triggers],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemDisasterRecoveryContract:
        raw_targets = data.get("backup_targets", ())
        targets = tuple(BackupTarget.from_dict(t) for t in raw_targets if isinstance(t, Mapping))

        raw_steps = data.get("recovery_steps", ())
        steps = tuple(RecoveryStep.from_dict(s) for s in raw_steps if isinstance(s, Mapping))

        raw_triggers = data.get("rollback_triggers", ())
        triggers = tuple(RollbackTrigger.from_dict(r) for r in raw_triggers if isinstance(r, Mapping))

        return cls(
            ecosystem_id=str(data.get("ecosystem_id", "")),
            version=str(data.get("version", "1.0.0")),
            backup_targets=targets,
            recovery_steps=steps,
            rollback_triggers=triggers,
        )

    def to_json(self) -> str:
        """Serialize contract to indented JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text: str) -> EcosystemDisasterRecoveryContract:
        """Deserialize contract from JSON string."""
        return cls.from_dict(json.loads(text))

    def digest(self) -> str:
        """Deterministic 64-char hex SHA-256 digest of canonical JSON serialization."""
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Contract Synthesis
# ---------------------------------------------------------------------------


def _surface_kind_from(surface: Any) -> str:
    if isinstance(surface, Mapping):
        return str(surface.get("surface_kind", surface.get("kind", "customer_web")))
    return str(getattr(surface, "surface_kind", getattr(surface, "kind", "customer_web")))


def _surface_slug_from(surface: Any) -> str:
    if isinstance(surface, Mapping):
        return str(surface.get("slug", "surface"))
    return str(getattr(surface, "slug", "surface"))


def synthesize_ecosystem_recovery(
    ecosystem_id: str,
    surfaces: Sequence[Mapping[str, Any]],
    version: str = "1.0.0",
) -> EcosystemDisasterRecoveryContract:
    """Synthesize canonical multi-surface disaster recovery, snapshot backup, and
    rollback triggers.

    Fully deterministic, 100% offline, 0 network or filesystem I/O.
    """
    targets: list[BackupTarget] = []
    steps: list[RecoveryStep] = []
    triggers: list[RollbackTrigger] = []

    has_db = False
    has_api = False
    db_slug = ""
    api_slug = ""

    # 1. Derive Backup Targets
    for s in surfaces:
        slug = _surface_slug_from(s)
        kind = _surface_kind_from(s).lower()

        if kind in ("database", "postgres", "sqlite", "mysql") or "db" in slug:
            has_db = True
            db_slug = slug
            targets.append(
                BackupTarget(
                    target_id=f"target-{slug}-db",
                    surface_slug=slug,
                    target_kind="database",
                    storage_uri=f"snapshots/{ecosystem_id}/{slug}/database.sql.gz",
                    frequency="daily",
                    retention_days=30,
                    encryption_required=True,
                    tags=("database", "critical", "transactional"),
                )
            )
        elif kind in ("api", "api_gateway", "backend", "worker"):
            has_api = True
            api_slug = slug
            targets.append(
                BackupTarget(
                    target_id=f"target-{slug}-state",
                    surface_slug=slug,
                    target_kind="state",
                    storage_uri=f"snapshots/{ecosystem_id}/{slug}/state.json",
                    frequency="hourly",
                    retention_days=14,
                    encryption_required=True,
                    tags=("api", "state"),
                )
            )
        else:
            # Web / Admin / Frontend surfaces
            targets.append(
                BackupTarget(
                    target_id=f"target-{slug}-config",
                    surface_slug=slug,
                    target_kind="configuration",
                    storage_uri=f"snapshots/{ecosystem_id}/{slug}/config.json",
                    frequency="daily",
                    retention_days=7,
                    encryption_required=False,
                    tags=("configuration", slug),
                )
            )

    if not targets:
        # Fallback target for empty or minimal surface set
        targets.append(
            BackupTarget(
                target_id=f"target-{ecosystem_id}-root",
                surface_slug="root",
                target_kind="configuration",
                storage_uri=f"snapshots/{ecosystem_id}/root/manifest.json",
                frequency="daily",
                retention_days=7,
                encryption_required=True,
                tags=("root", "config"),
            )
        )

    # 2. Derive Sequential Recovery Steps
    step_num = 1

    # Step 1: Isolation
    steps.append(
        RecoveryStep(
            step_id="step-drain-traffic",
            sequence_order=step_num,
            surface_slug=api_slug or (targets[0].surface_slug if targets else "system"),
            action="drain_traffic",
            target="ingress_gateway",
            timeout_seconds=30,
            critical=True,
            description="Drain external connections and put gateway in maintenance mode",
        )
    )
    step_num += 1

    # Step 2: Stop application surfaces
    for s in surfaces:
        slug = _surface_slug_from(s)
        kind = _surface_kind_from(s).lower()
        if kind not in ("database", "postgres", "sqlite", "mysql") and "db" not in slug:
            steps.append(
                RecoveryStep(
                    step_id=f"step-stop-{slug}",
                    sequence_order=step_num,
                    surface_slug=slug,
                    action="stop_service",
                    target=slug,
                    timeout_seconds=30,
                    critical=True,
                    description=f"Gracefully stop surface {slug} during snapshot restoration",
                )
            )
            step_num += 1

    # Step 3: Database restoration & migrations
    if has_db:
        steps.append(
            RecoveryStep(
                step_id=f"step-restore-{db_slug}",
                sequence_order=step_num,
                surface_slug=db_slug,
                action="restore_data",
                target=f"snapshots/{ecosystem_id}/{db_slug}/latest.sql.gz",
                timeout_seconds=120,
                critical=True,
                description=f"Restore {db_slug} database storage from verified snapshot",
            )
        )
        step_num += 1

        steps.append(
            RecoveryStep(
                step_id=f"step-migrate-{db_slug}",
                sequence_order=step_num,
                surface_slug=db_slug,
                action="run_migration",
                target="schema",
                timeout_seconds=60,
                critical=True,
                description=f"Execute schema migration and integrity verification on {db_slug}",
            )
        )
        step_num += 1

    # Step 4: Restart services (APIs first, then frontends)
    for s in surfaces:
        slug = _surface_slug_from(s)
        kind = _surface_kind_from(s).lower()
        if kind in ("api", "api_gateway", "backend", "worker"):
            steps.append(
                RecoveryStep(
                    step_id=f"step-start-{slug}",
                    sequence_order=step_num,
                    surface_slug=slug,
                    action="verify_health",
                    target="/healthz",
                    timeout_seconds=30,
                    critical=True,
                    description=f"Start and verify health for backend surface {slug}",
                )
            )
            step_num += 1

    for s in surfaces:
        slug = _surface_slug_from(s)
        kind = _surface_kind_from(s).lower()
        if kind not in ("database", "postgres", "sqlite", "mysql", "api", "api_gateway", "backend", "worker") and "db" not in slug:
            steps.append(
                RecoveryStep(
                    step_id=f"step-start-{slug}",
                    sequence_order=step_num,
                    surface_slug=slug,
                    action="verify_health",
                    target="/",
                    timeout_seconds=20,
                    critical=True,
                    description=f"Start and verify health for frontend surface {slug}",
                )
            )
            step_num += 1

    # Step 5: Resume Traffic
    steps.append(
        RecoveryStep(
            step_id="step-resume-traffic",
            sequence_order=step_num,
            surface_slug="gateway",
            action="resume_traffic",
            target="ingress",
            timeout_seconds=15,
            critical=True,
            description="Re-enable live gateway routing and exit maintenance mode",
        )
    )

    # 3. Derive Rollback Triggers
    triggers.append(
        RollbackTrigger(
            trigger_id="trig-health-failed",
            condition="health_probe_failed",
            threshold="consecutive_failures >= 3",
            action="revert_to_last_known_good_snapshot",
            severity="critical",
        )
    )
    triggers.append(
        RollbackTrigger(
            trigger_id="trig-migration-error",
            condition="migration_error",
            threshold="exit_code != 0",
            action="rollback_database_migration",
            severity="critical",
        )
    )
    triggers.append(
        RollbackTrigger(
            trigger_id="trig-step-timeout",
            condition="timeout_exceeded",
            threshold="elapsed_seconds > step_timeout",
            action="abort_and_alert_oncall",
            severity="warning",
        )
    )

    return EcosystemDisasterRecoveryContract(
        ecosystem_id=ecosystem_id,
        version=version,
        backup_targets=tuple(targets),
        recovery_steps=tuple(steps),
        rollback_triggers=tuple(triggers),
    )


# ---------------------------------------------------------------------------
# Simulation Engine
# ---------------------------------------------------------------------------


@dataclass
class SnapshotResult:
    """Result of simulating snapshot creation for one backup target."""

    snapshot_id: str
    target_id: str
    surface_slug: str
    status: str  # "pass" | "fail"
    checksum_sha256: str
    size_bytes: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "target_id": self.target_id,
            "surface_slug": self.surface_slug,
            "status": self.status,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "message": self.message,
        }


@dataclass
class RecoveryStepResult:
    """Result of evaluating one sequential recovery step."""

    step_id: str
    sequence_order: int
    surface_slug: str
    action: str
    status: str  # "pass" | "fail"
    duration_ms: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "sequence_order": self.sequence_order,
            "surface_slug": self.surface_slug,
            "action": self.action,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "message": self.message,
        }


@dataclass
class RollbackTriggerResult:
    """Result of evaluating one rollback trigger assertion."""

    trigger_id: str
    condition: str
    status: str  # "pass" | "fail"
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "condition": self.condition,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
        }


class EcosystemRecoveryEngine:
    """Thread-safe, in-process, fully deterministic disaster recovery simulation engine.

    Simulates snapshot creation, multi-step recovery sequence execution, and
    rollback trigger evaluations without actual network or filesystem mutations.
    """

    def __init__(self, contract: EcosystemDisasterRecoveryContract) -> None:
        self._contract = contract
        self._lock = threading.Lock()

    @property
    def contract(self) -> EcosystemDisasterRecoveryContract:
        return self._contract

    def simulate_snapshot_creation(self, target_id: str) -> SnapshotResult:
        """Deterministically simulate creating a snapshot for a backup target."""
        with self._lock:
            match = next((t for t in self._contract.backup_targets if t.target_id == target_id), None)
            if not match:
                return SnapshotResult(
                    snapshot_id="",
                    target_id=target_id,
                    surface_slug="unknown",
                    status="fail",
                    checksum_sha256="",
                    size_bytes=0,
                    message=f"[DRY-RUN] Target '{target_id}' not found in recovery contract",
                )

            seed = f"{self._contract.ecosystem_id}:{target_id}:snapshot"
            checksum = hashlib.sha256(seed.encode("utf-8")).hexdigest()
            size = 1048576 if match.target_kind == "database" else 65536

            return SnapshotResult(
                snapshot_id=f"snap-{checksum[:12]}",
                target_id=match.target_id,
                surface_slug=match.surface_slug,
                status="pass",
                checksum_sha256=checksum,
                size_bytes=size,
                message=f"[DRY-RUN] Captured {match.target_kind} snapshot for surface '{match.surface_slug}' ({size} bytes)",
            )

    def simulate_recovery_plan(self) -> list[RecoveryStepResult]:
        """Deterministically simulate executing all recovery plan steps in order."""
        with self._lock:
            results: list[RecoveryStepResult] = []
            for step in self._contract.recovery_steps:
                duration = max(5, step.timeout_seconds * 50)
                results.append(
                    RecoveryStepResult(
                        step_id=step.step_id,
                        sequence_order=step.sequence_order,
                        surface_slug=step.surface_slug,
                        action=step.action,
                        status="pass",
                        duration_ms=duration,
                        message=f"[DRY-RUN] Completed action '{step.action}' on '{step.surface_slug}' in {duration}ms",
                    )
                )
            return results

    def simulate_rollback_triggers(self) -> list[RollbackTriggerResult]:
        """Deterministically evaluate all rollback triggers."""
        with self._lock:
            results: list[RollbackTriggerResult] = []
            for trig in self._contract.rollback_triggers:
                results.append(
                    RollbackTriggerResult(
                        trigger_id=trig.trigger_id,
                        condition=trig.condition,
                        status="pass",
                        severity=trig.severity,
                        message=f"[DRY-RUN] Trigger '{trig.trigger_id}' condition '{trig.condition}' within nominal threshold",
                    )
                )
            return results

    def simulate_full_dr_exercise(self) -> dict[str, Any]:
        """Run a complete dry-run disaster recovery exercise simulation."""
        snapshot_results = [
            self.simulate_snapshot_creation(t.target_id) for t in self._contract.backup_targets
        ]
        step_results = self.simulate_recovery_plan()
        trigger_results = self.simulate_rollback_triggers()

        snap_pass = sum(1 for r in snapshot_results if r.status == "pass")
        snap_fail = sum(1 for r in snapshot_results if r.status == "fail")
        step_pass = sum(1 for r in step_results if r.status == "pass")
        step_fail = sum(1 for r in step_results if r.status == "fail")
        trigger_pass = sum(1 for r in trigger_results if r.status == "pass")
        trigger_fail = sum(1 for r in trigger_results if r.status == "fail")

        overall_status = "pass" if (snap_fail == 0 and step_fail == 0 and trigger_fail == 0) else "fail"

        return {
            "status": overall_status,
            "ecosystem_id": self._contract.ecosystem_id,
            "version": self._contract.version,
            "snapshot_results": [r.to_dict() for r in snapshot_results],
            "recovery_step_results": [r.to_dict() for r in step_results],
            "rollback_trigger_results": [r.to_dict() for r in trigger_results],
            "summary": {
                "overall_status": overall_status,
                "total_backup_targets": len(snapshot_results),
                "snapshots_pass": snap_pass,
                "snapshots_fail": snap_fail,
                "total_recovery_steps": len(step_results),
                "steps_pass": step_pass,
                "steps_fail": step_fail,
                "total_rollback_triggers": len(trigger_results),
                "triggers_pass": trigger_pass,
                "triggers_fail": trigger_fail,
            },
        }
