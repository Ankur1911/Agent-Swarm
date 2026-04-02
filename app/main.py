import sys

from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# Validate configuration before any agent (and its heavy ML deps) is imported.
# On misconfiguration we print a concise, actionable message and exit with a
# non-zero status instead of dumping a stack trace.
from config import ConfigurationError, get_settings

try:
    get_settings()
except ConfigurationError as exc:
    print(f"[config] {exc}", file=sys.stderr)
    sys.exit(1)

from agents.router_agent import RouterAgent  # noqa: E402

app = FastAPI()
agent = RouterAgent()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with the correct origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    user_id: str
    message: str

@app.post("/ask")
async def ask_question(payload: AskRequest):
    try:
        response = agent.run(payload.user_id, payload.message)
        return JSONResponse(content=response)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
