import asyncio
import logging
import re
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, Form, UploadFile

from core.exceptions import FileValidationError, LLMCallError, ScannedPdfError
from models.schemas import (
    AnalysisData, AnalysisResponse,
    CandidateInfo, DeepExtraction, DimensionScore,
    ProjectItem, QuickAnalysisData, QuickAnalysisResponse,
    SkillItem, TaskResultData, TaskStatus, TaskStatusResponse,
    WorkExperience,
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


def _candidate_from_extraction(extraction: dict) -> CandidateInfo:
    return CandidateInfo(
        name=extraction.get("name", ""),
        phone=extraction.get("phone", ""),
        email=extraction.get("email", ""),
        address=extraction.get("address", ""),
        years_of_experience=extraction.get("years_of_experience", ""),
        highest_degree=extraction.get("highest_degree", ""),
        school=extraction.get("school", ""),
        major=extraction.get("major", ""),
    )


def _safe_task_error(exc: Exception) -> str:
    """Return a generic error message for task failures; log details internally."""
    logger.debug("Internal task error detail: %r", exc)
    return "AI deep analysis failed; showing rule-based fallback result."


def _dict_items(value: object) -> list[dict]:
    """Filter a list to only dict items, ignoring strings or other primitives LLM may emit."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalize_deep_extraction(deep_result: dict) -> DeepExtraction:
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

    return DeepExtraction(
        name=deep_result.get("name", ""),
        phone=deep_result.get("phone", ""),
        email=deep_result.get("email", ""),
        address=deep_result.get("address", ""),
        years_of_experience=deep_result.get("years_of_experience", ""),
        highest_degree=deep_result.get("highest_degree", ""),
        school=deep_result.get("school", ""),
        major=deep_result.get("major", ""),
        skills=[SkillItem(**s) for s in _dict_items(deep_result.get("skills", []))],
        work_experience=[WorkExperience(**w) for w in _dict_items(deep_result.get("work_experience", []))],
        projects=[ProjectItem(**p) for p in _dict_items(deep_result.get("projects", []))],
        certificates=deep_result.get("certificates", []),
        languages=normalized_languages,
    )


async def _run_deep_analysis(
    task_id: str,
    file_md5: str,
    jd_text: str,
    cleaned_text: str,
    fallback_data: AnalysisData,
) -> None:
    """Phase 2: LLM deep extraction + rubric scoring in background."""
    try:
        await cache_service.set_task_state(task_id, {
            "task_id": task_id,
            "status": TaskStatus.running.value,
            "phase": "llm_deep_extraction",
            "progress": 30,
            "result": None,
            "fallback_result": fallback_data.model_dump(),
            "error": None,
        })

        extraction: dict = {}
        deep_extraction: DeepExtraction | None = None
        try:
            deep_result = await llm_service.extract_resume_deep(cleaned_text)
            extraction = deep_result
            deep_extraction = _normalize_deep_extraction(deep_result)
            logger.info("Task %s: deep extraction OK, skills=%d", task_id, len(deep_extraction.skills))
        except Exception as e:
            logger.warning("Task %s: deep extraction failed, using regex fallback", task_id, exc_info=e)
            extraction = fallback_data.raw_json

        await cache_service.set_task_state(task_id, {
            "task_id": task_id,
            "status": TaskStatus.running.value,
            "phase": "llm_rubric_scoring",
            "progress": 70,
            "result": None,
            "fallback_result": fallback_data.model_dump(),
            "error": None,
        })

        candidate_info = _candidate_from_extraction(extraction)
        overall_score = fallback_data.overall_score
        summary = fallback_data.summary
        dimensions = fallback_data.dimensions
        missing_skills = fallback_data.missing_skills

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
            logger.info("Task %s: rubric scoring OK, overall=%d", task_id, overall_score)
        except Exception as e:
            logger.warning("Task %s: rubric scoring failed, using rule-based", task_id, exc_info=e)

        final_data = AnalysisData(
            candidate_info=candidate_info,
            overall_score=overall_score,
            summary=summary,
            dimensions=dimensions,
            missing_skills=missing_skills,
            risk_tips=fallback_data.risk_tips,
            deep_extraction=deep_extraction,
            raw_json=extraction,
        )
        final_response = AnalysisResponse(code=200, message="解析成功", data=final_data)

        await cache_service.set_final_result(file_md5, jd_text, final_response.model_dump())
        await cache_service.set_task_state(task_id, {
            "task_id": task_id,
            "status": TaskStatus.succeeded.value,
            "phase": "completed",
            "progress": 100,
            "result": final_data.model_dump(),
            "fallback_result": fallback_data.model_dump(),
            "error": None,
        })
        logger.info("Task %s: completed successfully", task_id)

    except Exception as e:
        logger.exception("Task %s: failed", task_id)
        await cache_service.set_task_state(task_id, {
            "task_id": task_id,
            "status": TaskStatus.failed.value,
            "phase": "failed",
            "progress": 100,
            "result": None,
            "fallback_result": fallback_data.model_dump(),
            "error": _safe_task_error(e),
        })


@router.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
):
    """Upload a PDF resume and JD.

    Phase 1 (fast, <2s): PDF extraction + regex basic info + rule match + returns immediately with task_id.
    Phase 2 (background): LLM deep extraction + rubric scoring. Poll GET /analyze/tasks/{task_id}.
    """
    file_bytes = await file.read()
    validate_file(file, file_bytes)

    jd_text = jd_text.strip()
    if len(jd_text) < MIN_JD_LENGTH:
        raise FileValidationError(
            f"岗位描述文本过短（{len(jd_text)}字符），请至少填写{MIN_JD_LENGTH}个字符"
        )

    logger.info("Received file: %s, size=%d bytes, jd_text_len=%d",
                file.filename, len(file_bytes), len(jd_text))

    # Check final cache first (complete async result)
    file_md5 = pdf_service.compute_md5_bytes(file_bytes)
    final_cached = await cache_service.get_final_result(file_md5, jd_text)
    if final_cached:
        logger.info("Final cache hit for file_md5=%s, returning complete result", file_md5)
        return AnalysisResponse(**final_cached)

    # Check for existing in-progress task (idempotent submit)
    existing_task_id = await cache_service.get_task_index(file_md5, jd_text)
    if existing_task_id:
        existing_state = await cache_service.get_task_state(existing_task_id)
        if existing_state and existing_state.get("status") in ("pending", "running"):
            logger.info("Reusing existing task: %s", existing_task_id)
            fb = existing_state.get("fallback_result") or {}
            ci_data = fb.get("candidate_info", {})
            return QuickAnalysisResponse(
                code=200,
                message="分析任务已存在",
                data=QuickAnalysisData(
                    task_id=existing_task_id,
                    status=existing_state["status"],
                    candidate_info=CandidateInfo(**ci_data) if ci_data else CandidateInfo(),
                    overall_score=fb.get("overall_score", 0),
                    summary=fb.get("summary", ""),
                    dimensions=[DimensionScore(**d) for d in fb.get("dimensions", [])],
                    missing_skills=fb.get("missing_skills", []),
                    risk_tips=fb.get("risk_tips", []),
                    raw_json=fb.get("raw_json", {}),
                ),
            )

    # Save to temp file
    suffix = Path(file.filename).suffix if file.filename else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        # Extract + clean PDF text
        raw_text = await pdf_service.extract_text(tmp_path)
        cleaned_text = pdf_service.clean_text(raw_text)
        logger.info("Cleaned text: %d chars", len(cleaned_text))

        # Scanned PDF check
        if pdf_service.is_scanned_pdf(cleaned_text):
            raise ScannedPdfError("不支持扫描件，请提供文本型 PDF（非图片版）")

        # Phase 1: regex basic info extraction (no LLM call)
        extraction = _regex_extract(cleaned_text)
        candidate_info = _candidate_from_extraction(extraction)

        # Phase 1: rule-based matching (pure CPU, always runs)
        rule_match = match_service.calculate_rule_match(cleaned_text, jd_text)
        dimensions = [DimensionScore(**d) for d in rule_match.get("dimensions", [])]
        missing_skills = [
            r.replace("缺失技能：", "") for r in rule_match.get("risks", [])
            if r.startswith("缺失技能：")
        ]

        # Create async task and store fallback data
        task_id = str(uuid4())
        fallback_data = AnalysisData(
            candidate_info=candidate_info,
            overall_score=rule_match.get("overall_score", 0),
            summary="规则初评完成，AI 深度分析进行中",
            dimensions=dimensions,
            missing_skills=missing_skills,
            risk_tips=rule_match.get("risks", []),
            deep_extraction=None,
            raw_json=extraction,
        )

        await cache_service.set_task_state(task_id, {
            "task_id": task_id,
            "status": TaskStatus.running.value,
            "phase": "queued",
            "progress": 10,
            "result": None,
            "fallback_result": fallback_data.model_dump(),
            "error": None,
        })
        await cache_service.set_task_index(file_md5, jd_text, task_id)

        # Launch Phase 2 in background (LLM deep extraction + rubric scoring)
        asyncio.create_task(
            _run_deep_analysis(task_id, file_md5, jd_text, cleaned_text, fallback_data)
        )

        # Fire-and-forget OSS upload
        if file.filename:
            asyncio.create_task(_upload_to_oss(file_bytes, file.filename))

        return QuickAnalysisResponse(
            code=200,
            message="快速分析完成",
            data=QuickAnalysisData(
                task_id=task_id,
                status="running",
                candidate_info=candidate_info,
                overall_score=fallback_data.overall_score,
                summary=fallback_data.summary,
                dimensions=dimensions,
                missing_skills=missing_skills,
                risk_tips=fallback_data.risk_tips,
                raw_json=extraction,
            ),
        )

    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/analyze/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Poll async deep-analysis task status."""
    state = await cache_service.get_task_state(task_id)
    if not state:
        return TaskStatusResponse(
            code=404,
            message="任务不存在或已过期",
            data=TaskResultData(
                task_id=task_id,
                status=TaskStatus.expired.value,
                phase="expired",
                progress=100,
                result=None,
                fallback_result=None,
                error="task not found or expired",
            ),
        )

    return TaskStatusResponse(
        code=200,
        message="任务状态获取成功",
        data=TaskResultData(**state),
    )
