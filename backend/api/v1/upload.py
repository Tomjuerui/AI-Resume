"""POST /api/v1/upload — standalone PDF upload & text extraction.

PRD P0: "RESTful API: /api/upload (单 PDF 上传及基础文本提取)"
"""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from core.exceptions import FileValidationError, PdfParseError, ScannedPdfError
from services import pdf_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class UploadResponse(BaseModel):
    code: int = 200
    message: str = "上传成功"
    filename: str = ""
    text_length: int = 0
    text_preview: str = ""  # First 500 chars
    raw_text: str = ""      # Full extracted text


def _validate_upload(file: UploadFile, file_bytes: bytes) -> None:
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"仅支持 PDF 格式，不支持 '{ext}' 格式的文件"
            )
    if len(file_bytes) > MAX_FILE_SIZE:
        size_mb = len(file_bytes) / (1024 * 1024)
        raise FileValidationError(
            f"文件大小 ({size_mb:.1f}MB) 超过限制 (10MB)"
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """Upload a PDF resume and return the extracted text.

    This is a lightweight endpoint that only performs PDF parsing.
    For full JD matching analysis, use POST /api/v1/analyze.
    """
    file_bytes = await file.read()
    _validate_upload(file, file_bytes)

    logger.info("Upload: %s, size=%d bytes", file.filename, len(file_bytes))

    suffix = Path(file.filename).suffix if file.filename else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        raw_text = await pdf_service.extract_text(tmp_path)
        cleaned_text = pdf_service.clean_text(raw_text)

        if pdf_service.is_scanned_pdf(cleaned_text):
            raise ScannedPdfError(
                "不支持扫描件，请提供文本型 PDF（非图片版）"
            )

        logger.info("Upload OK: %s, text=%d chars",
                     file.filename, len(cleaned_text))

        return UploadResponse(
            filename=file.filename or "unknown.pdf",
            text_length=len(cleaned_text),
            text_preview=cleaned_text[:500],
            raw_text=cleaned_text,
        )

    finally:
        tmp_path.unlink(missing_ok=True)
