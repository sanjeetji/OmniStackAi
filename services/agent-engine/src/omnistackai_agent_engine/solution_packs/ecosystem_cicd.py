"""Ecosystem Multi-Surface CI/CD Workflow & GitHub Actions Orchestration (R-452).

Provides canonical CI/CD contracts, deterministic Python 3.13 stdlib-only GitHub
Actions YAML workflow generation (zero external dependencies, no PyYAML), in-process
DAG dependency validation (topological sort / cycle detection), deterministic contract
synthesis from ecosystem surfaces, and dry-run pipeline simulation.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class CIJobStep:
    """Individual step in a CI/CD job."""

    name: str
    uses: str | None = None
    run: str | None = None
    working_directory: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    with_args: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"name": self.name}
        if self.uses is not None:
            result["uses"] = self.uses
        if self.run is not None:
            result["run"] = self.run
        if self.working_directory is not None:
            result["working_directory"] = self.working_directory
        if self.env:
            result["env"] = dict(self.env)
        if self.with_args:
            result["with_args"] = dict(self.with_args)
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CIJobStep:
        return cls(
            name=str(data.get("name", "")),
            uses=data.get("uses"),
            run=data.get("run"),
            working_directory=data.get("working_directory"),
            env=dict(data.get("env", {})),
            with_args=dict(data.get("with_args", {})),
        )


@dataclass(frozen=True, slots=True)
class CIJob:
    """Single job in a CI/CD workflow, optionally scoped to a surface."""

    job_id: str
    name: str
    surface_slug: str | None = None
    runs_on: str = "ubuntu-latest"
    needs: tuple[str, ...] = ()
    steps: tuple[CIJobStep, ...] = ()
    services: dict[str, dict[str, Any]] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "job_id": self.job_id,
            "name": self.name,
            "runs_on": self.runs_on,
            "needs": list(self.needs),
            "steps": [step.to_dict() for step in self.steps],
        }
        if self.surface_slug is not None:
            result["surface_slug"] = self.surface_slug
        if self.services:
            result["services"] = dict(self.services)
        if self.env:
            result["env"] = dict(self.env)
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CIJob:
        return cls(
            job_id=str(data.get("job_id", "")),
            name=str(data.get("name", "")),
            surface_slug=data.get("surface_slug"),
            runs_on=str(data.get("runs_on", "ubuntu-latest")),
            needs=tuple(str(n) for n in data.get("needs", ())),
            steps=tuple(
                CIJobStep.from_dict(step) for step in data.get("steps", ())
            ),
            services=dict(data.get("services", {})),
            env=dict(data.get("env", {})),
        )


@dataclass(frozen=True, slots=True)
class CIWorkflow:
    """Top-level CI/CD workflow definition."""

    workflow_id: str
    name: str
    triggers: tuple[str, ...] = ("push", "pull_request", "workflow_dispatch")
    jobs: tuple[CIJob, ...] = ()
    env: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "triggers": list(self.triggers),
            "jobs": [j.to_dict() for j in self.jobs],
        }
        if self.env:
            result["env"] = dict(self.env)
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CIWorkflow:
        return cls(
            workflow_id=str(data.get("workflow_id", "")),
            name=str(data.get("name", "")),
            triggers=tuple(str(t) for t in data.get("triggers", ("push", "pull_request"))),
            jobs=tuple(CIJob.from_dict(j) for j in data.get("jobs", ())),
            env=dict(data.get("env", {})),
        )


@dataclass(frozen=True, slots=True)
class EcosystemCICDContract:
    """Canonical multi-surface CI/CD specification for an ecosystem."""

    ecosystem_id: str
    version: str = "1.0.0"
    workflows: tuple[CIWorkflow, ...] = ()
    surfaces_covered: tuple[str, ...] = ()
    required_gates: tuple[str, ...] = ("lint", "typecheck", "test", "build", "contract-verify")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ecosystem_id": self.ecosystem_id,
            "version": self.version,
            "workflows": [w.to_dict() for w in self.workflows],
            "surfaces_covered": list(self.surfaces_covered),
            "required_gates": list(self.required_gates),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EcosystemCICDContract:
        return cls(
            ecosystem_id=str(data.get("ecosystem_id", "")),
            version=str(data.get("version", "1.0.0")),
            workflows=tuple(CIWorkflow.from_dict(w) for w in data.get("workflows", ())),
            surfaces_covered=tuple(str(s) for s in data.get("surfaces_covered", ())),
            required_gates=tuple(str(g) for g in data.get("required_gates", ())),
        )


def _safe_yaml_str(val: str) -> str:
    """Return quoted or unquoted YAML string value safely."""
    if any(c in val for c in (":", "{", "}", "[", "]", ",", "&", "*", "#", "?", "|", "-", "<", ">", "=", "!", "%", "@", "`")):
        return f'"{val}"'
    return val


def generate_github_actions_workflow(workflow: CIWorkflow) -> str:
    """Generate deterministic, valid GitHub Actions YAML from a CIWorkflow.

    Python 3.13 stdlib only, zero external dependencies.
    """
    lines: list[str] = [
        f"name: {_safe_yaml_str(workflow.name)}",
        "",
        "on:",
    ]

    for trigger in workflow.triggers:
        if trigger in ("push", "pull_request"):
            lines.extend([
                f"  {trigger}:",
                "    branches:",
                "      - main",
                "      - master",
            ])
        elif trigger == "workflow_dispatch":
            lines.append("  workflow_dispatch:")
        else:
            lines.append(f"  {trigger}:")

    lines.append("")

    if workflow.env:
        lines.append("env:")
        for k in sorted(workflow.env.keys()):
            lines.append(f"  {k}: {_safe_yaml_str(str(workflow.env[k]))}")
        lines.append("")

    lines.append("jobs:")

    for job in workflow.jobs:
        lines.append(f"  {job.job_id}:")
        lines.append(f"    name: {_safe_yaml_str(job.name)}")
        lines.append(f"    runs-on: {job.runs_on}")

        if job.needs:
            lines.append("    needs:")
            for n in job.needs:
                lines.append(f"      - {n}")

        if job.services:
            lines.append("    services:")
            for s_name, s_spec in sorted(job.services.items()):
                lines.append(f"      {s_name}:")
                if "image" in s_spec:
                    lines.append(f"        image: {s_spec['image']}")
                if "env" in s_spec:
                    lines.append("        env:")
                    for ek, ev in sorted(s_spec["env"].items()):
                        lines.append(f"          {ek}: {_safe_yaml_str(str(ev))}")
                if "ports" in s_spec:
                    lines.append("        ports:")
                    for p in s_spec["ports"]:
                        lines.append(f"          - {_safe_yaml_str(str(p))}")
                if "options" in s_spec:
                    lines.append(f"        options: {_safe_yaml_str(str(s_spec['options']))}")

        if job.env:
            lines.append("    env:")
            for k, v in sorted(job.env.items()):
                lines.append(f"      {k}: {_safe_yaml_str(str(v))}")

        lines.append("    steps:")
        for step in job.steps:
            lines.append(f"      - name: {_safe_yaml_str(step.name)}")
            if step.uses is not None:
                lines.append(f"        uses: {step.uses}")
            if step.with_args:
                lines.append("        with:")
                for wk, wv in sorted(step.with_args.items()):
                    lines.append(f"          {wk}: {_safe_yaml_str(str(wv))}")
            if step.working_directory is not None:
                lines.append(f"        working-directory: {step.working_directory}")
            if step.run is not None:
                lines.append(f"        run: {step.run}")
            if step.env:
                lines.append("        env:")
                for ek, ev in sorted(step.env.items()):
                    lines.append(f"          {ek}: {_safe_yaml_str(str(ev))}")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def to_workflow_yaml(contract: EcosystemCICDContract) -> str:
    """Generate GitHub Actions YAML for the primary workflow in an EcosystemCICDContract."""
    if not contract.workflows:
        empty_wf = CIWorkflow(
            workflow_id="ecosystem-ci",
            name=f"{contract.ecosystem_id} CI/CD Pipeline",
            triggers=("push", "pull_request", "workflow_dispatch"),
            jobs=(),
        )
        return generate_github_actions_workflow(empty_wf)
    return generate_github_actions_workflow(contract.workflows[0])


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return cleaned or "app"


def synthesize_ecosystem_cicd(
    ecosystem_id: str,
    surfaces: Sequence[Mapping[str, Any] | Any],
) -> EcosystemCICDContract:
    """Derive a canonical EcosystemCICDContract from ecosystem surfaces."""
    raw_surfaces = [
        s.to_dict() if hasattr(s, "to_dict") else dict(s)
        for s in surfaces
    ]

    jobs: list[CIJob] = []
    surfaces_covered: list[str] = []
    surface_job_ids: list[str] = []

    for s in raw_surfaces:
        slug = str(s.get("slug") or _slug(str(s.get("app_name", "app"))))
        kind = str(s.get("surface_kind", "web"))
        app_name = str(s.get("app_name") or slug)
        surfaces_covered.append(slug)

        job_id = f"test-{slug}"
        surface_job_ids.append(job_id)

        # Detect runtime / framework
        runtime = str(s.get("runtime_target") or "").lower()
        combined_desc = f"{kind.lower()} {slug.lower()} {runtime}"
        is_go = "go" in runtime or "go" in kind.lower()
        is_python = "python" in runtime or "python" in kind.lower() or ("api" in slug.lower() and not is_go and "node" not in combined_desc)

        if is_python:
            # Python FastAPI Backend
            steps = (
                CIJobStep(name="Checkout repository", uses="actions/checkout@v4"),
                CIJobStep(
                    name="Set up Python 3.13",
                    uses="actions/setup-python@v5",
                    with_args={"python-version": "3.13", "cache": "pip"},
                ),
                CIJobStep(
                    name="Install dependencies",
                    run="pip install -r services/api/requirements.txt",
                ),
                CIJobStep(
                    name="Type-check & byte-compile",
                    run="python -m compileall services/api/app",
                ),
                CIJobStep(
                    name="Run test suite",
                    run="pytest -q services/api/tests",
                    env={
                        "POSTGRES_HOST": "localhost",
                        "POSTGRES_PORT": "5432",
                        "POSTGRES_USER": "omnistackai",
                        "POSTGRES_PASSWORD": "omnistackai_secret",
                        "POSTGRES_DB": f"{slug}_test",
                    },
                ),
            )
            services = {
                "postgres": {
                    "image": "postgres:16-alpine",
                    "env": {
                        "POSTGRES_USER": "omnistackai",
                        "POSTGRES_PASSWORD": "omnistackai_secret",
                        "POSTGRES_DB": f"{slug}_test",
                    },
                    "ports": ["5432:5432"],
                    "options": "--health-cmd pg_isready --health-interval 5s --health-timeout 5s --health-retries 5",
                }
            }
            job = CIJob(
                job_id=job_id,
                name=f"{app_name} (Python API) Verification",
                surface_slug=slug,
                runs_on="ubuntu-latest",
                steps=steps,
                services=services,
            )
        elif is_go:
            # Go Backend
            steps = (
                CIJobStep(name="Checkout repository", uses="actions/checkout@v4"),
                CIJobStep(
                    name="Set up Go 1.24",
                    uses="actions/setup-go@v5",
                    with_args={"go-version": "1.24", "cache": "true"},
                ),
                CIJobStep(
                    name="Vet source code",
                    run="go vet ./...",
                    working_directory="services/api",
                ),
                CIJobStep(
                    name="Run test suite",
                    run="go test -v ./...",
                    working_directory="services/api",
                    env={
                        "POSTGRES_HOST": "localhost",
                        "POSTGRES_PORT": "5432",
                        "POSTGRES_USER": "omnistackai",
                        "POSTGRES_PASSWORD": "omnistackai_secret",
                        "POSTGRES_DB": f"{slug}_test",
                    },
                ),
                CIJobStep(
                    name="Compile binary",
                    run="go build ./...",
                    working_directory="services/api",
                ),
            )
            services = {
                "postgres": {
                    "image": "postgres:16-alpine",
                    "env": {
                        "POSTGRES_USER": "omnistackai",
                        "POSTGRES_PASSWORD": "omnistackai_secret",
                        "POSTGRES_DB": f"{slug}_test",
                    },
                    "ports": ["5432:5432"],
                    "options": "--health-cmd pg_isready --health-interval 5s --health-timeout 5s --health-retries 5",
                }
            }
            job = CIJob(
                job_id=job_id,
                name=f"{app_name} (Go API) Verification",
                surface_slug=slug,
                runs_on="ubuntu-latest",
                steps=steps,
                services=services,
            )
        else:
            # Next.js Web / Admin / Portal
            steps = (
                CIJobStep(name="Checkout repository", uses="actions/checkout@v4"),
                CIJobStep(
                    name="Set up Node.js 20",
                    uses="actions/setup-node@v4",
                    with_args={"node-version": "20"},
                ),
                CIJobStep(
                    name="Install pnpm",
                    uses="pnpm/action-setup@v3",
                    with_args={"version": "9"},
                ),
                CIJobStep(
                    name="Install dependencies",
                    run="pnpm install",
                    working_directory=f"apps/{slug}" if not slug.startswith("apps/") else slug,
                ),
                CIJobStep(
                    name="Type-check",
                    run="pnpm exec tsc --noEmit",
                    working_directory=f"apps/{slug}" if not slug.startswith("apps/") else slug,
                ),
                CIJobStep(
                    name="Lint code",
                    run="pnpm run lint",
                    working_directory=f"apps/{slug}" if not slug.startswith("apps/") else slug,
                ),
                CIJobStep(
                    name="Production build",
                    run="pnpm run build",
                    working_directory=f"apps/{slug}" if not slug.startswith("apps/") else slug,
                ),
            )
            job = CIJob(
                job_id=job_id,
                name=f"{app_name} Web Verification",
                surface_slug=slug,
                runs_on="ubuntu-latest",
                steps=steps,
            )
        jobs.append(job)

    # Ecosystem Integration Verification Job (depends on all surface jobs)
    integration_steps = (
        CIJobStep(name="Checkout repository", uses="actions/checkout@v4"),
        CIJobStep(
            name="Set up Python 3.13",
            uses="actions/setup-python@v5",
            with_args={"python-version": "3.13"},
        ),
        CIJobStep(
            name="Verify ecosystem package checksums",
            run="task agent-engine:solution-pack:ecosystem -- verify",
        ),
        CIJobStep(
            name="Verify multi-surface gateway deployment",
            run="task agent-engine:solution-pack:ecosystem -- deploy --compose",
        ),
        CIJobStep(
            name="Verify cross-surface data sync contract",
            run="task agent-engine:solution-pack:ecosystem -- sync",
        ),
    )
    integration_job = CIJob(
        job_id="ecosystem-integration",
        name="Ecosystem Multi-Surface Integration Gate",
        runs_on="ubuntu-latest",
        needs=tuple(surface_job_ids),
        steps=integration_steps,
    )
    jobs.append(integration_job)

    primary_workflow = CIWorkflow(
        workflow_id="ecosystem-ci",
        name=f"Ecosystem Multi-Surface CI/CD ({ecosystem_id})",
        triggers=("push", "pull_request", "workflow_dispatch"),
        jobs=tuple(jobs),
        env={"CI": "true", "OMNISTACKAI_OFFLINE": "true"},
    )

    return EcosystemCICDContract(
        ecosystem_id=ecosystem_id,
        version="1.0.0",
        workflows=(primary_workflow,),
        surfaces_covered=tuple(surfaces_covered),
        required_gates=("lint", "typecheck", "test", "build", "contract-verify"),
    )


class EcosystemCICDEngine:
    """Engine validating DAG dependencies and simulating multi-surface CI/CD pipeline execution."""

    def __init__(self, contract: EcosystemCICDContract) -> None:
        self._contract = contract

    @property
    def contract(self) -> EcosystemCICDContract:
        return self._contract

    def validate_dag(self, workflow_id: str | None = None) -> tuple[bool, str]:
        """Validate that the job dependency graph in the workflow has no cycles."""
        wf = self._get_workflow(workflow_id)
        if wf is None:
            return False, f"Workflow '{workflow_id}' not found."

        job_ids = {j.job_id for j in wf.jobs}
        adj: dict[str, list[str]] = {j.job_id: [] for j in wf.jobs}
        in_degree: dict[str, int] = {j.job_id: 0 for j in wf.jobs}

        for j in wf.jobs:
            for dep in j.needs:
                if dep not in job_ids:
                    return False, f"Job '{j.job_id}' depends on unknown job '{dep}'."
                adj[dep].append(j.job_id)
                in_degree[j.job_id] += 1

        queue = deque([jid for jid, deg in in_degree.items() if deg == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(job_ids):
            return False, "Cycle detected in CI/CD job dependency graph."
        return True, "Valid acyclic workflow DAG."

    def topological_sort(self, workflow_id: str | None = None) -> tuple[CIJob, ...]:
        """Return jobs in valid execution order using topological sort."""
        wf = self._get_workflow(workflow_id)
        if wf is None:
            return ()

        job_map = {j.job_id: j for j in wf.jobs}
        adj: dict[str, list[str]] = {j.job_id: [] for j in wf.jobs}
        in_degree: dict[str, int] = {j.job_id: 0 for j in wf.jobs}

        for j in wf.jobs:
            for dep in j.needs:
                if dep in job_map:
                    adj[dep].append(j.job_id)
                    in_degree[j.job_id] += 1

        queue = deque(sorted([jid for jid, deg in in_degree.items() if deg == 0]))
        ordered: list[CIJob] = []

        while queue:
            node = queue.popleft()
            ordered.append(job_map[node])
            for neighbor in sorted(adj[node]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) != len(wf.jobs):
            raise ValueError(f"Cycle detected in CI/CD workflow '{wf.workflow_id}'; cannot perform topological sort.")

        return tuple(ordered)

    def simulate_pipeline_run(
        self,
        workflow_id: str | None = None,
        trigger: str = "push",
    ) -> dict[str, Any]:
        """Perform a deterministic offline dry-run simulation of the CI/CD pipeline."""
        is_valid, msg = self.validate_dag(workflow_id)
        if not is_valid:
            return {
                "success": False,
                "error": msg,
                "trigger": trigger,
                "ecosystem_id": self._contract.ecosystem_id,
            }

        ordered_jobs = self.topological_sort(workflow_id)
        simulated_jobs: list[dict[str, Any]] = []
        total_duration_ms = 0

        for j in ordered_jobs:
            step_logs: list[dict[str, Any]] = []
            job_duration_ms = 0
            for step in j.steps:
                # Deterministic step simulation duration
                step_dur = 1200 + (len(step.name) * 45)
                job_duration_ms += step_dur
                step_logs.append({
                    "step_name": step.name,
                    "action": step.uses or step.run or "custom",
                    "status": "passed",
                    "duration_ms": step_dur,
                    "exit_code": 0,
                })

            simulated_jobs.append({
                "job_id": j.job_id,
                "job_name": j.name,
                "surface_slug": j.surface_slug,
                "runs_on": j.runs_on,
                "needs": list(j.needs),
                "status": "passed",
                "duration_ms": job_duration_ms,
                "steps": step_logs,
            })
            total_duration_ms += job_duration_ms

        return {
            "success": True,
            "status": "passed",
            "trigger": trigger,
            "ecosystem_id": self._contract.ecosystem_id,
            "workflow_id": workflow_id or (self._contract.workflows[0].workflow_id if self._contract.workflows else "ecosystem-ci"),
            "total_jobs": len(simulated_jobs),
            "total_duration_ms": total_duration_ms,
            "required_gates": list(self._contract.required_gates),
            "jobs": simulated_jobs,
        }

    def _get_workflow(self, workflow_id: str | None = None) -> CIWorkflow | None:
        if not self._contract.workflows:
            return None
        if workflow_id is None:
            return self._contract.workflows[0]
        for w in self._contract.workflows:
            if w.workflow_id == workflow_id:
                return w
        return None
