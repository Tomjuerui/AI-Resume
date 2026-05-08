"""
JD matching & scoring engine.

Two-stage per PRD:
  P0 — Rule-based keyword matching (always runs, no LLM cost)
  P1 — LLM semantic scoring (optional, deep analysis)
"""

import re
import logging

logger = logging.getLogger(__name__)

# ── Keyword banks ──

TECH_SKILLS = {
    "python", "java", "javascript", "typescript", "golang", "go", "rust",
    "c++", "c#", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    "react", "vue", "angular", "node.js", "nodejs", "django", "flask",
    "fastapi", "spring", "springboot", "express", "next.js", "nuxt",
    "docker", "kubernetes", "k8s", "aws", "azure", "gcp", "阿里云",
    "terraform", "jenkins", "gitlab", "github", "ci/cd",
    "redis", "mongodb", "mysql", "postgresql", "oracle", "elasticsearch",
    "kafka", "rabbitmq", "nginx", "graphql", "rest", "grpc",
    "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
    "spark", "hadoop", "flink", "airflow",
    "linux", "shell", "bash", "git", "微服务", "分布式", "高并发",
    "机器学习", "深度学习", "人工智能", "大模型", "LLM",
}

SOFT_SKILLS = {
    "沟通", "协作", "领导", "项目", "团队", "管理", "演讲",
    "problem-solving", "agile", "scrum", "沟通能力", "团队合作",
    "leadership", "communication", "teamwork",
}

EDUCATION_KEYWORDS = {
    "本科", "硕士", "博士", "研究生", "学士", "MBA", "EMBA",
    "计算机", "软件工程", "数据科学", "人工智能", "数学", "统计",
    "bachelor", "master", "phd", "doctor", "computer science",
}

EXPERIENCE_PATTERNS = [
    (r"(\d+)\s*年.*?(经验|工作|开发|研发|从业)", "年工作经验"),
    (r"(\d+)\s*years?\s*(of\s*)?experience", "years experience"),
    (r"(高级|资深|专家|负责人|经理|总监|主管|lead|senior|staff|principal|manager|director)", "职位级别"),
]


# ── JD Keyword Extraction ──

def extract_jd_keywords(jd_text: str) -> dict[str, list[str]]:
    """Extract structured keywords from JD text."""
    jd_lower = jd_text.lower()

    skills: list[str] = []
    for kw in TECH_SKILLS:
        if kw.lower() in jd_lower:
            skills.append(kw)

    soft: list[str] = []
    for kw in SOFT_SKILLS:
        if kw.lower() in jd_lower:
            soft.append(kw)

    education: list[str] = []
    for kw in EDUCATION_KEYWORDS:
        if kw in jd_text or kw.lower() in jd_lower:
            education.append(kw)

    experience: list[str] = []
    for pattern, label in EXPERIENCE_PATTERNS:
        matches = re.findall(pattern, jd_text, re.IGNORECASE)
        if matches:
            for m in matches:
                val = m[0] if isinstance(m, tuple) else m
                experience.append(f"{val}{label}")

    return {
        "skills": skills,
        "soft_skills": soft,
        "education": education,
        "experience": experience,
    }


# ── Rule-Based Scoring ──

def _score_skills(resume_text: str, jd_keywords: dict) -> tuple[int, str]:
    """Score tech-skill overlap between resume and JD."""
    keywords = jd_keywords.get("skills", [])
    if not keywords:
        return 0, "JD中未明确列出技能要求"

    resume_lower = resume_text.lower()
    matched = [kw for kw in keywords if kw.lower() in resume_lower]
    score = min(100, int(len(matched) / len(keywords) * 100))

    if not matched:
        return 10, f"未在简历中发现JD要求的{len(keywords)}项技术关键词"
    elif score >= 80:
        return score, f"技能高度匹配：{', '.join(matched[:5])}"
    elif score >= 50:
        return score, f"部分技能匹配：{', '.join(matched[:5])}"
    else:
        return score, f"技能匹配度较低：仅匹配{', '.join(matched)}"


