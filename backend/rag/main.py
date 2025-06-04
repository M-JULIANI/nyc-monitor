from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from pydantic import BaseModel
from .agent import root_agent, investigate_alert
from .investigation.state_manager import AlertData
import os
from datetime import datetime

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")  # Set this in your .env

app = FastAPI(
    title="RAG Backend",
    description="Backend service for RAG (Retrieval-Augmented Generation) application using Vertex AI RAG Engine",
    version="0.1.0",
    root_path="/api"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nyc-monitor.app",  # Production custom domain
        "https://atlas-frontend-290750569862.us-central1.run.app",  # Original Cloud Run URL
        "http://localhost:3000",  # Local development
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# OAuth2 (Google)
# Not used for Google, but required by FastAPI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_google_token(token: str = Depends(oauth2_scheme)):
    try:
        idinfo = id_token.verify_oauth2_token(
            token, grequests.Request(), GOOGLE_CLIENT_ID)
        return idinfo
    except Exception:
        raise HTTPException(
            status_code=401, detail="Invalid authentication credentials")


class Question(BaseModel):
    text: str


class Answer(BaseModel):
    response: str


class InvestigationResult(BaseModel):
    investigation_id: str
    status: str
    findings: str
    artifacts: list
    confidence_score: float


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.post("/ask", response_model=Answer)
@limiter.limit("5/minute")
async def ask_question(
    request: Request,
    question: Question,
    user=Depends(verify_google_token)
):
    try:
        # Create a mock alert based on the question for demonstration
        alert_data = AlertData(
            alert_id=f"user_query_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            severity=5,  # Default severity for user queries
            event_type="user_investigation",
            location="NYC",  # Default location
            summary=question.text,
            timestamp=datetime.utcnow(),
            sources=["user_input"]
        )

        # Use the investigation system
        response_text = investigate_alert(alert_data)

        return Answer(response=response_text)
    except Exception as e:
        print("ERROR in /ask:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/investigate", response_model=InvestigationResult)
@limiter.limit("3/minute")  # Lower limit for more intensive operations
async def investigate_alert_endpoint(
    request: Request,
    alert_data: AlertData,
    user=Depends(verify_google_token)
):
    """
    Investigate a specific alert using the multi-agent system.

    This endpoint triggers a full investigation including:
    - Research agent collecting data and artifacts
    - Analysis of findings
    - Generation of investigation report
    """
    try:
        # Run the investigation
        findings = investigate_alert(alert_data)

        # For now, return mock investigation results
        # TODO: Implement actual artifact collection and analysis
        investigation_result = InvestigationResult(
            investigation_id=alert_data.alert_id,
            status="completed",
            findings=findings,
            artifacts=[
                f"media_{alert_data.event_type}_0_0.png",
                f"screenshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
            ],
            confidence_score=0.8
        )

        return investigation_result

    except Exception as e:
        print("ERROR in /investigate:", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "rag-backend"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
