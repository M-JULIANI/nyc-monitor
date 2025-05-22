from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .agent import root_agent

app = FastAPI(
    title="RAG Backend",
    description="Backend service for RAG (Retrieval-Augmented Generation) application using Vertex AI RAG Engine",
    version="0.1.0",
    root_path="/api"  # This ensures OpenAPI docs work correctly behind the proxy
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return {"status": "healthy", "service": "rag-backend"}
