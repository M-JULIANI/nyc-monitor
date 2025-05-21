from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from .agent import root_agent

app = FastAPI(
    title="RAG Backend",
    description="Backend service for RAG (Retrieval-Augmented Generation) application using Vertex AI RAG Engine",
    version="0.1.0"
)

class Question(BaseModel):
    text: str

class Answer(BaseModel):
    response: str

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.post("/ask", response_model=Answer)
async def ask_question(question: Question):
    try:
        response = await root_agent.ask(question.text)
        return Answer(response=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 