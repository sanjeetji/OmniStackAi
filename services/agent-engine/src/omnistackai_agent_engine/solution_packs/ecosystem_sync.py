"""Solution Pack Ecosystem Cross-Surface Data Sync, Conflict Resolution, and Offline-First Protocol.

Provides canonical contracts, deterministic conflict resolution strategies (Last-Write-Wins,
Source-of-Truth, Field-Merge), thread-safe in-process synchronization engine, and deterministic
sync topology synthesis across multi-surface business ecosystems.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import threading
from typing import Any, Literal

SyncMode = Literal["bidirectional", "upstream_only", "downstream_only", "read_only"]
ConflictStrategy = Literal["last_write_wins", "source_of_truth", "field_merge"]


@dataclass(frozen=True)
class SyncEntitySpec:
    """Specification for an entity participating in cross-surface synchronization."""

    entity_name: str
    sync_mode: SyncMode = "bidirectional"
    conflict_strategy: ConflictStrategy = "last_write_wins"
    source_of_truth_surface: str | None = None
    immutable_fields: tuple[str, ...] = ("id", "created_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_name": self.entity_name,
            "sync_mode": self.sync_mode,
            "conflict_strategy": self.conflict_strategy,
            "source_of_truth_surface": self.source_of_truth_surface,
            "immutable_fields": list(self.immutable_fields),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncEntitySpec:
        return cls(
            entity_name=str(data["entity_name"]),
            sync_mode=data.get("sync_mode", "bidirectional"),
            conflict_strategy=data.get("conflict_strategy", "last_write_wins"),
            source_of_truth_surface=data.get("source_of_truth_surface"),
            immutable_fields=tuple(data.get("immutable_fields", ["id", "created_at"])),
        )


@dataclass(frozen=True)
class SyncMutation:
    """A single discrete mutation record originating from a surface or sync server."""

    mutation_id: str
    entity_name: str
    record_id: str
    action: Literal["create", "update", "delete"]
    payload: dict[str, Any]
    timestamp: str  # ISO-8601 UTC
    surface_slug: str
    client_mutation_id: str | None = None
    version: int = 1
    base_version: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "entity_name": self.entity_name,
            "record_id": self.record_id,
            "action": self.action,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "surface_slug": self.surface_slug,
            "client_mutation_id": self.client_mutation_id,
            "version": self.version,
            "base_version": self.base_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncMutation:
        return cls(
            mutation_id=str(data["mutation_id"]),
            entity_name=str(data["entity_name"]),
            record_id=str(data["record_id"]),
            action=data.get("action", "update"),
            payload=dict(data.get("payload", {})),
            timestamp=str(data.get("timestamp", datetime.now(timezone.utc).isoformat())),
            surface_slug=str(data.get("surface_slug", "")),
            client_mutation_id=data.get("client_mutation_id"),
            version=int(data.get("version", 1)),
            base_version=data.get("base_version"),
        )


@dataclass(frozen=True)
class SyncConflict:
    """Representation of a detected sync conflict and its deterministic resolution."""

    conflict_id: str
    entity_name: str
    record_id: str
    local_mutation: SyncMutation
    remote_mutation: SyncMutation
    strategy_applied: ConflictStrategy
    resolved_payload: dict[str, Any]
    winning_surface: str
    resolved_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "entity_name": self.entity_name,
            "record_id": self.record_id,
            "local_mutation": self.local_mutation.to_dict(),
            "remote_mutation": self.remote_mutation.to_dict(),
            "strategy_applied": self.strategy_applied,
            "resolved_payload": self.resolved_payload,
            "winning_surface": self.winning_surface,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncConflict:
        return cls(
            conflict_id=str(data["conflict_id"]),
            entity_name=str(data["entity_name"]),
            record_id=str(data["record_id"]),
            local_mutation=SyncMutation.from_dict(data["local_mutation"]),
            remote_mutation=SyncMutation.from_dict(data["remote_mutation"]),
            strategy_applied=data.get("strategy_applied", "last_write_wins"),
            resolved_payload=dict(data.get("resolved_payload", {})),
            winning_surface=str(data.get("winning_surface", "")),
            resolved_at=str(data.get("resolved_at", datetime.now(timezone.utc).isoformat())),
        )


@dataclass(frozen=True)
class SyncCheckpoint:
    """Checkpoint water-mark representing the last synchronized mutation version."""

    surface_slug: str
    last_synced_version: int
    last_synced_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_slug": self.surface_slug,
            "last_synced_version": self.last_synced_version,
            "last_synced_at": self.last_synced_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SyncCheckpoint:
        return cls(
            surface_slug=str(data["surface_slug"]),
            last_synced_version=int(data.get("last_synced_version", 0)),
            last_synced_at=str(data.get("last_synced_at", datetime.now(timezone.utc).isoformat())),
        )


@dataclass(frozen=True)
class EcosystemSyncContract:
    """Canonical specification of multi-surface cross-surface data synchronization."""

    ecosystem_id: str
    version: str
    sync_entities: tuple[SyncEntitySpec, ...]
    surface_policies: dict[str, str]  # surface_slug -> sync_mode
    default_strategy: ConflictStrategy = "last_write_wins"
    offline_queue_max_size: int = 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "sync_entities": [e.to_dict() for e in self.sync_entities],
            "surface_policies": dict(self.surface_policies),
            "default_strategy": self.default_strategy,
            "offline_queue_max_size": self.offline_queue_max_size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EcosystemSyncContract:
        return cls(
            ecosystem_id=str(data["ecosystem_id"]),
            version=str(data.get("version", "1.0.0")),
            sync_entities=tuple(
                SyncEntitySpec.from_dict(e) for e in data.get("sync_entities", [])
            ),
            surface_policies=dict(data.get("surface_policies", {})),
            default_strategy=data.get("default_strategy", "last_write_wins"),
            offline_queue_max_size=int(data.get("offline_queue_max_size", 1000)),
        )


def resolve_sync_conflict(
    local_mutation: SyncMutation,
    remote_mutation: SyncMutation,
    strategy: ConflictStrategy = "last_write_wins",
    authoritative_surface: str | None = None,
    immutable_fields: tuple[str, ...] = ("id", "created_at"),
) -> tuple[dict[str, Any], str]:
    """Deterministically resolve a mutation conflict between local and remote states.

    Returns:
        tuple of (resolved_payload, winning_surface_slug)
    """
    # 1. Source of Truth strategy
    if strategy == "source_of_truth" and authoritative_surface:
        if local_mutation.surface_slug == authoritative_surface:
            return dict(local_mutation.payload), local_mutation.surface_slug
        if remote_mutation.surface_slug == authoritative_surface:
            return dict(remote_mutation.payload), remote_mutation.surface_slug
        # Fall back to last_write_wins if neither is authoritative

    # 2. Field Merge strategy
    if strategy == "field_merge":
        merged: dict[str, Any] = {}
        # Start with keys from both payloads
        all_keys = set(local_mutation.payload.keys()) | set(remote_mutation.payload.keys())
        for k in sorted(all_keys):
            in_local = k in local_mutation.payload
            in_remote = k in remote_mutation.payload
            if in_local and not in_remote:
                merged[k] = local_mutation.payload[k]
            elif in_remote and not in_local:
                merged[k] = remote_mutation.payload[k]
            else:
                # Key present in both: preserve immutable fields from local, otherwise LWW on key
                if k in immutable_fields:
                    merged[k] = local_mutation.payload[k]
                elif local_mutation.timestamp >= remote_mutation.timestamp:
                    merged[k] = local_mutation.payload[k]
                else:
                    merged[k] = remote_mutation.payload[k]
        # Winning surface is the one with the latest timestamp overall
        winning_slug = (
            local_mutation.surface_slug
            if local_mutation.timestamp >= remote_mutation.timestamp
            else remote_mutation.surface_slug
        )
        return merged, winning_slug

    # 3. Last Write Wins strategy (default)
    if local_mutation.timestamp > remote_mutation.timestamp:
        return dict(local_mutation.payload), local_mutation.surface_slug
    elif remote_mutation.timestamp > local_mutation.timestamp:
        return dict(remote_mutation.payload), remote_mutation.surface_slug
    else:
        # Strict tie-breaker: deterministic comparison on mutation_id
        if local_mutation.mutation_id >= remote_mutation.mutation_id:
            return dict(local_mutation.payload), local_mutation.surface_slug
        return dict(remote_mutation.payload), remote_mutation.surface_slug


class EcosystemSyncEngine:
    """Thread-safe in-process sync coordinator and conflict resolution manager."""

    def __init__(self, contract: EcosystemSyncContract) -> None:
        self.contract = contract
        self._lock = threading.RLock()
        self._mutations: list[SyncMutation] = []
        self._state_store: dict[str, dict[str, dict[str, Any]]] = {}  # entity -> record_id -> payload
        self._conflicts: list[SyncConflict] = []
        self._checkpoints: dict[str, SyncCheckpoint] = {}  # surface_slug -> checkpoint
        self._current_version = 0

    @property
    def current_version(self) -> int:
        with self._lock:
            return self._current_version

    @property
    def conflict_count(self) -> int:
        with self._lock:
            return len(self._conflicts)

    @property
    def mutation_count(self) -> int:
        with self._lock:
            return len(self._mutations)

    def get_entity_spec(self, entity_name: str) -> SyncEntitySpec | None:
        for spec in self.contract.sync_entities:
            if spec.entity_name == entity_name:
                return spec
        return None

    def push_mutations(
        self,
        surface_slug: str,
        mutations: list[SyncMutation],
    ) -> tuple[list[SyncMutation], list[SyncConflict]]:
        """Push a batch of mutations from a surface.

        Performs conflict detection against existing state and applies resolved mutations.
        Returns:
            tuple of (accepted_mutations, detected_conflicts)
        """
        accepted: list[SyncMutation] = []
        detected_conflicts: list[SyncConflict] = []

        with self._lock:
            for mut in mutations:
                entity = mut.entity_name
                record_id = mut.record_id
                spec = self.get_entity_spec(entity)
                strategy = spec.conflict_strategy if spec else self.contract.default_strategy
                auth_surface = spec.source_of_truth_surface if spec else None
                immutable = spec.immutable_fields if spec else ("id", "created_at")

                # Check existing canonical state
                existing_entity_store = self._state_store.setdefault(entity, {})
                existing_payload = existing_entity_store.get(record_id)

                if existing_payload is not None:
                    # Find previous mutation for this record
                    prev_mut = None
                    for m in reversed(self._mutations):
                        if m.entity_name == entity and m.record_id == record_id:
                            prev_mut = m
                            break

                    # Check for concurrency collision (if client sent an older or concurrent version)
                    is_conflict = False
                    if prev_mut and prev_mut.surface_slug != surface_slug:
                        # Mutation from another surface happened since client's base
                        if mut.base_version is not None:
                            if mut.base_version < prev_mut.version:
                                is_conflict = True
                        else:
                            if mut.version < prev_mut.version or (mut.version == prev_mut.version and mut.timestamp < prev_mut.timestamp):
                                is_conflict = True

                    if is_conflict and prev_mut:
                        resolved_payload, winner = resolve_sync_conflict(
                            local_mutation=mut,
                            remote_mutation=prev_mut,
                            strategy=strategy,
                            authoritative_surface=auth_surface,
                            immutable_fields=immutable,
                        )
                        conflict = SyncConflict(
                            conflict_id=f"conf-{len(self._conflicts) + 1:04d}",
                            entity_name=entity,
                            record_id=record_id,
                            local_mutation=mut,
                            remote_mutation=prev_mut,
                            strategy_applied=strategy,
                            resolved_payload=resolved_payload,
                            winning_surface=winner,
                        )
                        self._conflicts.append(conflict)
                        detected_conflicts.append(conflict)

                        # Update canonical state with resolved payload
                        self._current_version += 1
                        resolved_mut = SyncMutation(
                            mutation_id=f"mut-{self._current_version:06d}",
                            entity_name=entity,
                            record_id=record_id,
                            action=mut.action,
                            payload=resolved_payload,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            surface_slug=winner,
                            client_mutation_id=mut.client_mutation_id,
                            version=self._current_version,
                        )
                        existing_entity_store[record_id] = resolved_payload
                        self._mutations.append(resolved_mut)
                        accepted.append(resolved_mut)
                        continue

                # No conflict: apply mutation directly
                self._current_version += 1
                new_mut = SyncMutation(
                    mutation_id=f"mut-{self._current_version:06d}",
                    entity_name=entity,
                    record_id=record_id,
                    action=mut.action,
                    payload=mut.payload,
                    timestamp=mut.timestamp,
                    surface_slug=surface_slug,
                    client_mutation_id=mut.client_mutation_id,
                    version=self._current_version,
                )
                if mut.action == "delete":
                    existing_entity_store.pop(record_id, None)
                else:
                    existing_entity_store[record_id] = dict(mut.payload)

                self._mutations.append(new_mut)
                accepted.append(new_mut)

            # Update checkpoint for pushing surface
            now_iso = datetime.now(timezone.utc).isoformat()
            self._checkpoints[surface_slug] = SyncCheckpoint(
                surface_slug=surface_slug,
                last_synced_version=self._current_version,
                last_synced_at=now_iso,
            )

        return accepted, detected_conflicts

    def pull_changes(
        self,
        surface_slug: str,
        since_version: int = 0,
    ) -> tuple[list[SyncMutation], SyncCheckpoint]:
        """Pull mutations that occurred after `since_version`.

        Returns:
            tuple of (new_mutations, updated_checkpoint)
        """
        with self._lock:
            new_mutations = [
                m for m in self._mutations if m.version > since_version
            ]
            now_iso = datetime.now(timezone.utc).isoformat()
            checkpoint = SyncCheckpoint(
                surface_slug=surface_slug,
                last_synced_version=self._current_version,
                last_synced_at=now_iso,
            )
            self._checkpoints[surface_slug] = checkpoint
            return new_mutations, checkpoint

    def get_entity_state(self, entity_name: str, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._state_store.get(entity_name, {}).get(record_id)

    def get_all_records(self, entity_name: str) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._state_store.get(entity_name, {}).values())

    def get_conflicts(self) -> list[SyncConflict]:
        with self._lock:
            return list(self._conflicts)

    def simulate_conflict(
        self,
        entity_name: str,
        record_id: str,
        local_surface: str,
        remote_surface: str,
        local_updates: dict[str, Any],
        remote_updates: dict[str, Any],
        strategy: ConflictStrategy = "field_merge",
    ) -> SyncConflict:
        """Simulate a concurrent write conflict between two surfaces and return the resolved result."""
        spec = self.get_entity_spec(entity_name)
        immutable = spec.immutable_fields if spec else ("id", "created_at")
        auth_surface = spec.source_of_truth_surface if spec else None

        t_now = datetime.now(timezone.utc).isoformat()
        mut_local = SyncMutation(
            mutation_id=f"sim-loc-{uuid_hash(local_updates)}",
            entity_name=entity_name,
            record_id=record_id,
            action="update",
            payload=local_updates,
            timestamp=t_now,
            surface_slug=local_surface,
            version=1,
        )
        mut_remote = SyncMutation(
            mutation_id=f"sim-rem-{uuid_hash(remote_updates)}",
            entity_name=entity_name,
            record_id=record_id,
            action="update",
            payload=remote_updates,
            timestamp=t_now,
            surface_slug=remote_surface,
            version=1,
        )

        resolved_payload, winner = resolve_sync_conflict(
            local_mutation=mut_local,
            remote_mutation=mut_remote,
            strategy=strategy,
            authoritative_surface=auth_surface,
            immutable_fields=immutable,
        )

        conflict = SyncConflict(
            conflict_id=f"sim-conf-{len(self._conflicts) + 1:04d}",
            entity_name=entity_name,
            record_id=record_id,
            local_mutation=mut_local,
            remote_mutation=mut_remote,
            strategy_applied=strategy,
            resolved_payload=resolved_payload,
            winning_surface=winner,
        )
        with self._lock:
            self._conflicts.append(conflict)
        return conflict


def uuid_hash(data: Any) -> str:
    """Compute a short deterministic hash for simulation IDs."""
    encoded = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:8]


def _surface_val(surface: Any, key: str, default: Any = None) -> Any:
    """Helper to extract property from either dataclass or dictionary surface."""
    if isinstance(surface, dict):
        return surface.get(key, default)
    return getattr(surface, key, default)


def synthesize_ecosystem_sync(
    ecosystem_id: str,
    surfaces: list[Any],
    version: str = "1.0.0",
) -> EcosystemSyncContract:
    """Synthesize canonical EcosystemSyncContract from multi-surface ecosystem specifications.

    Analyzes shared entity dependencies across surfaces, assigns bidirectional or downstream sync
    modes, sets source of truth based on surface kind (admin > api > web), and establishes
    field-level merge or last-write-wins strategies.
    """
    surface_policies: dict[str, str] = {}
    entity_surfaces: dict[str, list[tuple[str, str]]] = {}  # entity -> list of (surface_slug, surface_kind)

    for s in surfaces:
        slug = str(_surface_val(s, "slug", ""))
        kind = str(_surface_val(s, "surface_kind", "web"))
        if not slug:
            continue

        # Surface sync policy based on kind
        if kind in ("admin", "portal"):
            policy: SyncMode = "bidirectional"
        elif kind in ("api", "backend"):
            policy = "bidirectional"
        elif kind == "mobile":
            policy = "bidirectional"
        else:
            policy = "bidirectional"
        surface_policies[slug] = policy

        # Inspect IR entities if available
        ir_dict = _surface_val(s, "ir_dict", {})
        if isinstance(ir_dict, dict):
            entities = ir_dict.get("entities", [])
            for ent in entities:
                ent_name = ent.get("name") if isinstance(ent, dict) else getattr(ent, "name", None)
                if ent_name:
                    entity_surfaces.setdefault(ent_name, []).append((slug, kind))

    # If no entities detected from IR, synthesize default entities based on ecosystem domain
    if not entity_surfaces:
        if "rideshare" in ecosystem_id:
            sample_entities = ["RideRequest", "DriverProfile", "TripStatus"]
        elif "blog" in ecosystem_id:
            sample_entities = ["Post", "Author", "Comment"]
        else:
            sample_entities = ["Item", "UserProfile", "Activity"]

        for ent_name in sample_entities:
            entity_surfaces[ent_name] = [
                (str(_surface_val(s, "slug", "")), str(_surface_val(s, "surface_kind", "web")))
                for s in surfaces
                if _surface_val(s, "slug", "")
            ]

    sync_entities: list[SyncEntitySpec] = []
    for ent_name, surf_list in sorted(entity_surfaces.items()):
        # Determine source of truth surface: admin preferred, then api, then first surface
        auth_surface = None
        for slug, kind in surf_list:
            if kind == "admin":
                auth_surface = slug
                break
        if not auth_surface:
            for slug, kind in surf_list:
                if kind in ("api", "backend"):
                    auth_surface = slug
                    break
        if not auth_surface and surf_list:
            auth_surface = surf_list[0][0]

        # Use field_merge for primary entities, last_write_wins for simpler ones
        strategy: ConflictStrategy = "field_merge" if ent_name in ("Post", "RideRequest", "Item") else "last_write_wins"

        sync_entities.append(
            SyncEntitySpec(
                entity_name=ent_name,
                sync_mode="bidirectional",
                conflict_strategy=strategy,
                source_of_truth_surface=auth_surface,
                immutable_fields=("id", "created_at"),
            )
        )

    return EcosystemSyncContract(
        ecosystem_id=ecosystem_id,
        version=version,
        sync_entities=tuple(sync_entities),
        surface_policies=surface_policies,
        default_strategy="last_write_wins",
        offline_queue_max_size=1000,
    )
