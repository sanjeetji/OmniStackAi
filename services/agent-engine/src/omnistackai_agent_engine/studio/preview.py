"""Managed trusted-local preview composition for the OmniStackAI Studio (R-421/R-422/R-446).

The coordinator owns managed ``LocalAppSession`` instances. Process execution remains behind the
platform-owned local-run boundary and is enabled only by the explicit Studio preview command.
Previews use automatically allocated, collision-free ports (R-422). Supports single-app preview
and multi-surface ecosystem preview orchestration (R-446) with on-demand surface switching,
independent process management, and bounded status/stop/restart controls.
"""

from __future__ import annotations

from threading import RLock
from typing import Any, Callable, Mapping

from ..localrun import LocalAppSession, start_preview_app
from ..solution_packs.ecosystem_auth import (
    CrossAppAuthMatrix,
    EcosystemAuthContract,
    generate_surface_tokens,
    synthesize_ecosystem_auth,
)
from ..solution_packs.ecosystem_deployment import (
    EcosystemDeploymentManifest,
    EcosystemLiveGateway,
    synthesize_ecosystem_deployment,
)
from ..solution_packs.ecosystem_events import (
    EcosystemEventBridge,
    EcosystemEventBridgeContract,
    EcosystemEventPayload,
    synthesize_ecosystem_events,
)
from ..solution_packs.ecosystem_state import (
    EcosystemStateBinding,
    synthesize_ecosystem_state,
)
from ..solution_packs.ecosystem_telemetry import (
    EcosystemTelemetryContract,
    EcosystemTelemetryCollector,
    synthesize_ecosystem_telemetry,
)
from ..solution_packs.ecosystem_sync import (
    EcosystemSyncContract,
    EcosystemSyncEngine,
    SyncMutation,
    synthesize_ecosystem_sync,
)
from ..solution_packs.ecosystem_cicd import (
    EcosystemCICDContract,
    EcosystemCICDEngine,
    synthesize_ecosystem_cicd,
    to_workflow_yaml,
)
from ..solution_packs.ecosystem_verification import (
    EcosystemVerificationContract,
    EcosystemVerificationEngine,
    synthesize_ecosystem_verification,
)
from ..solution_packs.ecosystem_recovery import (
    EcosystemDisasterRecoveryContract,
    EcosystemRecoveryEngine,
    synthesize_ecosystem_recovery,
)
from ..solution_packs.ecosystem_capacity import (
    EcosystemCapacityContract,
    EcosystemCapacityEngine,
    synthesize_ecosystem_capacity,
)
from ..solution_packs.ecosystem_alerting import (
    EcosystemAlertingContract,
    EcosystemAlertingEngine,
    synthesize_ecosystem_alerting,
)
from ..solution_packs.ecosystem_sla import (
    EcosystemSLAContract,
    EcosystemSLAEngine,
    synthesize_ecosystem_sla,
)

StartFn = Callable[..., LocalAppSession]

_PREVIEW_ERROR = (
    "Preview could not start. Stop other local app sessions, check Docker and dependencies, then retry."
)
_IDLE = {"status": "idle", "message": "No preview is running yet. Build an app to start one."}
_STOPPED = {"status": "stopped", "message": "Preview stopped."}
_EXITED = {"status": "stopped", "message": "The preview stopped running. Restart to run it again."}


