# Building on a local model (Ollama)

The platform can build with no cloud provider at all: planning, the compile repairs and page
design all run on a model on this machine through [Ollama](https://ollama.com). It costs nothing
and needs no key; it is slower than the cloud providers.

## Which model

`scripts/omnistack.sh status` shows what is installed, the model recommended for this machine
(from its memory - on Apple silicon the GPU shares it) and the model builds will use:

| Machine memory | Recommended | Size on disk |
|---|---|---|
| 40 GB or more | `qwen2.5-coder:32b` | about 20 GB |
| 14 GB or more | `qwen2.5-coder:14b` | about 9 GB |
| 8 GB or more | `qwen2.5-coder:7b` | about 5 GB |
| less | `qwen2.5-coder:3b` | about 2 GB |

Install one with `ollama pull <model>` and name it in `.env` as `OMNISTACKAI_OLLAMA_MODEL`. The
setting is checked against what Ollama has installed when the Studio starts: a model that is not
installed is replaced by the best installed one that fits the machine (the Studio log says which
and why), and with none installed the message names the model to pull. Nothing is downloaded
automatically - a model is gigabytes.

## Local only

Set `OMNISTACKAI_PREFER_LOCAL=1` in `.env` (or the environment) and restart. Every model call of a
build then stays on this machine, page design included. A project pinned to its own provider
keeps it. Without the setting, the local model is the last fallback after the configured cloud
providers.
