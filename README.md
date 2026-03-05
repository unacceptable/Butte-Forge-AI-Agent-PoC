# AI Agent Proof of Concept

An AI agent that runs entirely in Docker, powered by [Ollama](https://ollama.com) for local LLM inference. The agent can call tools - right now it controls an RGB LED diode via a color mixer (placeholder). Designed to deploy easily on a Raspberry Pi or any Docker host.

## What It Does

You send a chat message, the LLM decides whether to call a tool, executes it, and responds with the result. For example:

> "Set the LED to warm orange"

The agent picks RGB values, calls `set_rgb_color(255, 140, 0)`, and confirms the change.

## Quick Start

```bash
docker compose up -d
```

First run pulls the model (~13 GB for `gpt-oss:20b`). Watch the download:

```bash
docker compose logs -f ollama-pull
```

Once ready, test it:

```bash
# Health check
curl http://localhost:8000/health | jq

# Chat with tool calling
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Set the LED to bright purple"}'

# Read LED state directly
curl http://localhost:8000/led

# Set LED directly (no LLM)
curl -X POST http://localhost:8000/led \
  -H "Content-Type: application/json" \
  -d '{"red": 0, "green": 255, "blue": 128}'
```

## Services

| Service | Port | Purpose |
|---|---|---|
| `ollama` | 11434 | LLM inference server |
| `agent` | 8000 | FastAPI app with chat and tool-calling |
| `ollama-pull` | - | One-shot container that pulls the model on first run |

## API

Endpoint documentation found at http://localhost:8000/docs

## Configuration

Environment variables in `docker-compose.yml` under the `agent` service:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API URL |
| `MODEL_NAME` | `gpt-oss:20b` | Model for inference (must be pulled) |

To change models, update `MODEL_NAME` in both `agent` and `ollama-pull`, then:

```bash
docker compose down && docker compose up -d
```

## Adding Tools

1. Define the tool schema in `agent/tools/tools.json`
2. Write the executor function in a new module under `agent/tools/`
3. Register it in `agent/tools/__init__.py`

See `agent/tools/rgb_mixer.py` for an example.

## Project Structure

```
docker-compose.yml
agent/
  Dockerfile
  app.py                  # FastAPI app with agentic chat loop
  requirements.txt
  tools/
    __init__.py            # Loads tools.json + registers executors
    tools.json             # Tool definitions (Ollama function-calling format)
    rgb_mixer.py           # RGB LED tool executor
```

## Requirements

- Docker & Docker Compose v2+
- 16+ GB RAM for `gpt-oss:20b` (or 4 GB for smaller models like `tinyllama`)

## Increasing Docker Desktop Memory

By default Docker Desktop allocates limited RAM, which is not enough for larger models. To increase it:

1. Open **Docker Desktop**
2. Go to **Settings** (gear icon) -> **Resources** -> **Advanced**
3. Drag the **Memory** slider to at least **16 GB** (20 GB recommended for `gpt-oss:20b`)
4. Click **Apply & Restart**

After Docker restarts, bring the stack back up:

```bash
docker compose up -d
```

If the Ollama container gets killed during model loading, this is almost always a memory issue. Check with:

```bash
docker compose logs ollama --tail 20
```

Look for `signal: killed` - that means OOM. Increase Docker memory and retry.
