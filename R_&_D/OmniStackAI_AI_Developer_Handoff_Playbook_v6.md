# OmniStackAI — AI + Developer Start, Resume and Handoff Playbook v6

Date: 2026-09-05

This file is the operational companion to the Master Blueprint and Implementation Brief. It is deliberately short enough to give directly to Codex, Claude Code, Cursor, another coding agent, or a new developer.

## 1. What to give the AI tool

Give it the repository, not a giant pasted chat. The repository must contain `AGENTS.md`, `docs/START_HERE.md`, `.ai/PROJECT_STATE.yaml`, `.ai/CURRENT_TASK.yaml`, `.ai/HANDOFF.md`, IR/ADRs and the task tracker/export.

### Initial prompt — first session

```text
You are implementing OmniStackAI from this repository.

Start by reading, in order:
1) AGENTS.md
2) docs/START_HERE.md
3) .ai/PROJECT_STATE.yaml
4) .ai/CURRENT_TASK.yaml
5) only the relevant IR/ADR/policy files referenced by the current task.

Then inspect git status/branch/HEAD and run `task doctor`.
Do not edit code yet.
Report:
- current phase and task ID,
- what is already completed,
- exact acceptance criteria,
- expected affected paths/blast radius,
- dependencies/blockers,
- verification commands,
- the single next implementation step.

After that, execute only the current task. Keep changes scoped. Run required verification. Update state/work-log/handoff files before stopping. Never expose secrets or deploy to production without the required approval.
```

### Resume prompt — after a day/week/new chat

```text
Resume this repository from durable project state; do not rely on previous chat.
Read AGENTS.md, docs/START_HERE.md, .ai/PROJECT_STATE.yaml, .ai/CURRENT_TASK.yaml and .ai/HANDOFF.md.
Verify the recorded branch/HEAD against Git and inspect any uncommitted diff.
Run `task doctor` and re-run the last relevant verification from HANDOFF.md.
If Git and state disagree, repair the state files first and explain the discrepancy.
Then continue exactly from `next_action`; do not restart completed work and do not jump to a later roadmap task.
Before stopping, refresh CURRENT_TASK.yaml, WORK_LOG.md and HANDOFF.md with exact evidence and next command.
```

### Review-only prompt

```text
Do not implement. Audit the current task against its acceptance criteria, expected blast radius, architecture policies, security rules and verification evidence. Return blocking issues first. Do not broaden scope unless the evidence proves the current design cannot satisfy the requirement.
```

## 2. Human developer start

Clone -> read START_HERE -> `task doctor` -> `task bootstrap` -> `task ai:status` -> checkout/create the task branch -> run baseline verification -> implement the current task -> `task verify` -> update handoff -> PR.

A developer must be able to determine current state without asking the previous developer what happened in chat.

## 3. Stop checklist

Before leaving work:

```text
[ ] task state is accurate
[ ] branch and HEAD recorded
[ ] changed files listed
[ ] acceptance criteria marked only with evidence
[ ] last tests/verification recorded with result
[ ] blockers/risks recorded
[ ] next_action is one concrete action
[ ] next_command is executable
[ ] IR/ADR updated if architecture/product truth changed
[ ] no secret copied into logs/handoff
[ ] stable work committed when appropriate
```

## 4. Model setup policy

The application talks only to the Model Gateway. Configure one or more provider profiles:

```text
ollama-local     -> local Ollama-compatible endpoint, e.g. a validated Qwen coding model
openai-byok      -> OpenAI API key through SecretProvider
anthropic-byok   -> Anthropic API key through SecretProvider
private-openai   -> enterprise OpenAI-compatible endpoint
```

No feature code imports provider SDKs. A provider can be enabled/disabled without changing task/domain logic.

Every exact model configuration is registered with measured context budget, tool-call support, structured-output support, quality eval, latency/concurrency and data-policy classification. A cheap local model receives production coding tasks only after it meets the acceptance threshold for that task class.

## 5. Recommended repository commands

```text
task doctor          # validate toolchains/config/services
task bootstrap       # deterministic local dependency/bootstrap
task dev              # start local platform
task lint             # affected/static checks
task test             # standard test suite
task verify           # CI-equivalent scoped verification
task ai:status        # print phase/task/branch/HEAD/next action
task ai:handoff       # validate + render/update handoff payload
task env:check        # typed environment/config validation
task security:quick   # secrets/dependency/SAST baseline
task eval:model       # provider/model conformance + quality eval
```

Commands are a contract: they must work the same for humans and agents and return non-zero on failure.

## 6. R&D verdict

V5 is a strong R&D blueprint, but it was more complete as an architecture than as a *drop-a-repo-into-any-coding-agent and resume deterministically* specification. V6 fills that gap. The highest-risk remaining work is implementation validation: benchmark sandbox/runtime choices, prove model routing quality/cost, prove crash-resume/idempotency, prove tenant isolation, and measure real build/deploy reliability before calling the platform production-ready.
