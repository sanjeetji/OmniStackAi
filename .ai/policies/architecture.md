# Architecture Policy

- Instant Browser Preview precedes QR, physical-device, and cloud-device options.
- PostgreSQL is the OmniStackAI control-plane database.
- `modules/` contains logical in-process boundaries unless measured evidence approves a split.
- Provider-specific SDKs stay inside provider adapters and never enter product/domain logic.
- Cloud execution of untrusted code is isolated.
- Secrets and signing keys are brokered capabilities, never prompt or source context.
- Deterministic tools precede model calls; context is retrieved progressively and budgeted.
- Change impact defines the allowed blast radius for every task.
- Advanced infrastructure and native/device work require their roadmap prerequisites.

