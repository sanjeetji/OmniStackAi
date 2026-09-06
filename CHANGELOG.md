# Changelog

2026-09-06  R-009  Added deterministic usage and cost accounting for the model gateway: immutable metadata-only usage records (no content/secret), a configurable Decimal price book (local Ollama zero, unknown unpriced), and an aggregating ledger with per-provider/model breakdowns, p50/p95 latency, and cost per successful call
2026-09-06  R-008  Added key-activated cloud ModelProvider adapters (Anthropic, OpenAI, Gemini, OpenRouter, Groq) behind the shared boundary with an env bootstrap; standard-library only, no vendor SDK, keys env-only, local Ollama stays default and no key means no cloud call
2026-09-06  R-007  Added the deterministic Balanced Model Gateway router — escalation ladder (L0 refused), sub-L3 local Ollama routing, L3/L4 escalation-required, conservative context-budget guard, and no silent cloud fallback — with 14 offline tests
2026-09-06  R-006  Added the bounded loopback-only Ollama ModelProvider adapter with conservative model eligibility, offline conformance tests, and live generation/streaming proof
2026-09-06  R-005  Added the vendor-neutral Python ModelProvider contract, validated model-call records, deterministic registry, and CI-equivalent tests
2026-09-06  R-004  Added the minimal Go control-plane with typed config, PostgreSQL readiness, structured logs, graceful shutdown, tests, and live Compose verification
2026-09-06  R-003  Added loopback-only local Ollama configuration, model discovery, lifecycle commands, and live inference verification
2026-09-06  R-002  Added pinned local PostgreSQL+pgvector Compose bootstrap, versioned initial migration, and deterministic lifecycle/verification commands
2026-09-06  R-001  Bootstrapped the Section 74 monorepo skeleton and Stage 0 start, verification, state, and handoff contract
