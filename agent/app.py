'''
AI Agent - conversational agent with tool-calling, backed by Ollama.

Exposes a FastAPI server with:
  POST /chat   - send a message; the agent may invoke tools before replying
  GET  /health - readiness check (verifies Ollama connectivity)
  GET  /led    - read the current RGB LED state
  POST /led    - directly set the RGB LED color (bypasses the LLM)
'''

import json
import os
import logging
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from tools import ALL_TOOL_DEFINITIONS, ALL_TOOLS
from tools.rgb_mixer import STATE_FILE, set_rgb_color

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-oss:20b")

SYSTEM_PROMPT = (
    "You are a helpful AI assistant running on a Raspberry Pi that controls "
    "hardware peripherals. You have access to an RGB LED diode. When the user "
    "asks you to set, change, or mix a color, use the set_rgb_color tool. "
    "Always confirm the color you set. Keep answers concise."
)

MAX_TOOL_ROUNDS = 5  # safety limit on agentic loop iterations

app = FastAPI(title="AI Agent", version="0.2.0")

class ChatRequest(BaseModel):
    '''
    Chat request model.
    '''
    message: str


class ToolCall(BaseModel):
    '''
    Tool call model.
    '''
    name: str
    args: dict
    result: dict


class ChatResponse(BaseModel):
    '''
    Chat response model.
    '''
    response: str
    tool_calls: list[ToolCall] = []
    model: str


class LEDRequest(BaseModel):
    '''
    RGB LED color request model.
    '''
    red: int = Field(..., ge=0, le=255)
    green: int = Field(..., ge=0, le=255)
    blue: int = Field(..., ge=0, le=255)


async def _ollama_chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    '''
    Call Ollama /api/chat and return the parsed response body.
    '''
    payload: dict = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=300) as client:
        resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()


@app.get("/health")
async def health():
    '''
    Check that Ollama is reachable and the model is available.
    '''
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            model_ready = any(MODEL_NAME in m for m in models)
            return {
                "status": "ok" if model_ready else "model_not_loaded",
                "ollama": "reachable",
                "model": MODEL_NAME,
                "available_models": models,
                "tools": [t["function"]["name"] for t in ALL_TOOL_DEFINITIONS],
            }
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"Ollama unreachable: {exc}") from exc


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    '''
    Agentic chat endpoint.

    Sends the user message to the model along with available tool
    definitions.  If the model responds with tool calls, we execute
    them locally and feed the results back, looping until the model
    produces a final text response.
    '''
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": req.message},
    ]
    executed_tools: list[ToolCall] = []

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            data = await _ollama_chat(messages, tools=ALL_TOOL_DEFINITIONS)
            assistant_msg = data.get("message", {})

            # ── Check for tool calls ────────────────────────────────
            tool_calls = assistant_msg.get("tool_calls")
            if not tool_calls:
                # No tool calls → final answer
                break

            # Append the assistant's message (with tool_calls) to history
            messages.append(assistant_msg)

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = tc["function"]["arguments"]
                logger.info("Tool call: %s(%s)", fn_name, fn_args)

                executor = ALL_TOOLS.get(fn_name)
                if executor is None:
                    result = {"error": f"Unknown tool: {fn_name}"}
                else:
                    try:
                        result = executor(**fn_args)
                    except (ValueError, TypeError, KeyError) as e:
                        result = {"error": str(e)}

                executed_tools.append(
                    ToolCall(name=fn_name, args=fn_args, result=result)
                )

                # Feed tool result back to the model
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                })

            # Loop back so the model can see the tool results
        else:
            # Exceeded MAX_TOOL_ROUNDS - ask the model one more time
            # without tools to force a text reply
            data = await _ollama_chat(messages, tools=None)
            assistant_msg = data.get("message", {})

        return ChatResponse(
            response=assistant_msg.get("content", ""),
            tool_calls=executed_tools,
            model=MODEL_NAME,
        )

    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}") from exc


@app.get("/led")
async def get_led():
    '''
    Return the current RGB LED state.
    '''
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))

    return {
        "red": 0,
        "green": 0,
        "blue": 0,
        "hex": "#000000"
    }


@app.post("/led")
async def set_led(req: LEDRequest):
    '''
    Directly set the LED color (without going through the LLM).
    '''
    return set_rgb_color(red=req.red, green=req.green, blue=req.blue)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
