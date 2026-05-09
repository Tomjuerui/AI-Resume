import json
import re
import logging

from openai import AsyncOpenAI
from core.config import settings, PROVIDER_CONFIG
from core.exceptions import LLMCallError
from core.pii_mask import mask_name

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

# ═══════════════════════════════════════════════════
#  P0 — Basic field extraction (name, phone, email, address)
# ═══════════════════════════════════════════════════

EXTRACTION_PROMPT = """你是一位专业的简历解析助手。请从以下简历文本中提取候选人的基本信息。

要求：
1. 仔细阅读简历内容
2. 提取以下字段（如果简历中没有明确信息，字段值设为空字符串 ""）：
   - name: 候选人姓名（中文或英文全名）
   - phone: 联系电话（手机号或座机，去掉无关字符）
   - email: 电子邮箱地址
   - address: 通讯地址或所在城市
3. 只返回 JSON 对象，不要添加任何解释、注释或 Markdown 标记

简历文本：
---
{resume_text}
---

请以如下 JSON 格式返回提取结果：
{{"name": "...", "phone": "...", "email": "...", "address": "..."}}"""


# ═══════════════════════════════════════════════════
#  P1 — Deep extraction (education, projects, skills, certificates)
# ═══════════════════════════════════════════════════

DEEP_EXTRACTION_PROMPT = """你是一位专业的简历解析专家。请从以下简历文本中深度提取候选人的全面信息。

简历文本：
---
{resume_text}
---

要求：
1. 仔细阅读简历，提取以下维度的结构化信息
2. 对于简历中未提及的信息，使用空字符串 "" 或空数组 []
3. 只返回 JSON 对象，不要添加任何解释、注释或 Markdown 标记

提取字段说明：
- name: 姓名
- phone: 电话
- email: 邮箱
- address: 地址
- years_of_experience: 总工作年限（如 "5年"）
- highest_degree: 最高学历（如 "硕士", "本科", "博士"）
- school: 毕业院校
- major: 专业
- skills: 技能列表，每项包含 name（技能名）和 level（"精通"/"熟练"/"了解"）
- work_experience: 工作经历列表，每项包含 company（公司）、role（职位）、duration（时间）、highlights（亮点/成果列表）
- projects: 项目经历列表，每项包含 name（项目名）、role（角色）、description（简述）、tech_stack（技术栈列表）
- certificates: 证书/资质列表
- languages: 语言能力列表

返回格式：
{{
  "name": "",
  "phone": "",
  "email": "",
  "address": "",
  "years_of_experience": "",
  "highest_degree": "",
  "school": "",
  "major": "",
  "skills": [{{"name": "Python", "level": "精通"}}],
  "work_experience": [{{"company": "", "role": "", "duration": "", "highlights": [""]}}],
  "projects": [{{"name": "", "role": "", "description": "", "tech_stack": [""]}}],
  "certificates": [],
  "languages": []
}}"""


# ═══════════════════════════════════════════════════
#  P1 — Semantic scoring (System Prompt.md rubric)
# ═══════════════════════════════════════════════════

