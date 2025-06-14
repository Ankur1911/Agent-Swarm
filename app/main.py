from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from agents.router_agent import RouterAgent 
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

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
