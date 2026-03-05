# AGENTS.md - AI Agent Instructions

This file provides context for AI coding agents working on this repository.

## Project Overview

This is a containerized AI agent proof of concept. A FastAPI app (`agent/app.py`) communicates with an Ollama LLM server to provide an agentic chat endpoint that supports tool calling. The stack runs via Docker Compose.

## Architecture

- `docker-compose.yml` - Defines three services: `ollama` (LLM server), `agent` (FastAPI app), `ollama-pull` (one-shot model downloader)
- `agent/app.py` - FastAPI application. Handles `/chat`, `/health`, `/led` endpoints. The `/chat` endpoint implements an agentic loop: it sends user messages to Ollama with tool definitions, executes any tool calls the model returns, feeds results back, and loops until the model produces a final text response. Max 5 tool rounds.
- `agent/tools/__init__.py` - Loads tool schemas from `tools.json` and aggregates executor functions into `ALL_TOOL_DEFINITIONS` and `ALL_TOOLS` dicts.
- `agent/tools/tools.json` - JSON array of Ollama function-calling tool schemas. This is the single source of truth for tool definitions sent to the model.
- `agent/tools/rgb_mixer.py` - Executor for `set_rgb_color`. Clamps RGB values 0-255, persists state to `/tmp/rgb_state.json`, returns status dict. Has a TODO placeholder for real GPIO PWM control on Raspberry Pi hardware.
- `agent/Dockerfile` - Python 3.14-slim image, installs dependencies from `requirements.txt`, runs `app.py`.
- `agent/requirements.txt` - `fastapi`, `uvicorn[standard]`, `httpx`, `pydantic`.

## Code Conventions

- Docstrings use triple single quotes (`'''`), always multi-line with opening/closing on their own lines
- No em-dashes or en-dashes; use regular hyphens (`-`)
- Tool definitions live in `agent/tools/tools.json` (not inline in Python)
- Tool executor functions are registered in `agent/tools/__init__.py` in the `ALL_TOOLS` dict
- Environment config via `os.getenv()` with sensible defaults in `app.py`
- Ollama communication uses `httpx.AsyncClient` with `/api/chat` (not `/api/generate`)

## How to Add a New Tool

1. Add the tool schema to `agent/tools/tools.json` following Ollama's function-calling format
2. Create a new Python module in `agent/tools/` with the executor function
3. Import and register the function in `agent/tools/__init__.py` in the `ALL_TOOLS` dict
4. The agentic loop in `app.py` will automatically pick it up - no changes needed there

## Key Environment Variables

- `OLLAMA_BASE_URL` - Ollama server URL (default: `http://localhost:11434`, set to `http://ollama:11434` in Docker)
- `MODEL_NAME` - Ollama model name (default: `gpt-oss:20b`)

## Testing

After `docker compose up -d`:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message": "Set LED to red"}'
curl http://localhost:8000/led
```

## Important Notes

- The model `gpt-oss:20b` requires ~13 GB RAM for inference. Docker Desktop must be allocated at least 16 GB.
- The `ollama-pull` service runs once to download the model, then exits. It is expected to show as stopped.
- Tool results are fed back to the model as `role: tool` messages in the conversation history.
- The `MAX_TOOL_ROUNDS` constant (5) prevents infinite tool-calling loops.