SYSTEM_SCORING_PROMPT = """# Role (角色设定)
你是一位极其严谨、客观的资深技术总监兼高级HR专家。你的任务是对候选人的非结构化简历文本与特定的岗位需求(JD)进行深度的交叉对比，并给出一份精准、一致且经得起推敲的量化匹配度报告。

# Task (任务目标)
请仔细阅读提供的 [JD 文本] 和 [候选人简历文本]，严格依据下方的【评分基准（Rubric）】进行多维度打分，并输出纯 JSON 格式的评估结果。

# Core Principles (绝对约束 - 保证每次评分一致性的铁律)
1. 【零脑补原则】：只评估简历中显式呈现的事实。候选人没有写明的技能或经验，默认其得分为 0。绝对禁止基于常规行业认知去推断"他做过这个项目，应该也会那个技术"。
2. 【证据驱动】：你给出的每一个评分维度，其对应的 `reason`（理由）必须引用简历中的具体数据、技术栈或项目描述作为论据支撑。没有证据，不能给高分。
3. 【扣分制思维】：基础分为 100 分。如果 JD 明确要求的内容在简历中缺失或不足，必须严格扣分。

# Scoring Rubric (评分基准 - 决策逻辑的标尺)
请将综合评估分为以下 3 个维度，并严格按照对应的分数段锚点（Anchor）进行打分：

## 维度一：核心技能匹配度 (Skill Match) - 权重 50%
* 评估逻辑：对比 JD 中的硬性技能要求与简历中的技能清单。
* 分数锚点：
  - [90-100分]：完全命中 JD 要求的核心技能，且有主导的复杂项目经验作为深度掌握的佐证。
  - [75-89分]：命中了 80% 核心技能，或者命中 100% 但部分技能仅停留在"熟悉"阶段，缺乏深度落地证明。
  - [60-74分]：命中了 50%-79% 的核心技能，能够胜任基础工作，但需要培养。
  - [0-59分]：缺失 JD 中最致命/最底层的核心技能要求。

## 维度二：项目与经验相关性 (Experience Relevance) - 权重 35%
* 评估逻辑：判断候选人过去解决的问题域、业务场景复杂度和工作年限是否契合 JD。
* 分数锚点：
  - [85-100分]：做过与当前岗位几乎一模一样的业务，且在其中承担核心开发/架构角色，解决了关键高并发/复杂业务痛点。
  - [70-84分]：行业不同但技术架构相似，或行业相同但项目复杂度略低。
  - [50-69分]：过往项目全是简单的外包或单体CRUD，与要求的复杂架构经验不符。

## 维度三：背景与加分项 (Bonus & Background) - 权重 15%
* 评估逻辑：学历背景、沟通能力描述、开源贡献、博客等。
* 分数锚点：
  - [80-100分]：有明确的加分项（如名企背景、优质开源项目主导者、985/211学历且JD有要求）。
  - [60-79分]：背景平庸，无明显加分项，但符合底线要求。

# Output Format (输出格式)
你必须以纯 JSON 对象的格式输出，不要包含任何 Markdown 标记（如 ```json），不要有任何前言或后语。JSON 结构必须完全遵循以下契约：

{{
  "overall_score": <基于上述权重计算出的整数总分 0-100>,
  "summary": "<用一句话总结该候选人是否值得面试，以及最突出的亮点或致命伤>",
  "dimensions": [
    {{
      "name": "技能匹配度",
      "score": <整数 0-100>,
      "reason": "<结合简历原文说明给此分的具体依据>"
    }},
    {{
      "name": "项目经验相关性",
      "score": <整数 0-100>,
      "reason": "<结合简历原文说明给此分的具体依据>"
    }},
    {{
      "name": "背景与加分项",
      "score": <整数 0-100>,
      "reason": "<结合简历原文说明给此分的具体依据>"
    }}
  ],
  "missing_skills": ["<缺失的技能词1>", "<缺失的技能词2>"]
}}

---

JD 文本：
---
{jd_text}
---

候选人简历文本：
---
{resume_text}
---"""


# ── Client ──

def _get_client() -> AsyncOpenAI:
    """Create OpenAI-compatible client based on LLM_PROVIDER config."""
    provider = settings.llm_provider
    api_key = settings.effective_api_key
    base_url = settings.effective_base_url

    logger.info("LLM client: provider=%s, base_url=%s", provider, base_url)
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def _get_model() -> str:
    """Resolve the model name from config or provider default."""
    if settings.llm_model:
        return settings.llm_model
    provider = settings.llm_provider
    cfg = PROVIDER_CONFIG.get(provider, {})
    return cfg.get("default_model", "gpt-4o")


def _is_api_key_configured() -> bool:
    key = settings.effective_api_key
    return bool(key and not key.startswith("sk-your-"))


# ── JSON Cleaning ──

def _clean_json_response(raw: str) -> str:
    """Strip Markdown code fences, think tags, and extra whitespace from LLM response."""
    # Remove thinking/scratchpad tags (DeepSeek-R1, Qwen thinking mode)
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
    raw = re.sub(r'<thinking>.*?</thinking>', '', raw, flags=re.DOTALL)

    # Strip ```json ... ``` or ``` ... ``` wrappers
    raw = raw.strip()
    if raw.startswith('```'):
        first_newline = raw.find('\n')
        if first_newline != -1:
            raw = raw[first_newline + 1:]
        if raw.endswith('```'):
            raw = raw[:-3]
    return raw.strip()


def _parse_with_retry(raw: str) -> dict:
    """Attempt to parse JSON from LLM output, aggressive cleaning on retry."""
    for attempt in range(1 + MAX_RETRIES):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            if attempt < MAX_RETRIES:
                start = raw.find('{')
                end = raw.rfind('}')
                if start != -1 and end != -1 and end > start:
                    raw = raw[start:end + 1]
                else:
                    raw = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', raw)
            else:
                raise


