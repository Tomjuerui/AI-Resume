from pydantic import BaseModel, Field


# ── Request ──

class AnalyzeRequest(BaseModel):
    """Parsed form fields for the analyze endpoint."""
    jd_text: str


# ── Response ──

class CandidateInfo(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""


class DimensionScore(BaseModel):
    name: str
    score: int
    reason: str


class AnalysisData(BaseModel):
    candidate_info: CandidateInfo = Field(default_factory=CandidateInfo)
    overall_score: int = 0
    dimensions: list[DimensionScore] = Field(default_factory=list)
    raw_json: dict = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    code: int = 200
    message: str = "解析成功"
    data: AnalysisData | None = None


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: str = ""
