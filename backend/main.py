import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.analyze import router as analyze_router
from core.config import settings
from core.exceptions import (
    CacheError,
    FileValidationError,
    LLMCallError,
    OSSUploadError,
    PdfParseError,
    ScannedPdfError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

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


# ── Global Exception Handlers ──

@app.exception_handler(FileValidationError)
async def file_validation_handler(request: Request, exc: FileValidationError):
    return JSONResponse(
        status_code=400,
        content={"code": 400, "message": str(exc), "data": None},
    )


@app.exception_handler(PdfParseError)
async def pdf_parse_handler(request: Request, exc: PdfParseError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": str(exc), "data": None},
    )


@app.exception_handler(ScannedPdfError)
async def scanned_pdf_handler(request: Request, exc: ScannedPdfError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": str(exc), "data": None},
    )


@app.exception_handler(LLMCallError)
async def llm_call_handler(request: Request, exc: LLMCallError):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": str(exc), "data": None},
    )


@app.exception_handler(OSSUploadError)
async def oss_upload_handler(request: Request, exc: OSSUploadError):
    logger.error("OSS upload error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "文件存储失败，请稍后重试", "data": None},
    )


@app.exception_handler(CacheError)
async def cache_error_handler(request: Request, exc: CacheError):
    logger.error("Cache error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器缓存异常", "data": None},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "AI-Resume Analyzer"}
