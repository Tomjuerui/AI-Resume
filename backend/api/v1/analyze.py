import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from core.exceptions import FileValidationError, ScannedPdfError
from models.schemas import AnalysisData, AnalysisResponse, CandidateInfo
from services import pdf_service, llm_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/octet-stream"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_file(file: UploadFile, file_bytes: bytes) -> None:
    """Validate the uploaded file (extension, MIME, size)."""
    # Check extension
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"仅支持 PDF 格式，不支持 '{ext}' 格式的文件"
            )

    # Check MIME type (if available)
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        # Log but don't block — some browsers send octet-stream for PDF
        logger.warning("Unexpected MIME type: %s for file %s",
                       file.content_type, file.filename)

    # Check size
    if len(file_bytes) > MAX_FILE_SIZE:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise FileValidationError(
            f"文件大小 ({size_mb:.1f}MB) 超过限制 (10MB)"
        )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
):
    """Upload a PDF resume and a JD, get AI-powered structured extraction."""
    # 1. Read file bytes + validate
    file_bytes = await file.read()
    validate_file(file, file_bytes)

    logger.info("Received file: %s, size=%d bytes, jd_text_len=%d",
                file.filename, len(file_bytes), len(jd_text))

    # 2. Save to temp file for processing
    suffix = Path(file.filename).suffix if file.filename else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        # 3. Extract text from PDF
        raw_text = await pdf_service.extract_text(tmp_path)
        logger.info("Raw text extracted: %d chars", len(raw_text))

        # 4. Clean text
        cleaned_text = pdf_service.clean_text(raw_text)
        logger.info("Cleaned text: %d chars", len(cleaned_text))

        # 5. Check for scanned PDF
        if pdf_service.is_scanned_pdf(cleaned_text):
            raise ScannedPdfError(
                "不支持扫描件，请提供文本型 PDF（非图片版）"
            )

        # 6. Extract candidate info via LLM (P0: name, phone, email, address)
        extraction = await llm_service.extract_resume_info(cleaned_text)

        candidate_info = CandidateInfo(
            name=extraction.get("name", ""),
            phone=extraction.get("phone", ""),
            email=extraction.get("email", ""),
            address=extraction.get("address", ""),
        )

        return AnalysisResponse(
            code=200,
            message="解析成功",
            data=AnalysisData(
                candidate_info=candidate_info,
                overall_score=0,
                dimensions=[],
                raw_json=extraction,
            ),
        )

    finally:
        # Clean up temp file per PRD requirements
        tmp_path.unlink(missing_ok=True)
