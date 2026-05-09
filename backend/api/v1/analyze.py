import asyncio
import logging
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from core.exceptions import FileValidationError, LLMCallError, ScannedPdfError
from models.schemas import (
    AnalysisData, AnalysisResponse,
    CandidateInfo, DeepExtraction, DimensionScore,
    ProjectItem, SkillItem, WorkExperience,
)
from services import pdf_service, llm_service, match_service, cache_service, oss_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

ALLOWED_EXTENSIONS = {".pdf"}
ALLOWED_MIME_TYPES = {"application/pdf", "application/octet-stream"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MIN_JD_LENGTH = 10  # Minimum meaningful JD text length


def _regex_extract(text: str) -> dict:
    """Basic regex-based extraction as fallback when LLM is unavailable."""
    result: dict = {"name": "", "phone": "", "email": "", "address": ""}

    phone_match = re.search(r'1[3-9]\d{9}', text)
    if phone_match:
        result["phone"] = phone_match.group()

    email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
    if email_match:
        result["email"] = email_match.group()

    name_match = re.search(r'姓名[：:]\s*(\S{2,4})', text)
    if name_match:
        result["name"] = name_match.group(1)

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


async def _upload_to_oss(file_bytes: bytes, filename: str) -> None:
    """Background task: upload PDF to OSS for archival."""
    try:
        url = await oss_service.upload_pdf(file_bytes, filename)
        logger.info("OSS upload OK: %s -> %s", filename, url)
    except Exception as e:
        logger.warning("OSS upload skipped: %s", e)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
):
    """Upload a PDF resume and JD. Returns deep extraction + rubric-based match scores."""
    # 1. Read file bytes + validate
    file_bytes = await file.read()
    validate_file(file, file_bytes)

    # Validate JD text
    jd_text = jd_text.strip()
    if len(jd_text) < MIN_JD_LENGTH:
        raise FileValidationError(
            f"岗位描述文本过短（{len(jd_text)}字符），请至少填写{MIN_JD_LENGTH}个字符"
        )

    logger.info("Received file: %s, size=%d bytes, jd_text_len=%d",
                file.filename, len(file_bytes), len(jd_text))

    # 1.5 Check cache (by file MD5 + JD hash)
    file_md5 = pdf_service.compute_md5_bytes(file_bytes)
    cached = await cache_service.get_cached_result(file_md5, jd_text)
    if cached:
        logger.info("Cache hit for file_md5=%s, returning cached result", file_md5)
        return AnalysisResponse(**cached)

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

        # ── 5. Deep Extraction (P1) — candidate profile ──
        deep_extraction: DeepExtraction | None = None
        extraction: dict = {}
        try:
            deep_result = await llm_service.extract_resume_deep(cleaned_text)
            extraction = deep_result  # also use for basic info
            # Normalize languages: LLM may return strings or {name, level} dicts
            raw_languages = deep_result.get("languages", [])
            normalized_languages: list[str] = []
            for lang in raw_languages:
                if isinstance(lang, dict) and lang.get("name"):
                    level = lang.get("level", "")
                    normalized_languages.append(
                        f"{lang['name']} ({level})" if level else lang["name"]
                    )
                elif isinstance(lang, str):
                    normalized_languages.append(lang)

            deep_extraction = DeepExtraction(
                name=deep_result.get("name", ""),
                phone=deep_result.get("phone", ""),
                email=deep_result.get("email", ""),
                address=deep_result.get("address", ""),
                years_of_experience=deep_result.get("years_of_experience", ""),
                highest_degree=deep_result.get("highest_degree", ""),
                school=deep_result.get("school", ""),
                major=deep_result.get("major", ""),
                skills=[SkillItem(**s) for s in deep_result.get("skills", [])],
                work_experience=[WorkExperience(**w) for w in deep_result.get("work_experience", [])],
                projects=[ProjectItem(**p) for p in deep_result.get("projects", [])],
                certificates=deep_result.get("certificates", []),
                languages=normalized_languages,
            )
            logger.info("Deep extraction OK: skills=%d, work=%d, projects=%d",
                        len(deep_extraction.skills),
                        len(deep_extraction.work_experience),
                        len(deep_extraction.projects))
        except LLMCallError as e:
            logger.warning("Deep extraction failed, using basic: %s", e)
            try:
                extraction = await llm_service.extract_resume_info(cleaned_text)
            except LLMCallError:
                extraction = _regex_extract(cleaned_text)

        candidate_info = CandidateInfo(
            name=extraction.get("name", ""),
            phone=extraction.get("phone", ""),
            email=extraction.get("email", ""),
            address=extraction.get("address", ""),
            years_of_experience=extraction.get("years_of_experience", ""),
            highest_degree=extraction.get("highest_degree", ""),
            school=extraction.get("school", ""),
            major=extraction.get("major", ""),
        )

        # ── 6. Rule-based matching (P0, always runs as fallback) ──
        rule_match = match_service.calculate_rule_match(cleaned_text, jd_text)

        # ── 7. AI Rubric Scoring (P1) ──
        overall_score = rule_match["overall_score"]
        summary = ""
        dimensions: list[DimensionScore] = []
        missing_skills: list[str] = []

        try:
            rubric = await llm_service.score_resume_vs_jd(cleaned_text, jd_text)
            if rubric.get("dimensions"):
                dimensions = [DimensionScore(**d) for d in rubric["dimensions"]]
            if rubric.get("overall_score", 0) > 0:
                overall_score = rubric["overall_score"]
            if rubric.get("summary"):
                summary = rubric["summary"]
            if rubric.get("missing_skills"):
                missing_skills = rubric["missing_skills"]
            logger.info("Rubric scoring used: overall=%d, summary=%s",
                        overall_score, summary[:50])
        except LLMCallError as e:
            logger.warning("Rubric scoring failed, using rule-based: %s", e)
            dimensions = [DimensionScore(**d) for d in rule_match["dimensions"]]
            missing_skills = [
                r.replace("缺失技能：", "") for r in rule_match.get("risks", [])
                if r.startswith("缺失技能：")
            ]
        except Exception as e:
            logger.warning("Rubric scoring unexpected error, using rule-based: %s", e)
            dimensions = [DimensionScore(**d) for d in rule_match["dimensions"]]

        response = AnalysisResponse(
            code=200,
            message="解析成功",
            data=AnalysisData(
                candidate_info=candidate_info,
                overall_score=overall_score,
                summary=summary,
                dimensions=dimensions,
                missing_skills=missing_skills,
                risk_tips=rule_match.get("risks", []),
                deep_extraction=deep_extraction,
                raw_json=extraction,
            ),
        )

        # Cache the result for future identical requests
        await cache_service.set_cached_result(
            file_md5, jd_text, response.model_dump()
        )

        # Fire-and-forget OSS upload (non-blocking)
        if file.filename:
            asyncio.create_task(
                _upload_to_oss(file_bytes, file.filename)
            )

        return response

    finally:
        tmp_path.unlink(missing_ok=True)
