# Local models

Founder Stage 0 uses Ollama as its only configured model runtime. The endpoint stays on loopback and
the selected model comes from environment configuration.

## Configuration

Set these values in ignored `.env`:

```text
OMNISTACKAI_OLLAMA_BASE_URL=http://127.0.0.1:11434
OMNISTACKAI_OLLAMA_MODEL=qwen2.5-coder:14b
```

The model value is a local default, not a product capability claim. Future provider-registry work
must discover installed models and score their exact versions/configurations through the evaluation
suite before routing real L2 work.

## Commands

```text
task ollama:config
task ollama:serve
task ollama:status
task ollama:models
task ollama:pull
task ollama:verify
```

`ollama:serve` runs in the foreground. On macOS, starting Ollama.app is an equivalent runtime
operation. `ollama:pull` downloads only the model selected in `.env`. `ollama:verify` first checks
that the model appears in Ollama's model list, then makes one short local generation request. It
does not use a cloud provider.
