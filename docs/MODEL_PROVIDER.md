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

## R-008 Cloud API-key adapters (multi-provider, key-activated)

Cloud adapters live behind the same `ModelProvider` boundary and are built on the Python standard
library over HTTPS — no vendor SDK, no external dependency:

- **OpenAI-compatible** (`OpenAICompatibleProvider`) serves `openai`, `openrouter`, and `groq`.
- **Anthropic** (`AnthropicProvider`) uses the Messages API.
- **Google Gemini** (`GeminiProvider`) uses `generateContent`.

Each provider is **key-activated**: it is registered only when its API key is present in the
environment. Keys are read from the environment, sent only as the provider auth header, and never
placed in logs, errors, records, or a provider's `repr`. Every provider has a documented default
model (overridable via `OMNISTACKAI_<PROVIDER>_MODEL`) and conservative shared budgets
(`OMNISTACKAI_CLOUD_*`). As of R-010, `stream()` is true incremental Server-Sent-Events streaming for
every cloud provider (OpenAI-compatible, Anthropic, Gemini), yielding ordered delta events and a final
event with measured usage — matching the local Ollama adapter's streaming contract.

`build_gateway_from_env()` (`bootstrap.py`) always registers local Ollama, registers each cloud
provider whose key is set, and selects the L3/L4 cloud tier from `OMNISTACKAI_CLOUD_PROVIDER`
(`none` by default). Selecting a provider whose key is absent is a configuration error, never a
silent local downgrade. To enable a cloud tier, set that provider's key and the selector in the
untracked `.env`:

```
ANTHROPIC_API_KEY=...              # only the provider you use
OMNISTACKAI_CLOUD_PROVIDER=anthropic
```

Then `task agent-engine:gateway:run` shows the cloud provider registered and L3/L4 routing to it,
while L1/L2 stay on local Ollama. With no key set, everything runs locally at zero cloud cost.

## R-009 Usage & cost accounting

`ModelGateway` accepts an optional `recorder=UsageLedger()`. When set, every dispatch writes exactly
one immutable, **metadata-only** `UsageRecord` (provider, model, tier, complexity, token counts,
latency, finish reason, success/error code) — never message content, response text, or a secret
(Brief 90). Accounting is observational: it never changes the returned response or the raised error.

`PriceBook` computes an exact USD estimate with `decimal.Decimal`. `DEFAULT_PRICE_BOOK` ships
illustrative, operator-configurable cloud prices and prices local Ollama at zero; unknown models are
recorded as **unpriced** rather than guessed. `UsageLedger.summary()` aggregates overall and
per-provider/per-model totals, token sums, cost, success/failure counts, deterministic p50/p95
latency (nearest-rank), unpriced-call count, and cost per successful call — the inputs to optimizing
cost per successful accepted change (Brief 18.4, 68, 92.15).

`build_gateway_from_env(recorder=...)` threads a ledger into the gateway, and
`task agent-engine:gateway:run` prints the summary after its live run (local Ollama shows $0.000000).

## R-221 Cross-provider fallback and circuit breaking

`RoutingPolicy` accepts an optional ordered `fallback` chain of `ModelDescriptor`. With none set the
gateway behaves exactly as before (single provider). When set, `generate`/`stream` try the primary
then each fallback candidate that is registered, in-budget, and whose circuit is closed. Fail-over is
**explicit** (only along the configured chain) and happens **only on retriable errors**
(`ProviderUnavailableError`, `ProviderTimeoutError`, `ProviderHTTPError`); a non-retriable error
(budget, unknown model, unsupported request) is raised immediately. Streaming fails over only before
the first event; a mid-stream error propagates. When every candidate is skipped or failing, the
gateway raises `AllProvidersFailedError` (a single-provider config still surfaces its own error).

`ModelGateway(..., breaker=CircuitBreaker())` adds a per-provider circuit breaker: after
`failure_threshold` consecutive failures a provider is skipped for `cooldown_seconds`, then half-opens
for a trial; success resets it. The breaker is deterministic (injectable clock) and thread-safe. Every
attempt is still recorded by the accounting ledger, so fail-over cost is visible.

## Deferred work

Durable/persistent cost storage, benchmark-backed capability promotion, richer context management,
HTTP serving, and agent orchestration remain deferred to their own Tracker IDs.
