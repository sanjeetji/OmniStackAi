# Model provider boundary and local Ollama adapter

R-005 defines the vendor-neutral Python boundary used by local, cloud, and private model adapters.
R-006 supplies the first adapter through Ollama's native HTTP API. Product and agent logic must
depend on `ModelProvider`, never on a provider SDK.

## Contract invariants

- Provider IDs are canonical, validated platform identifiers.
- Model capabilities describe measured states as unsupported, unverified, or verified.
- Every request has an idempotency-oriented request ID, exact model reference, explicit output
  budget, and finite timeout.
- Usage and latency are typed response evidence; streamed usage appears only on the final event.
- Provider health returns a stable detail code instead of exposing a raw provider error.
- Registry enumeration is deterministic; invalid, duplicate, and unknown providers use stable
  platform-owned errors.

## R-006 Ollama safety profile

- `OllamaProvider` accepts only `http://127.0.0.1:11434` or `http://localhost:11434` in Stage 0,
  disables environment proxies, and rejects redirects.
- Only explicitly configured model profiles are eligible. A capability cannot be marked verified
  without pinning the exact pulled-model digest; unprofiled model names are ignored.
- Native `/api/version`, `/api/tags`, and `/api/chat` responses are bounded and mapped to stable
  platform records and errors. Server error bodies and raw network errors do not cross the boundary.
- Each generation carries its own finite timeout and output ceiling. The adapter also bounds total
  response bytes, stream-line bytes, and concurrent calls, and closes streams on cancellation.
- Tool messages are rejected until a later task adds and evaluates the missing tool-call contract.

Use `task agent-engine:lint` and `task agent-engine:test` for deterministic offline verification.
With the configured model pulled and Ollama running locally, use
`task agent-engine:ollama:verify` for health, eligible-model discovery, one generation, and one
streaming conformance proof. That live command makes two local inference calls and zero cloud calls.

## R-007 Balanced Model Gateway router

`ModelGateway` is the only component that selects a provider. Product/agent code submits a
`RoutingTask` (its `TaskComplexity`, messages, output budget, and timeout) and never names a provider
or model. Under Balanced routing the gateway applies the Brief 18.1 escalation ladder and 84 routing
policy deterministically, with no model call needed to route:

- `L0` deterministic work is refused (`DeterministicWorkNotRoutableError`) — a deterministic tool
  must answer instead of a model.
- `L1`/`L2` (sub-L3) route to the local tier (`ollama-local`) resolved from the `ProviderRegistry`.
- `L3`/`L4` route to the cloud tier, which is unconfigured at Stage 0 and returns a stable
  `NoEligibleProviderError` (escalation required). High-risk work is never silently downgraded to the
  local model.
- If the resolved local provider reports `UNAVAILABLE` health, the gateway raises
  `ProviderUnavailableError` and never silently escalates to an unauthorized cloud provider.
- A conservative, deterministic token estimate guards each request against the resolved model's
  `safe_input_tokens` and `max_output_tokens` (`ContextBudgetExceededError`) rather than silently
  truncating.

`RoutingPolicy.cloud_model` stays `None` at Stage 0. When a later Tracker ID registers a cloud
API-key adapter behind the same `ModelProvider` boundary, populating `cloud_model` enables L3/L4
escalation with no gateway change. Routing is covered by offline tests in `tests/test_gateway.py`;
`task agent-engine:test` exercises it with zero network access and zero model calls.

### Running the platform locally through the gateway

With Ollama running and a local model pulled (e.g. `qwen2.5-coder:14b` or `qwen3.5:9b`), run:

```
OMNISTACKAI_OLLAMA_MODEL=qwen2.5-coder:14b task agent-engine:gateway:run
```

This opt-in command prints the deterministic routing decision for every complexity level, then
dispatches one L2 generation and one L1 stream through `ModelGateway` to the local Ollama provider.
It makes local inference calls and zero cloud calls, and is excluded from static `task verify`.
Select the model with `OMNISTACKAI_OLLAMA_MODEL`; override the prompt with `OMNISTACKAI_GATEWAY_PROMPT`.

## Deferred work

Cloud API-key adapters, fallback across providers, circuit breaking, durable cost accounting,
benchmark-backed capability promotion, richer context management, HTTP serving, and agent
orchestration remain deferred to their own Tracker IDs.
