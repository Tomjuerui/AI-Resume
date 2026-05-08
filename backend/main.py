from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.analyze import router as analyze_router
from core.config import settings

app = FastAPI(
    title="AI-Resume Analyzer",
    description="AI-powered resume analysis and JD matching",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(analyze_router)


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "AI-Resume Analyzer"}
