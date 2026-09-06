# Model provider boundary

R-005 defines the vendor-neutral Python boundary used by future local, cloud, and private model
adapters. Product and agent logic must depend on `ModelProvider`, never on a provider SDK.

## Contract invariants

- Provider IDs are canonical, validated platform identifiers.
- Model capabilities describe measured states as unsupported, unverified, or verified.
- Every request has an idempotency-oriented request ID, exact model reference, explicit output
  budget, and finite timeout.
- Usage and latency are typed response evidence; streamed usage appears only on the final event.
- Provider health returns a stable detail code instead of exposing a raw provider error.
- Registry enumeration is deterministic; invalid, duplicate, and unknown providers use stable
  platform-owned errors.

## Deferred work

R-005 does not implement Ollama or cloud adapters, selection/routing, fallback, circuit breaking,
budget enforcement, accounting, HTTP serving, or agent orchestration. Those changes require their
own Tracker IDs and tests against this contract.