def _score_experience(resume_text: str, jd_keywords: dict) -> tuple[int, str]:
    """Score experience relevance."""
    keywords = jd_keywords.get("experience", [])
    if not keywords:
        return 50, "JD中未明确经验要求，给予基准分"

    resume_lower = resume_text.lower()
    matched = [kw for kw in keywords if kw.lower() in resume_lower]
    score = min(100, int(len(matched) / len(keywords) * 100))

    if not matched:
        return 30, "未发现与JD要求匹配的工作经验描述"
    else:
        return score, f"经验相关性：匹配到{', '.join(matched[:3])}"


def _score_education(resume_text: str, jd_keywords: dict) -> tuple[int, str]:
    """Score education level match."""
    keywords = jd_keywords.get("education", [])
    if not keywords:
        return 50, "JD中未明确学历要求，给予基准分"

    resume_lower = resume_text.lower()
    matched = [kw for kw in keywords if kw in resume_text or kw.lower() in resume_lower]
    score = min(100, int(len(matched) / len(keywords) * 100))

    if not matched:
        return 30, "未发现与JD要求匹配的学历或专业背景"
    else:
        return score, f"学历匹配：{', '.join(matched[:3])}"


def _score_soft_skills(resume_text: str, jd_keywords: dict) -> tuple[int, str]:
    """Score soft skills and overall fit."""
    keywords = jd_keywords.get("soft_skills", [])
    if not keywords:
        return 60, "JD中未明确列出软技能要求，给予基准分"

    resume_lower = resume_text.lower()
    matched = [kw for kw in keywords if kw.lower() in resume_lower]
    score = min(100, int(len(matched) / max(len(keywords), 1) * 100))

    if not matched:
        return 40, "未发现与JD匹配的软技能描述"
    else:
        return score, f"软技能部分匹配"


def _identify_risks(resume_text: str, jd_keywords: dict) -> list[str]:
    """Identify risk factors / gaps."""
    risks: list[str] = []

    skills = jd_keywords.get("skills", [])
    resume_lower = resume_text.lower()
    missing = [kw for kw in skills if kw.lower() not in resume_lower]
    if missing:
        top_missing = missing[:5]
        risks.append(f"缺失技能：{', '.join(top_missing)}")

    if len(resume_text) < 200:
        risks.append("简历内容偏少，可能存在信息不完整的情况")

    phone = re.search(r'1[3-9]\d{9}', resume_text)
    email = re.search(r'[\w.-]+@[\w.-]+\.\w+', resume_text)
    if not phone and not email:
        risks.append("简历中未找到联系方式（电话/邮箱），可能影响后续联系")

    return risks


def calculate_rule_match(resume_text: str, jd_text: str) -> dict:
    """Score resume against JD using rule-based keyword matching.

    Returns:
        dict with keys: overall_score, dimensions (list of {name, score, reason}), risks
    """
    if not jd_text or not jd_text.strip():
        return {
            "overall_score": 0,
            "dimensions": [],
            "risks": ["未提供岗位描述(JD)，无法进行匹配分析"],
        }

    jd_keywords = extract_jd_keywords(jd_text)
    logger.info("JD keywords extracted: skills=%d, soft=%d, edu=%d, exp=%d",
                len(jd_keywords["skills"]), len(jd_keywords["soft_skills"]),
                len(jd_keywords["education"]), len(jd_keywords["experience"]))

    # Score each dimension
    skill_score, skill_reason = _score_skills(resume_text, jd_keywords)
    exp_score, exp_reason = _score_experience(resume_text, jd_keywords)
    edu_score, edu_reason = _score_education(resume_text, jd_keywords)
    soft_score, soft_reason = _score_soft_skills(resume_text, jd_keywords)

    dimensions = [
        {"name": "技能匹配度", "score": skill_score, "reason": skill_reason},
        {"name": "经验相关性", "score": exp_score, "reason": exp_reason},
        {"name": "教育背景", "score": edu_score, "reason": edu_reason},
        {"name": "综合素养", "score": soft_score, "reason": soft_reason},
    ]

    # Weighted overall (skills 40%, experience 30%, education 15%, soft 15%)
    overall = int(
        skill_score * 0.40 +
        exp_score * 0.30 +
        edu_score * 0.15 +
        soft_score * 0.15
    )

    risks = _identify_risks(resume_text, jd_keywords)

    logger.info("Rule match: overall=%d, risks=%d", overall, len(risks))

    return {
        "overall_score": overall,
        "dimensions": dimensions,
        "risks": risks,
    }
