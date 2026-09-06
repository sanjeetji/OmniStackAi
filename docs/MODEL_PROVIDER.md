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

## Deferred work

Cloud adapters, selection/routing, fallback, circuit breaking, durable accounting, benchmark-backed
capability promotion, HTTP serving, and agent orchestration remain deferred to their own Tracker IDs.
