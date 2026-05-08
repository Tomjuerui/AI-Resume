import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from models.schemas import AnalysisResponse

router = APIRouter(prefix="/api/v1")


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    file: UploadFile = File(...),
    jd_text: str = Form(...),
):
    """Upload a PDF resume and a JD, get AI-powered match analysis."""
    # Save uploaded file to temp location
    suffix = Path(file.filename).suffix if file.filename else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        # TODO: wire up service calls
        # text = await pdf_service.extract_text(tmp_path)
        # resume_json = await llm_service.extract_resume_info(text, jd_text)
        # match = match_service.calculate_match(resume_json, jd_text)

        return AnalysisResponse(
            code=200,
            message="解析成功",
            data=None,  # no actual analysis yet
        )
    finally:
        tmp_path.unlink(missing_ok=True)