async def _call_llm(prompt: str, use_json_format: bool = True, max_tokens: int = 2000) -> str:
    """Call LLM with unified error handling.

    Args:
        prompt: The prompt to send.
        use_json_format: Whether to request json_object response format.
        max_tokens: Maximum tokens in response.
    """
    if not _is_api_key_configured():
        raise LLMCallError(
            f"LLM API key not configured. Set LLM_API_KEY in backend/.env for provider '{settings.llm_provider}'"
        )

    client = _get_client()
    model = _get_model()

    kwargs: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }

    if use_json_format:
        kwargs["response_format"] = {"type": "json_object"}

    logger.info("Calling LLM: model=%s, provider=%s, json_format=%s",
                model, settings.llm_provider, use_json_format)

    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception as e:
        err_msg = str(e)
        if use_json_format and ("response_format" in err_msg or "not support" in err_msg.lower()
                                or "not supported" in err_msg.lower()):
            logger.warning("response_format not supported, retrying without it")
            kwargs.pop("response_format", None)
            try:
                response = await client.chat.completions.create(**kwargs)
            except Exception as retry_e:
                logger.error("LLM retry also failed: %s", retry_e)
                raise LLMCallError(f"LLM API call failed: {retry_e}") from retry_e
        else:
            logger.error("LLM API call failed: %s", e)
            raise LLMCallError(f"LLM API call failed: {e}") from e

    return response.choices[0].message.content or ""


# ── Public API ──

async def extract_resume_info(resume_text: str) -> dict:
    """P0: LLM extraction of basic candidate info (name, phone, email, address)."""
    prompt = EXTRACTION_PROMPT.format(resume_text=resume_text)
    raw_output = await _call_llm(prompt, use_json_format=True)
    logger.info("LLM extraction raw output: %d chars", len(raw_output))

    cleaned = _clean_json_response(raw_output)
    try:
        result = _parse_with_retry(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse extraction JSON: %s", e)
        raise LLMCallError(f"Failed to parse LLM extraction JSON: {e}") from e

    for field in ("name", "phone", "email", "address"):
        if field not in result:
            result[field] = ""

    logger.info("Extraction OK: name=%s", mask_name(result.get("name", "")))
    return result


async def extract_resume_deep(resume_text: str) -> dict:
    """P1: LLM deep extraction — education, work history, projects, skills.

    Returns a rich dict with structured candidate profile.
    """
    prompt = DEEP_EXTRACTION_PROMPT.format(resume_text=resume_text)
    raw_output = await _call_llm(prompt, use_json_format=True, max_tokens=3000)
    logger.info("LLM deep extraction raw output: %d chars", len(raw_output))

    cleaned = _clean_json_response(raw_output)
    try:
        result = _parse_with_retry(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse deep extraction JSON: %s", e)
        raise LLMCallError(f"Failed to parse deep extraction JSON: {e}") from e

    # Ensure expected fields
    for field in ("name", "phone", "email", "address",
                  "years_of_experience", "highest_degree", "school", "major"):
        result.setdefault(field, "")
    for list_field in ("skills", "work_experience", "projects", "certificates", "languages"):
        result.setdefault(list_field, [])

    logger.info("Deep extraction OK: skills=%d, work_exp=%d, projects=%d",
                len(result.get("skills", [])),
                len(result.get("work_experience", [])),
                len(result.get("projects", [])))
    return result


async def score_resume_vs_jd(resume_text: str, jd_text: str) -> dict:
    """P1: Semantic JD-CV scoring using the System Prompt.md rubric.

    Returns:
        dict with keys: overall_score, summary, dimensions, missing_skills
    """
    if not jd_text.strip():
        return {
            "overall_score": 0, "summary": "未提供JD文本",
            "dimensions": [], "missing_skills": [],
        }

    prompt = SYSTEM_SCORING_PROMPT.format(resume_text=resume_text, jd_text=jd_text)
    raw_output = await _call_llm(prompt, use_json_format=True, max_tokens=2000)
    logger.info("LLM rubric scoring raw output: %d chars", len(raw_output))

    cleaned = _clean_json_response(raw_output)
    try:
        result = _parse_with_retry(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse rubric scoring JSON: %s", e)
        raise LLMCallError(f"Failed to parse rubric scoring JSON: {e}") from e

    # Normalize
    result.setdefault("overall_score", 0)
    result.setdefault("summary", "")
    result.setdefault("dimensions", [])
    result.setdefault("missing_skills", [])

    result["overall_score"] = max(0, min(100, int(result["overall_score"])))
    for dim in result["dimensions"]:
        dim["score"] = max(0, min(100, int(dim.get("score", 0))))

    logger.info("Rubric scoring OK: overall=%d, summary=%s",
                result["overall_score"], result.get("summary", "")[:60])
    return result


# ── Deprecated / compatible aliases ──

async def match_resume_to_jd(resume_text: str, jd_text: str) -> dict:
    """P1: Alias for score_resume_vs_jd (backward compat)."""
    result = await score_resume_vs_jd(resume_text, jd_text)
    # Convert missing_skills to risks format
    result["risks"] = [
        f"缺失技能：{s}" for s in result.get("missing_skills", [])
    ]
    return result
