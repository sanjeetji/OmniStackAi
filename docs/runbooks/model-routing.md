# Which model does which job

The platform works with no paid key. It uses the free cloud tiers first and local Ollama as the last
resort. Adding a paid key raises quality without any code change.

```bash
scripts/models.sh            # each job's models in order, and which are out right now
scripts/models.sh --clear    # forget every "out" mark (after adding credit or a new key)
```

## The jobs

| Job | Order comes from |
|---|---|
| **Plans and chat edits** | `OMNISTACKAI_CLOUD_PROVIDER` first, then `OMNISTACKAI_FALLBACK_PROVIDERS`, ranked by the model scorecard (`scripts/model-eval.sh`, PC-085) when one exists. Local Ollama is always the last resort. `OMNISTACKAI_PREFER_LOCAL=1` keeps every call on this machine. |
| **Page design and repair** | `OMNISTACKAI_PAGE_CHAIN`, or the default: Anthropic, OpenAI, Gemini, OpenRouter's free models, NVIDIA, then Ollama. |

A provider whose key is not set is skipped. It is never called and never billed. So Anthropic and
OpenAI stay at the front of the page chain but are used only once you add `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY`. That is how a paid key raises quality: no change, just the key.

## When a provider is out

Free tiers run out. Gemini's free tier allows a fixed number of requests a day, and Groq limits
tokens per minute. The platform remembers which providers are out, so the next build or page goes
straight to one that can answer instead of asking the spent one again.

| What happened | Out for |
|---|---|
| Rate limited | The provider's own retry hint, or 1 minute |
| Daily quota spent | Until it resets: the next 08:00 UTC, which is midnight in California |
| Unavailable (5xx, timeout) | 30 seconds |
| Key refused or out of credit (401, 402, 403) | 1 hour, or until `scripts/models.sh --clear` |

- A provider that answers is marked available again at once.
- Local Ollama is never marked out.
- If every provider is out, the one back soonest is still tried; a stale mark never stops a build.

The marks are kept in `~/.omnistackai/model-health.json`, so the Studio, chat edits and the benchmark
all share them. They hold no secrets.

## What to expect

| Setup | What you get |
|---|---|
| Free tiers only, fresh in the morning | Plans in about a minute; pages designed by Gemini |
| Free tiers spent (a heavy day) | Plans and pages from NVIDIA or OpenRouter's free models, then local Ollama. Slower, but they still finish. |
| Local only (`OMNISTACKAI_PREFER_LOCAL=1`) | Everything on this machine; 5 to 10 minutes for a project |
| A paid key added | The best pages; nothing else to change |

See `scripts/benchmark.sh` for measuring the difference (docs/runbooks/benchmark.md).
