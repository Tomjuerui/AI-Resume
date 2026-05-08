import logging
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from core.exceptions import FileValidationError, LLMCallError, ScannedPdfError
from models.schemas import AnalysisData, AnalysisResponse, CandidateInfo, DimensionScore
from services import pdf_service, llm_service, match_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/octet-stream"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _regex_extract(text: str) -> dict:
    """Basic regex-based extraction as fallback when LLM is unavailable."""
    result: dict = {"name": "", "phone": "", "email": "", "address": ""}

    # Phone: Chinese mobile
    phone_match = re.search(r'1[3-9]\d{9}', text)
    if phone_match:
        result["phone"] = phone_match.group()
        logger.info("Regex extracted phone: %s", result["phone"])

    # Email
    email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
    if email_match:
        result["email"] = email_match.group()
        logger.info("Regex extracted email: %s", result["email"])

    # Name: simple heuristic — look for "姓名：XXX" pattern
    name_match = re.search(r'姓名[：:]\s*(\S{2,4})', text)
    if name_match:
        result["name"] = name_match.group(1)
        logger.info("Regex extracted name: %s", result["name"])

    # Address: look for city/province patterns
    addr_match = re.search(
        r'(?:地址|所在地|现居)[：:]\s*(.{5,40}?)(?:\n|$)',
        text
    )
    if addr_match:
        result["address"] = addr_match.group(1).strip()

    return result


def validate_file(file: UploadFile, file_bytes: bytes) -> None:
    """Validate the uploaded file (extension, MIME, size)."""
    if file.filename:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"仅支持 PDF 格式，不支持 '{ext}' 格式的文件"
            )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning("Unexpected MIME type: %s for file %s",
                       file.content_type, file.filename)

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
    """Upload a PDF resume and JD. Returns extracted info + match scores."""
    # 1. Read file bytes + validate
    file_bytes = await file.read()
    validate_file(file, file_bytes)

    logger.info("Received file: %s, size=%d bytes, jd_text_len=%d",
                file.filename, len(file_bytes), len(jd_text))

    # 2. Save to temp file
    suffix = Path(file.filename).suffix if file.filename else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        # 3. Extract + clean PDF text
        raw_text = await pdf_service.extract_text(tmp_path)
        logger.info("Raw text: %d chars", len(raw_text))

        cleaned_text = pdf_service.clean_text(raw_text)
        logger.info("Cleaned text: %d chars", len(cleaned_text))

        # 4. Scanned PDF check
        if pdf_service.is_scanned_pdf(cleaned_text):
            raise ScannedPdfError(
                "不支持扫描件，请提供文本型 PDF（非图片版）"
            )

        # 5. Extract candidate info (LLM preferred, regex fallback)
        try:
            extraction = await llm_service.extract_resume_info(cleaned_text)
            logger.info("LLM extraction succeeded")
        except LLMCallError as e:
            logger.warning("LLM extraction unavailable, using regex: %s", e)
            extraction = _regex_extract(cleaned_text)

        candidate_info = CandidateInfo(
            name=extraction.get("name", ""),
            phone=extraction.get("phone", ""),
            email=extraction.get("email", ""),
            address=extraction.get("address", ""),
        )

        # 6. Rule-based keyword matching (P0)
        rule_match = match_service.calculate_rule_match(cleaned_text, jd_text)

        # 7. LLM semantic matching (P1) — try, fallback to rule-based
        overall_score = rule_match["overall_score"]
        dimensions = [
            DimensionScore(**d) for d in rule_match["dimensions"]
        ]
        risks = rule_match.get("risks", [])

        try:
            llm_match = await llm_service.match_resume_to_jd(cleaned_text, jd_text)
            # LLM takes priority for scores when available
            if llm_match.get("dimensions"):
                dimensions = [DimensionScore(**d) for d in llm_match["dimensions"]]
            if llm_match.get("overall_score", 0) > 0:
                overall_score = llm_match["overall_score"]
            if llm_match.get("risks"):
                risks = llm_match["risks"]
            logger.info("LLM match used: overall=%d", overall_score)
        except LLMCallError as e:
            logger.warning("LLM match failed, using rule-based: %s", e)
        except Exception as e:
            logger.warning("LLM match unexpected error, using rule-based: %s", e)

        return AnalysisResponse(
            code=200,
            message="解析成功",
            data=AnalysisData(
                candidate_info=candidate_info,
                overall_score=overall_score,
                dimensions=dimensions,
                risk_tips=risks,
                raw_json=extraction,
            ),
        )

    finally:
        tmp_path.unlink(missing_ok=True)
