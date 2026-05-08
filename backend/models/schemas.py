from pydantic import BaseModel


# ── Request ──

class AnalyzeRequest(BaseModel):
    """Parsed form fields for the analyze endpoint."""
    jd_text: str


# ── Response ──

class CandidateInfo(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""


class DimensionScore(BaseModel):
    name: str
    score: int
    reason: str


class AnalysisData(BaseModel):
    candidate_info: CandidateInfo
    overall_score: int
    dimensions: list[DimensionScore]
    raw_json: dict = {}


class AnalysisResponse(BaseModel):
    code: int = 200
    message: str = "解析成功"
    data: AnalysisData | None = None