class StudioPreviewManager:
    """Serialize preview replacement, manage local app sessions, and expose controls."""

    def __init__(self, *, start_fn: StartFn = start_preview_app) -> None:
        self._start_fn = start_fn
        self._session: LocalAppSession | None = None
        self._last_repo_dir: str | None = None
        self._state: dict = dict(_IDLE)
        self._lock = RLock()

        # Multi-surface ecosystem state (R-446/R-447/R-448/R-449)
        self._is_ecosystem = False
        self._ecosystem_id: str | None = None
        self._surfaces: list[dict] = []
        self._active_surface: str | None = None
        self._sessions: dict[str, LocalAppSession] = {}
        self._auth_contract: EcosystemAuthContract | None = None
        self._state_binding: EcosystemStateBinding | None = None
        self._demo_tokens: dict[str, str] = {}
        self._event_bridge_contract: EcosystemEventBridgeContract | None = None
        self._event_bridge: EcosystemEventBridge | None = None
        self._telemetry_contract: EcosystemTelemetryContract | None = None
        self._telemetry_collector: EcosystemTelemetryCollector | None = None
        self._deployment_manifest: EcosystemDeploymentManifest | None = None
        self._live_gateway: EcosystemLiveGateway | None = None
        self._sync_contract: EcosystemSyncContract | None = None
        self._sync_engine: EcosystemSyncEngine | None = None
        self._cicd_contract: EcosystemCICDContract | None = None
        self._cicd_engine: EcosystemCICDEngine | None = None
        self._verification_contract: EcosystemVerificationContract | None = None
        self._verification_engine: EcosystemVerificationEngine | None = None
        self._recovery_contract: EcosystemDisasterRecoveryContract | None = None
        self._recovery_engine: EcosystemRecoveryEngine | None = None
        self._capacity_contract: EcosystemCapacityContract | None = None
        self._capacity_engine: EcosystemCapacityEngine | None = None
        self._alerting_contract: EcosystemAlertingContract | None = None
        self._alerting_engine: EcosystemAlertingEngine | None = None
        self._sla_contract: EcosystemSLAContract | None = None
        self._sla_engine: EcosystemSLAEngine | None = None

    def replace(self, repo_dir: str) -> dict:
        """Stop prior previews, start single app ``repo_dir`` on free ports, and return state."""
        with self._lock:
            self._stop_locked()
            self._is_ecosystem = False
            self._ecosystem_id = None
            self._surfaces = []
            self._active_surface = None
            self._last_repo_dir = repo_dir
            try:
                session = self._start_fn(repo_dir, log=None)
            except Exception:
                return self._set_state({"status": "error", "message": _PREVIEW_ERROR})

            if not session.plan.has_web:
                session.stop()
                return self._set_state(
                    {
                        "status": "unavailable",
                        "message": "This generated project has no web target to preview.",
                    }
                )
            if not session.web_ready:
                session.stop()
                return self._set_state({"status": "error", "message": _PREVIEW_ERROR})

            self._session = session
            payload = {
                "status": "ready",
                "web_url": session.plan.web_url,
                "message": "The generated web application is running locally.",
            }
            if session.plan.backend_kind != "none" and session.api_ready:
                payload["api_url"] = session.plan.api_url
            return self._set_state(payload)

    def replace_ecosystem(
        self,
        ecosystem_id: str,
        surfaces: list[dict],
        active_surface_slug: str | None = None,
        auth_contract: EcosystemAuthContract | None = None,
        state_binding: EcosystemStateBinding | None = None,
        event_bridge: EcosystemEventBridgeContract | None = None,
        telemetry_contract: EcosystemTelemetryContract | None = None,
        deployment_manifest: EcosystemDeploymentManifest | None = None,
        sync_contract: EcosystemSyncContract | None = None,
        cicd_contract: EcosystemCICDContract | None = None,
        verification_contract: EcosystemVerificationContract | None = None,
        recovery_contract: EcosystemDisasterRecoveryContract | None = None,
        capacity_contract: EcosystemCapacityContract | None = None,
        alerting_contract: EcosystemAlertingContract | None = None,
        sla_contract: EcosystemSLAContract | None = None,
    ) -> dict:
        """Stop prior previews, register ecosystem surfaces, and start the active surface."""
        with self._lock:
            self._stop_locked()
            self._is_ecosystem = True
            self._ecosystem_id = ecosystem_id
            self._surfaces = [
                s.to_dict() if hasattr(s, "to_dict") else dict(s)
                for s in surfaces
            ]
            self._sessions = {}

            if not self._surfaces:
                return self._set_state({"status": "error", "message": "No surfaces provided in ecosystem."})

            if auth_contract is not None:
                self._auth_contract = auth_contract
            else:
                self._auth_contract = synthesize_ecosystem_auth(ecosystem_id, self._surfaces)

            if state_binding is not None:
                self._state_binding = state_binding
            else:
                self._state_binding = synthesize_ecosystem_state(ecosystem_id, self._surfaces)

            self._demo_tokens = generate_surface_tokens(self._auth_contract)

            if event_bridge is not None:
                self._event_bridge_contract = event_bridge
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_bridge = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_event_bridge(ecosystem_id)
                if cached_bridge is not None:
                    self._event_bridge_contract = cached_bridge
                else:
                    self._event_bridge_contract = synthesize_ecosystem_events(
                        ecosystem_id, self._surfaces, state_binding=self._state_binding
                    )
            self._event_bridge = EcosystemEventBridge(self._event_bridge_contract)

            # Telemetry contract (R-449)
            if telemetry_contract is not None:
                self._telemetry_contract = telemetry_contract
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_tc = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_telemetry_contract(ecosystem_id)
                if cached_tc is not None:
                    self._telemetry_contract = cached_tc
                else:
                    self._telemetry_contract = synthesize_ecosystem_telemetry(
                        ecosystem_id, self._surfaces
                    )
            self._telemetry_collector = EcosystemTelemetryCollector(self._telemetry_contract)

            # Deployment manifest (R-450)
            if deployment_manifest is not None:
                self._deployment_manifest = deployment_manifest
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_dm = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_deployment_manifest(ecosystem_id)
                if cached_dm is not None:
                    self._deployment_manifest = cached_dm
                else:
                    self._deployment_manifest = synthesize_ecosystem_deployment(
                        ecosystem_id, self._surfaces
                    )

            # Data Sync contract (R-451)
            if sync_contract is not None:
                self._sync_contract = sync_contract
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_sync = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_sync_contract(ecosystem_id)
                if cached_sync is not None:
                    self._sync_contract = cached_sync
                else:
                    self._sync_contract = synthesize_ecosystem_sync(
                        ecosystem_id, self._surfaces
                    )
            self._sync_engine = EcosystemSyncEngine(self._sync_contract)

            # CI/CD contract (R-452)
            if cicd_contract is not None:
                self._cicd_contract = cicd_contract
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_cicd = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_cicd_contract(ecosystem_id)
                if cached_cicd is not None:
                    self._cicd_contract = cached_cicd
                else:
                    self._cicd_contract = synthesize_ecosystem_cicd(
                        ecosystem_id, self._surfaces
                    )
            self._cicd_engine = EcosystemCICDEngine(self._cicd_contract)

            # Verification contract (R-453)
            if verification_contract is not None:
                self._verification_contract = verification_contract
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_vc = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_verification_contract(ecosystem_id)
                if cached_vc is not None:
                    self._verification_contract = cached_vc
                else:
                    self._verification_contract = synthesize_ecosystem_verification(
                        ecosystem_id, self._surfaces
                    )
            self._verification_engine = EcosystemVerificationEngine(self._verification_contract)

            # Disaster Recovery contract (R-454)
            if recovery_contract is not None:
                self._recovery_contract = recovery_contract
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_rc = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_recovery_contract(ecosystem_id)
                if cached_rc is not None:
                    self._recovery_contract = cached_rc
                else:
                    self._recovery_contract = synthesize_ecosystem_recovery(
                        ecosystem_id, self._surfaces
                    )
            self._recovery_engine = EcosystemRecoveryEngine(self._recovery_contract)

            # Capacity Planning contract (R-455)
            if capacity_contract is not None:
                self._capacity_contract = capacity_contract
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_cc = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_capacity_contract(ecosystem_id)
                if cached_cc is not None:
                    self._capacity_contract = cached_cc
                else:
                    self._capacity_contract = synthesize_ecosystem_capacity(
                        ecosystem_id, self._surfaces
                    )
            self._capacity_engine = EcosystemCapacityEngine(self._capacity_contract)

            # Alerting contract (R-456)
            if alerting_contract is not None:
                self._alerting_contract = alerting_contract
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_ac = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_alerting_contract(ecosystem_id)
                if cached_ac is not None:
                    self._alerting_contract = cached_ac
                else:
                    self._alerting_contract = synthesize_ecosystem_alerting(
                        ecosystem_id, self._surfaces
                    )
            self._alerting_engine = EcosystemAlertingEngine(self._alerting_contract)

            # SLA contract (R-457)
            if sla_contract is not None:
                self._sla_contract = sla_contract
            else:
                from ..solution_packs.ecosystem_registry import DEFAULT_ECOSYSTEM_PACK_REGISTRY
                cached_sc = DEFAULT_ECOSYSTEM_PACK_REGISTRY.get_sla_contract(ecosystem_id)
                if cached_sc is not None:
                    self._sla_contract = cached_sc
                else:
                    self._sla_contract = synthesize_ecosystem_sla(
                        ecosystem_id, self._surfaces
                    )
            self._sla_engine = EcosystemSLAEngine(self._sla_contract)

            # Determine initial active surface
            chosen_slug = active_surface_slug
            if not chosen_slug or not any(s["slug"] == chosen_slug for s in self._surfaces):
                customer_surface = next(
                    (s for s in self._surfaces if s.get("surface_kind") == "customer_web"),
                    None,
                )
                chosen_slug = customer_surface["slug"] if customer_surface else self._surfaces[0]["slug"]

            self._active_surface = chosen_slug
            return self._launch_surface_locked(chosen_slug)

    def switch_surface(self, surface_slug: str) -> dict:
        """Switch active preview to ``surface_slug``, launching it on demand if not running."""
        with self._lock:
            if not self._is_ecosystem:
                return self._set_state({"status": "error", "message": "No ecosystem preview is active."})

            target_surface = next((s for s in self._surfaces if s["slug"] == surface_slug), None)
            if target_surface is None:
                return self._set_state(
                    {"status": "error", "message": f"Surface '{surface_slug}' not found in ecosystem."}
                )

            self._active_surface = surface_slug
            existing_session = self._sessions.get(surface_slug)
            if existing_session is not None and existing_session.is_alive():
                return self._build_ecosystem_payload_locked()

            return self._launch_surface_locked(surface_slug)

    def _launch_surface_locked(self, surface_slug: str) -> dict:
        surface = next((s for s in self._surfaces if s["slug"] == surface_slug), None)
        if surface is None:
            return self._set_state(
                {"status": "error", "message": f"Surface '{surface_slug}' not found in ecosystem."}
            )

        repo_dir = surface.get("target_dir", "")
        self._last_repo_dir = repo_dir

        if surface_slug in self._sessions:
            sess = self._sessions.pop(surface_slug)
            sess.stop()

        try:
            session = self._start_fn(repo_dir, log=None)
        except Exception:
            return self._build_ecosystem_payload_locked(error_surface=surface_slug)

        if not session.plan.has_web:
            session.stop()
            return self._build_ecosystem_payload_locked(
                error_surface=surface_slug,
                error_msg="Surface has no web target to preview.",
            )
        if not session.web_ready:
            session.stop()
            return self._build_ecosystem_payload_locked(error_surface=surface_slug)

        self._sessions[surface_slug] = session
        return self._build_ecosystem_payload_locked()

    def status(self) -> dict:
        """Return a bounded, secret-free snapshot of the current preview state (liveness-aware)."""
        with self._lock:
            self._refresh_locked()
            if self._is_ecosystem:
                return self._build_ecosystem_payload_locked()
            return dict(self._state)

    def _refresh_locked(self) -> None:
        """If any active preview processes have exited on their own, stop and report them."""
        if self._session is not None and not self._session.is_alive():
            session, self._session = self._session, None
            session.stop()
            self._state = dict(_EXITED)

        if self._is_ecosystem:
            for slug, session in list(self._sessions.items()):
                if not session.is_alive():
                    del self._sessions[slug]
                    session.stop()

    def stop(self, surface_slug: str | None = None) -> dict:
        """Stop preview session(s). If ``surface_slug`` is given, stops only that surface."""
        with self._lock:
            if self._is_ecosystem and surface_slug:
                if surface_slug in self._sessions:
                    sess = self._sessions.pop(surface_slug)
                    sess.stop()
                return self._build_ecosystem_payload_locked()

            self._stop_locked()
            return self._set_state(dict(_STOPPED))

    def restart(self, surface_slug: str | None = None) -> dict:
        """Restart preview session(s)."""
        with self._lock:
            if self._is_ecosystem:
                target_slug = surface_slug or self._active_surface
                if not target_slug:
                    return dict(_IDLE)
                if target_slug in self._sessions:
                    sess = self._sessions.pop(target_slug)
                    sess.stop()
                return self._launch_surface_locked(target_slug)

            repo_dir = self._last_repo_dir
            if repo_dir is None:
                return dict(_IDLE)
            return self.replace(repo_dir)

    def _build_ecosystem_payload_locked(
        self,
        error_surface: str | None = None,
        error_msg: str | None = None,
    ) -> dict:
        surface_statuses = []
        for s in self._surfaces:
            slug = s["slug"]
            sess = self._sessions.get(slug)
            is_active = (slug == self._active_surface)
            is_ready = sess is not None and sess.is_alive() and sess.web_ready
            status_str = "ready" if is_ready else ("error" if slug == error_surface else "stopped")
            surface_statuses.append({
                "slug": slug,
                "app_name": s.get("app_name", slug),
                "surface_kind": s.get("surface_kind", "web"),
                "status": status_str,
                "is_active": is_active,
                "web_url": sess.plan.web_url if is_ready else None,
                "api_url": sess.plan.api_url if (is_ready and sess.api_ready) else None,
            })

        active_surface_info = next(
            (s for s in self._surfaces if s["slug"] == self._active_surface),
            None,
        )
        active_sess = self._sessions.get(self._active_surface or "") if self._active_surface else None
        active_ready = active_sess is not None and active_sess.is_alive() and active_sess.web_ready

        # Resolve active auth role and demo token
        active_role = None
        active_token = None
        if self._auth_contract and self._active_surface:
            for r in self._auth_contract.roles:
                if r.surface_slug == self._active_surface:
                    active_role = r.role_id
                    break
            active_token = self._demo_tokens.get(self._active_surface)

        if error_surface and error_surface == self._active_surface:
            payload = {
                "status": "error",
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "active_surface": self._active_surface,
                "active_role": active_role,
                "active_token": active_token,
                "has_auth": self._auth_contract is not None,
                "has_state": self._state_binding is not None,
                "has_events": self._event_bridge_contract is not None,
                "event_count": len(self._event_bridge_contract.supported_events) if self._event_bridge_contract else 0,
                "subscription_count": len(self._event_bridge_contract.subscriptions) if self._event_bridge_contract else 0,
                "has_telemetry": self._telemetry_contract is not None,
                "telemetry_surface_count": len(self._telemetry_contract.traced_surfaces) if self._telemetry_contract else 0,
                "has_deployment": self._deployment_manifest is not None,
                "deployment_surface_count": len(self._deployment_manifest.surfaces) if self._deployment_manifest else 0,
                "gateway_routes": [r.to_dict() for r in self._deployment_manifest.gateway_routes] if self._deployment_manifest else [],
                "gateway_port": self._deployment_manifest.gateway_port if self._deployment_manifest else None,
                "gateway_url": f"http://127.0.0.1:{self._deployment_manifest.gateway_port}" if self._deployment_manifest else None,
                "has_sync": self._sync_contract is not None,
                "sync_entity_count": len(self._sync_contract.sync_entities) if self._sync_contract else 0,
                "sync_conflict_count": self._sync_engine.conflict_count if self._sync_engine else 0,
                "sync_version": self._sync_engine.current_version if self._sync_engine else 0,
                "has_cicd": self._cicd_contract is not None,
                "cicd_workflow_count": len(self._cicd_contract.workflows) if self._cicd_contract else 0,
                "cicd_job_count": sum(len(w.jobs) for w in self._cicd_contract.workflows) if self._cicd_contract else 0,
                "cicd_status": "configured" if self._cicd_contract else "none",
                "has_verification": self._verification_contract is not None,
                "probe_count": len(self._verification_contract.probes) if self._verification_contract else 0,
                "smoke_test_count": len(self._verification_contract.smoke_tests) if self._verification_contract else 0,
                "canary_rule_count": len(self._verification_contract.canary_rules) if self._verification_contract else 0,
                "has_recovery": self._recovery_contract is not None,
                "backup_target_count": len(self._recovery_contract.backup_targets) if self._recovery_contract else 0,
                "recovery_step_count": len(self._recovery_contract.recovery_steps) if self._recovery_contract else 0,
                "rollback_trigger_count": len(self._recovery_contract.rollback_triggers) if self._recovery_contract else 0,
                "dr_status": "configured" if self._recovery_contract else "none",
                "has_capacity": self._capacity_contract is not None,
                "capacity_spec_count": len(self._capacity_contract.surface_capacities) if self._capacity_contract else 0,
                "quota_count": len(self._capacity_contract.resource_quotas) if self._capacity_contract else 0,
                "cost_model_count": len(self._capacity_contract.cost_models) if self._capacity_contract else 0,
                "monthly_budget_usd": self._capacity_contract.monthly_budget_limit_usd if self._capacity_contract else 0.0,
                "capacity_status": "configured" if self._capacity_contract else "none",
                "has_alerting": self._alerting_contract is not None,
                "alert_rule_count": len(self._alerting_contract.alert_rules) if self._alerting_contract else 0,
                "runbook_count": len(self._alerting_contract.runbooks) if self._alerting_contract else 0,
                "escalation_policy_count": len(self._alerting_contract.escalation_policies) if self._alerting_contract else 0,
                "alert_status": "configured" if self._alerting_contract else "none",
                "has_sla": self._sla_contract is not None,
                "sli_count": len(self._sla_contract.slis) if self._sla_contract else 0,
                "slo_count": len(self._sla_contract.slos) if self._sla_contract else 0,
                "sla_count": len(self._sla_contract.slas) if self._sla_contract else 0,
                "sla_status": "configured" if self._sla_contract else "none",
                "message": error_msg or _PREVIEW_ERROR,
                "surfaces": surface_statuses,
            }
        elif active_ready and active_sess is not None and active_surface_info is not None:
            payload = {
                "status": "ready",
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "active_surface": self._active_surface,
                "active_role": active_role,
                "active_token": active_token,
                "has_auth": self._auth_contract is not None,
                "has_state": self._state_binding is not None,
                "has_events": self._event_bridge_contract is not None,
                "event_count": len(self._event_bridge_contract.supported_events) if self._event_bridge_contract else 0,
                "subscription_count": len(self._event_bridge_contract.subscriptions) if self._event_bridge_contract else 0,
                "has_telemetry": self._telemetry_contract is not None,
                "telemetry_surface_count": len(self._telemetry_contract.traced_surfaces) if self._telemetry_contract else 0,
                "has_deployment": self._deployment_manifest is not None,
                "deployment_surface_count": len(self._deployment_manifest.surfaces) if self._deployment_manifest else 0,
                "gateway_routes": [r.to_dict() for r in self._deployment_manifest.gateway_routes] if self._deployment_manifest else [],
                "gateway_port": self._deployment_manifest.gateway_port if self._deployment_manifest else None,
                "gateway_url": f"http://127.0.0.1:{self._deployment_manifest.gateway_port}" if self._deployment_manifest else None,
                "has_sync": self._sync_contract is not None,
                "sync_entity_count": len(self._sync_contract.sync_entities) if self._sync_contract else 0,
                "sync_conflict_count": self._sync_engine.conflict_count if self._sync_engine else 0,
                "sync_version": self._sync_engine.current_version if self._sync_engine else 0,
                "has_cicd": self._cicd_contract is not None,
                "cicd_workflow_count": len(self._cicd_contract.workflows) if self._cicd_contract else 0,
                "cicd_job_count": sum(len(w.jobs) for w in self._cicd_contract.workflows) if self._cicd_contract else 0,
                "cicd_status": "configured" if self._cicd_contract else "none",
                "has_verification": self._verification_contract is not None,
                "probe_count": len(self._verification_contract.probes) if self._verification_contract else 0,
                "smoke_test_count": len(self._verification_contract.smoke_tests) if self._verification_contract else 0,
                "canary_rule_count": len(self._verification_contract.canary_rules) if self._verification_contract else 0,
                "has_recovery": self._recovery_contract is not None,
                "backup_target_count": len(self._recovery_contract.backup_targets) if self._recovery_contract else 0,
                "recovery_step_count": len(self._recovery_contract.recovery_steps) if self._recovery_contract else 0,
                "rollback_trigger_count": len(self._recovery_contract.rollback_triggers) if self._recovery_contract else 0,
                "dr_status": "configured" if self._recovery_contract else "none",
                "has_capacity": self._capacity_contract is not None,
                "capacity_spec_count": len(self._capacity_contract.surface_capacities) if self._capacity_contract else 0,
                "quota_count": len(self._capacity_contract.resource_quotas) if self._capacity_contract else 0,
                "cost_model_count": len(self._capacity_contract.cost_models) if self._capacity_contract else 0,
                "monthly_budget_usd": self._capacity_contract.monthly_budget_limit_usd if self._capacity_contract else 0.0,
                "capacity_status": "configured" if self._capacity_contract else "none",
                "has_alerting": self._alerting_contract is not None,
                "alert_rule_count": len(self._alerting_contract.alert_rules) if self._alerting_contract else 0,
                "runbook_count": len(self._alerting_contract.runbooks) if self._alerting_contract else 0,
                "escalation_policy_count": len(self._alerting_contract.escalation_policies) if self._alerting_contract else 0,
                "alert_status": "configured" if self._alerting_contract else "none",
                "has_sla": self._sla_contract is not None,
                "sli_count": len(self._sla_contract.slis) if self._sla_contract else 0,
                "slo_count": len(self._sla_contract.slos) if self._sla_contract else 0,
                "sla_count": len(self._sla_contract.slas) if self._sla_contract else 0,
                "sla_status": "configured" if self._sla_contract else "none",
                "web_url": active_sess.plan.web_url,
                "message": f"The generated {active_surface_info['app_name']} is running locally.",
                "surfaces": surface_statuses,
            }
            if active_sess.plan.backend_kind != "none" and active_sess.api_ready:
                payload["api_url"] = active_sess.plan.api_url
        else:
            payload = {
                "status": "stopped" if any(s["status"] == "ready" for s in surface_statuses) else (
                    self._state.get("status", "stopped")
                ),
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "active_surface": self._active_surface,
                "active_role": active_role,
                "active_token": active_token,
                "has_auth": self._auth_contract is not None,
                "has_state": self._state_binding is not None,
                "has_events": self._event_bridge_contract is not None,
                "event_count": len(self._event_bridge_contract.supported_events) if self._event_bridge_contract else 0,
                "subscription_count": len(self._event_bridge_contract.subscriptions) if self._event_bridge_contract else 0,
                "has_telemetry": self._telemetry_contract is not None,
                "telemetry_surface_count": len(self._telemetry_contract.traced_surfaces) if self._telemetry_contract else 0,
                "has_deployment": self._deployment_manifest is not None,
                "deployment_surface_count": len(self._deployment_manifest.surfaces) if self._deployment_manifest else 0,
                "gateway_routes": [r.to_dict() for r in self._deployment_manifest.gateway_routes] if self._deployment_manifest else [],
                "gateway_port": self._deployment_manifest.gateway_port if self._deployment_manifest else None,
                "gateway_url": f"http://127.0.0.1:{self._deployment_manifest.gateway_port}" if self._deployment_manifest else None,
                "has_sync": self._sync_contract is not None,
                "sync_entity_count": len(self._sync_contract.sync_entities) if self._sync_contract else 0,
                "sync_conflict_count": self._sync_engine.conflict_count if self._sync_engine else 0,
                "sync_version": self._sync_engine.current_version if self._sync_engine else 0,
                "has_cicd": self._cicd_contract is not None,
                "cicd_workflow_count": len(self._cicd_contract.workflows) if self._cicd_contract else 0,
                "cicd_job_count": sum(len(w.jobs) for w in self._cicd_contract.workflows) if self._cicd_contract else 0,
                "cicd_status": "configured" if self._cicd_contract else "none",
                "has_verification": self._verification_contract is not None,
                "probe_count": len(self._verification_contract.probes) if self._verification_contract else 0,
                "smoke_test_count": len(self._verification_contract.smoke_tests) if self._verification_contract else 0,
                "canary_rule_count": len(self._verification_contract.canary_rules) if self._verification_contract else 0,
                "has_recovery": self._recovery_contract is not None,
                "backup_target_count": len(self._recovery_contract.backup_targets) if self._recovery_contract else 0,
                "recovery_step_count": len(self._recovery_contract.recovery_steps) if self._recovery_contract else 0,
                "rollback_trigger_count": len(self._recovery_contract.rollback_triggers) if self._recovery_contract else 0,
                "dr_status": "configured" if self._recovery_contract else "none",
                "has_capacity": self._capacity_contract is not None,
                "capacity_spec_count": len(self._capacity_contract.surface_capacities) if self._capacity_contract else 0,
                "quota_count": len(self._capacity_contract.resource_quotas) if self._capacity_contract else 0,
                "cost_model_count": len(self._capacity_contract.cost_models) if self._capacity_contract else 0,
                "monthly_budget_usd": self._capacity_contract.monthly_budget_limit_usd if self._capacity_contract else 0.0,
                "capacity_status": "configured" if self._capacity_contract else "none",
                "has_alerting": self._alerting_contract is not None,
                "alert_rule_count": len(self._alerting_contract.alert_rules) if self._alerting_contract else 0,
                "runbook_count": len(self._alerting_contract.runbooks) if self._alerting_contract else 0,
                "escalation_policy_count": len(self._alerting_contract.escalation_policies) if self._alerting_contract else 0,
                "alert_status": "configured" if self._alerting_contract else "none",
                "has_sla": self._sla_contract is not None,
                "sli_count": len(self._sla_contract.slis) if self._sla_contract else 0,
                "slo_count": len(self._sla_contract.slos) if self._sla_contract else 0,
                "sla_count": len(self._sla_contract.slas) if self._sla_contract else 0,
                "sla_status": "configured" if self._sla_contract else "none",
                "message": f"Preview for {self._active_surface or 'surface'} stopped.",
                "surfaces": surface_statuses,
            }

        return self._set_state(payload)

    def _set_state(self, state: dict) -> dict:
        self._state = dict(state)
        return dict(state)

    def _stop_locked(self) -> None:
        if self._session is not None:
            session, self._session = self._session, None
            session.stop()
        for session in self._sessions.values():
            session.stop()
        self._sessions.clear()
        self._auth_contract = None
        self._state_binding = None
        self._demo_tokens.clear()
        self._event_bridge_contract = None
        self._event_bridge = None
        self._telemetry_contract = None
        self._telemetry_collector = None
        if self._live_gateway is not None:
            self._live_gateway.stop()
            self._live_gateway = None
        self._deployment_manifest = None
        self._verification_contract = None
        self._verification_engine = None
        self._recovery_contract = None
        self._recovery_engine = None
        self._capacity_contract = None
        self._capacity_engine = None
        self._alerting_contract = None
        self._alerting_engine = None
        self._sla_contract = None
        self._sla_engine = None

    def get_ecosystem_auth(self) -> dict:
        """Inspect the active ecosystem's auth contract, role matrix, and surface demo tokens."""
        with self._lock:
            if not self._is_ecosystem or not self._auth_contract:
                return {"is_ecosystem": False, "auth_contract": None, "tokens": {}}
            matrix = CrossAppAuthMatrix.from_contract(self._auth_contract)
            safe_contract = dict(self._auth_contract.to_dict())
            safe_contract["jwt_secret"] = "***"
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "auth_contract": safe_contract,
                "matrix": matrix.to_dict(),
                "active_surface": self._active_surface,
                "tokens": dict(self._demo_tokens),
            }

    def get_ecosystem_state(self) -> dict:
        """Inspect the active ecosystem's unified state binding."""
        with self._lock:
            if not self._is_ecosystem or not self._state_binding:
                return {"is_ecosystem": False, "state_binding": None}
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "state_binding": self._state_binding.to_dict(),
                "active_surface": self._active_surface,
            }

    def get_ecosystem_events(self) -> dict:
        """Inspect the active ecosystem's event bridge contract, subscriptions, and recent delivery logs."""
        with self._lock:
            if not self._is_ecosystem or not self._event_bridge_contract or not self._event_bridge:
                return {
                    "is_ecosystem": False,
                    "contract": None,
                    "supported_events": [],
                    "subscriptions": [],
                    "deliveries": [],
                }
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "contract": self._event_bridge_contract.to_dict(),
                "supported_events": list(self._event_bridge_contract.supported_events),
                "subscriptions": [s.to_dict() for s in self._event_bridge_contract.subscriptions],
                "deliveries": self._event_bridge.get_delivery_log(limit=50),
                "active_surface": self._active_surface,
            }

    def dispatch_ecosystem_event(
        self,
        event_type: str,
        entity_name: str,
        entity_id: str,
        action: str = "update",
        data: dict | None = None,
        source_surface: str | None = None,
    ) -> dict:
        """Dispatch a cross-surface event via the event bridge to running surface endpoints or simulated targets."""
        with self._lock:
            if not self._is_ecosystem or not self._event_bridge:
                return {"status": "error", "message": "No ecosystem preview is running."}

            src = source_surface or self._active_surface or (self._surfaces[0]["slug"] if self._surfaces else "system")
            event = EcosystemEventPayload(
                event_id="",
                event_type=event_type,
                ecosystem_id=self._ecosystem_id or "unknown",
                source_surface=src,
                timestamp="",
                entity_name=entity_name,
                entity_id=entity_id,
                action=action,
                data=data or {},
            )

            surface_urls: dict[str, str] = {}
            for slug, sess in self._sessions.items():
                if sess.is_alive() and sess.plan.web_url:
                    surface_urls[slug] = sess.plan.web_url

            deliveries = self._event_bridge.dispatch(event, surface_urls=surface_urls)
            return {
                "status": "ok",
                "event": event.to_dict(),
                "deliveries": [d.to_dict() for d in deliveries],
                "delivery_count": len(deliveries),
            }

    def get_ecosystem_telemetry(self) -> dict:
        """Inspect the active ecosystem's telemetry contract and recent spans."""
        with self._lock:
            if not self._is_ecosystem or not self._telemetry_contract:
                return {
                    "is_ecosystem": False,
                    "telemetry_contract": None,
                    "traced_surfaces": [],
                    "spans": [],
                    "audit_trail": [],
                    "span_count": 0,
                    "audit_count": 0,
                }
            span_count = self._telemetry_collector.get_span_count() if self._telemetry_collector else 0
            audit_count = self._telemetry_collector.get_audit_count() if self._telemetry_collector else 0
            recent_spans = self._telemetry_collector.get_spans(limit=50) if self._telemetry_collector else []
            recent_audit = self._telemetry_collector.get_audit_trail(limit=50) if self._telemetry_collector else []
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "telemetry_contract": self._telemetry_contract.to_dict(),
                "traced_surfaces": [ts.to_dict() for ts in self._telemetry_contract.traced_surfaces],
                "active_surface": self._active_surface,
                "span_count": span_count,
                "audit_count": audit_count,
                "spans": recent_spans,
                "audit_trail": recent_audit,
            }

    def get_ecosystem_deployment(self) -> dict | None:
        """Inspect the active ecosystem's deployment manifest and gateway routes."""
        with self._lock:
            if not self._is_ecosystem or not self._deployment_manifest:
                return None
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                **self._deployment_manifest.to_dict(),
            }

    def to_compose_yaml(self) -> str | None:
        """Generate Docker Compose YAML for the active ecosystem deployment."""
        with self._lock:
            if not self._is_ecosystem or not self._deployment_manifest:
                return None
            return self._deployment_manifest.to_compose_yaml()

    def get_ecosystem_sync(self) -> dict | None:
        """Inspect the active ecosystem's data sync contract and status."""
        with self._lock:
            if not self._is_ecosystem or not self._sync_contract:
                return None
            conflicts = [c.to_dict() for c in self._sync_engine.get_conflicts()] if self._sync_engine else []
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "sync_contract": self._sync_contract.to_dict(),
                "current_version": self._sync_engine.current_version if self._sync_engine else 0,
                "mutation_count": self._sync_engine.mutation_count if self._sync_engine else 0,
                "conflict_count": self._sync_engine.conflict_count if self._sync_engine else 0,
                "conflicts": conflicts,
            }

    def push_sync_mutations(
        self,
        surface_slug: str,
        mutations: list[dict],
    ) -> dict:
        """Push a batch of mutations to the active sync engine."""
        with self._lock:
            if not self._is_ecosystem or not self._sync_engine:
                return {"status": "error", "message": "No active ecosystem sync engine"}
            parsed_mutations = [SyncMutation.from_dict(m) for m in mutations]
            accepted, conflicts = self._sync_engine.push_mutations(surface_slug, parsed_mutations)
            return {
                "status": "ok",
                "accepted": [m.to_dict() for m in accepted],
                "conflicts": [c.to_dict() for c in conflicts],
                "current_version": self._sync_engine.current_version,
            }

    def pull_sync_changes(
        self,
        surface_slug: str,
        since_version: int = 0,
    ) -> dict:
        """Pull mutations that occurred since ``since_version``."""
        with self._lock:
            if not self._is_ecosystem or not self._sync_engine:
                return {"status": "error", "message": "No active ecosystem sync engine"}
            mutations, checkpoint = self._sync_engine.pull_changes(surface_slug, since_version)
            return {
                "status": "ok",
                "mutations": [m.to_dict() for m in mutations],
                "checkpoint": checkpoint.to_dict(),
                "current_version": self._sync_engine.current_version,
            }

    def simulate_sync_conflict(
        self,
        entity_name: str,
        record_id: str,
        local_surface: str,
        remote_surface: str,
        local_updates: dict,
        remote_updates: dict,
        strategy: str = "field_merge",
    ) -> dict:
        """Simulate a concurrent mutation conflict and return the resolved record."""
        with self._lock:
            if not self._is_ecosystem or not self._sync_engine:
                return {"status": "error", "message": "No active ecosystem sync engine"}
            conflict = self._sync_engine.simulate_conflict(
                entity_name=entity_name,
                record_id=record_id,
                local_surface=local_surface,
                remote_surface=remote_surface,
                local_updates=local_updates,
                remote_updates=remote_updates,
                strategy=strategy,
            )
            return {
                "status": "ok",
                "conflict": conflict.to_dict(),
                "conflict_count": self._sync_engine.conflict_count,
            }

    def get_ecosystem_cicd(self) -> dict:
        """Return the serialized EcosystemCICDContract and engine status."""
        with self._lock:
            if not self._is_ecosystem or not self._cicd_contract:
                return {"status": "none", "is_ecosystem": False, "message": "No active ecosystem CI/CD contract"}
            return {
                "status": "ok",
                "is_ecosystem": True,
                "cicd_contract": self._cicd_contract.to_dict(),
                "contract": self._cicd_contract.to_dict(),
                "workflow_count": len(self._cicd_contract.workflows),
                "job_count": sum(len(w.jobs) for w in self._cicd_contract.workflows),
            }

    def to_workflow_yaml(self) -> str:
        """Export the primary workflow as GitHub Actions YAML."""
        with self._lock:
            if not self._is_ecosystem or not self._cicd_contract:
                return "# No ecosystem CI/CD contract configured\n"
            return to_workflow_yaml(self._cicd_contract)

    def simulate_cicd_run(self, trigger: str = "push") -> dict:
        """Simulate a dry-run execution of the ecosystem CI/CD pipeline."""
        with self._lock:
            if not self._is_ecosystem or not self._cicd_engine:
                return {"status": "error", "success": False, "error": "No active ecosystem CI/CD engine"}
            res = self._cicd_engine.simulate_pipeline_run(trigger=trigger)
            return {
                **res,
                "status": "ok",
                "simulation": res,
            }

    def get_ecosystem_verification(self) -> dict:
        """Inspect the active ecosystem's verification contract (probes, smoke tests, canary rules)."""
        with self._lock:
            if not self._is_ecosystem or not self._verification_contract:
                return {
                    "is_ecosystem": False,
                    "verification_contract": None,
                    "probe_count": 0,
                    "smoke_test_count": 0,
                    "canary_rule_count": 0,
                }
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "verification_contract": self._verification_contract.to_dict(),
                "probe_count": len(self._verification_contract.probes),
                "smoke_test_count": len(self._verification_contract.smoke_tests),
                "canary_rule_count": len(self._verification_contract.canary_rules),
                "active_surface": self._active_surface,
            }

    def simulate_ecosystem_verification(self) -> dict:
        """Run a full dry-run simulation of ecosystem verification probes, smoke tests, and canary rules."""
        with self._lock:
            if not self._is_ecosystem or not self._verification_engine:
                return {"status": "error", "message": "No active ecosystem verification engine"}
            return self._verification_engine.simulate_full_verification()

    def get_ecosystem_recovery(self) -> dict:
        """Inspect the active ecosystem's disaster recovery contract."""
        with self._lock:
            if not self._is_ecosystem or not self._recovery_contract:
                return {
                    "is_ecosystem": False,
                    "recovery_contract": None,
                    "backup_target_count": 0,
                    "recovery_step_count": 0,
                    "rollback_trigger_count": 0,
                }
            return {
                "is_ecosystem": True,
                "ecosystem_id": self._ecosystem_id,
                "recovery_contract": self._recovery_contract.to_dict(),
                "backup_target_count": len(self._recovery_contract.backup_targets),
                "recovery_step_count": len(self._recovery_contract.recovery_steps),
                "rollback_trigger_count": len(self._recovery_contract.rollback_triggers),
                "active_surface": self._active_surface,
            }

    def simulate_ecosystem_recovery(self) -> dict:
        """Run a full dry-run simulation of ecosystem disaster recovery exercise."""
        with self._lock:
            if not self._is_ecosystem or not self._recovery_engine:
                return {"status": "error", "message": "No active ecosystem recovery engine"}
            return self._recovery_engine.simulate_full_dr_exercise()

    def get_ecosystem_capacity(self) -> dict:
        """Inspect the active ecosystem's capacity planning contract."""
        with self._lock:
            if not self._is_ecosystem or not self._capacity_contract:
                return {
                    "is_ecosystem": False,
                    "status": "not_configured",
                    "contract": None,
                    "capacity_contract": None,
                    "capacity_spec_count": 0,
                    "quota_count": 0,
                    "cost_model_count": 0,
                    "monthly_budget_usd": 0.0,
                }
            return {
                "is_ecosystem": True,
                "status": "ok",
                "ecosystem_id": self._ecosystem_id,
                "contract": self._capacity_contract.to_dict(),
                "capacity_contract": self._capacity_contract.to_dict(),
                "digest": self._capacity_contract.digest(),
                "capacity_spec_count": len(self._capacity_contract.surface_capacities),
                "quota_count": len(self._capacity_contract.resource_quotas),
                "cost_model_count": len(self._capacity_contract.cost_models),
                "monthly_budget_usd": self._capacity_contract.monthly_budget_limit_usd,
                "active_surface": self._active_surface,
            }

    def simulate_ecosystem_capacity(self, body: Mapping[str, Any] | None = None) -> dict:
        """Run a dry-run simulation of ecosystem capacity workload tier."""
        with self._lock:
            if not self._is_ecosystem or not self._capacity_engine:
                return {"status": "error", "message": "No active ecosystem capacity engine"}
            tier = "base"
            monthly_requests = 100_000
            if isinstance(body, Mapping):
                tier = str(body.get("tier", "base"))
                monthly_requests = int(body.get("monthly_requests", 100_000))
            rep = self._capacity_engine.simulate_workload_tier(tier=tier, monthly_requests=monthly_requests)
            return {
                "status": "ok",
                "report": rep.to_dict(),
                **rep.to_dict(),
            }

    def get_ecosystem_alerting(self) -> dict:
        """Inspect the active ecosystem's alerting contract."""
        with self._lock:
            if not self._is_ecosystem or not self._alerting_contract:
                return {
                    "is_ecosystem": False,
                    "status": "not_configured",
                    "contract": None,
                    "alerting_contract": None,
                    "alert_rule_count": 0,
                    "runbook_count": 0,
                    "escalation_policy_count": 0,
                }
            return {
                "is_ecosystem": True,
                "status": "ok",
                "ecosystem_id": self._ecosystem_id,
                "contract": self._alerting_contract.to_dict(),
                "alerting_contract": self._alerting_contract.to_dict(),
                "digest": self._alerting_contract.digest(),
                "alert_rule_count": len(self._alerting_contract.alert_rules),
                "runbook_count": len(self._alerting_contract.runbooks),
                "escalation_policy_count": len(self._alerting_contract.escalation_policies),
                "active_surface": self._active_surface,
            }

    def simulate_ecosystem_alerting(self, body: Mapping[str, Any] | None = None) -> dict:
        """Run a dry-run simulation of ecosystem alerting / incident scenario."""
        with self._lock:
            if not self._is_ecosystem or not self._alerting_engine:
                return {"status": "error", "message": "No active ecosystem alerting engine"}
            scenario = "api_error_spike"
            metric_value = None
            if isinstance(body, Mapping):
                scenario = str(body.get("scenario", body.get("rule_id", "api_error_spike")))
                if "metric_value" in body:
                    try:
                        metric_value = float(body["metric_value"])
                    except (ValueError, TypeError):
                        metric_value = None
            rep = self._alerting_engine.simulate_incident(scenario=scenario, metric_value=metric_value)
            return {
                "status": "ok",
                "report": rep.to_dict(),
                **rep.to_dict(),
            }

    def get_ecosystem_sla(self) -> dict:
        """Inspect the active ecosystem's SLA/SLO contract."""
        with self._lock:
            if not self._is_ecosystem or not self._sla_contract:
                return {
                    "is_ecosystem": False,
                    "status": "not_configured",
                    "contract": None,
                    "sla_contract": None,
                    "sli_count": 0,
                    "slo_count": 0,
                    "sla_count": 0,
                }
            return {
                "is_ecosystem": True,
                "status": "ok",
                "ecosystem_id": self._ecosystem_id,
                "contract": self._sla_contract.to_dict(),
                "sla_contract": self._sla_contract.to_dict(),
                "digest": self._sla_contract.digest(),
                "sli_count": len(self._sla_contract.slis),
                "slo_count": len(self._sla_contract.slos),
                "sla_count": len(self._sla_contract.slas),
                "active_surface": self._active_surface,
            }

    def simulate_ecosystem_sla(self, body: Mapping[str, Any] | None = None) -> dict:
        """Run a dry-run simulation of ecosystem SLA compliance and burn rates."""
        with self._lock:
            if not self._is_ecosystem or not self._sla_engine:
                return {"status": "error", "message": "No active ecosystem SLA engine"}
            scenario = "normal_operations"
            if isinstance(body, Mapping):
                scenario = str(body.get("scenario", "normal_operations"))
            rep = self._sla_engine.simulate_sla_compliance(scenario=scenario)
            return {
                **rep.to_dict(),
                "report": rep.to_dict(),
                "status": "ok",
                "sla_status": rep.status,
            }



