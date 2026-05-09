from enum import Enum

from pydantic import BaseModel, Field


# ── Request ──

class AnalyzeRequest(BaseModel):
    """Parsed form fields for the analyze endpoint."""
    jd_text: str


# ── Response sub-models ──

class CandidateInfo(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    years_of_experience: str = ""
    highest_degree: str = ""
    school: str = ""
    major: str = ""


class SkillItem(BaseModel):
    name: str = ""
    level: str = ""  # 精通 / 熟练 / 了解


class WorkExperience(BaseModel):
    company: str = ""
    role: str = ""
    duration: str = ""
    highlights: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str = ""
    role: str = ""
    description: str = ""
    tech_stack: list[str] = Field(default_factory=list)


class DeepExtraction(BaseModel):
    """P1: Full structured candidate profile from deep LLM extraction."""
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    years_of_experience: str = ""
    highest_degree: str = ""
    school: str = ""
    major: str = ""
    skills: list[SkillItem] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certificates: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class DimensionScore(BaseModel):
    name: str
    score: int
    reason: str


class AnalysisData(BaseModel):
    candidate_info: CandidateInfo = Field(default_factory=CandidateInfo)
    overall_score: int = 0
    summary: str = ""
    dimensions: list[DimensionScore] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    risk_tips: list[str] = Field(default_factory=list)
    deep_extraction: DeepExtraction | None = None
    raw_json: dict = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    code: int = 200
    message: str = "解析成功"
    data: AnalysisData | None = None


# ── Async Task Models ──

class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    expired = "expired"


class QuickAnalysisData(BaseModel):
    """Phase 1 fast response: regex extraction + rule match + async task_id."""
    task_id: str
    status: str = "running"
    candidate_info: CandidateInfo = Field(default_factory=CandidateInfo)
    overall_score: int = 0
    summary: str = ""
    dimensions: list[DimensionScore] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    risk_tips: list[str] = Field(default_factory=list)
    raw_json: dict = Field(default_factory=dict)


class QuickAnalysisResponse(BaseModel):
    code: int = 200
    message: str = "快速分析完成"
    data: QuickAnalysisData | None = None


class TaskResultData(BaseModel):
    """Task state for polling endpoint."""
    task_id: str
    status: str
    phase: str = ""
    progress: int = 0
    result: AnalysisData | None = None
    fallback_result: AnalysisData | None = None
    error: str | None = None


class TaskStatusResponse(BaseModel):
    code: int = 200
    message: str = "任务状态获取成功"
    data: TaskResultData | None = None


class ErrorResponse(BaseModel):
    code: int
    message: str
    detail: str = ""
