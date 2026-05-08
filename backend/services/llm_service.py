import json
import re
import logging

from openai import AsyncOpenAI
from core.config import settings, PROVIDER_CONFIG
from core.exceptions import LLMCallError

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

# ── Prompts ──

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

MATCHING_PROMPT = """你是一位资深的招聘专家和技术面试官。请根据以下岗位描述(JD)和候选人简历，进行多维度的匹配分析。

岗位描述(JD)：
---
{jd_text}
---

候选人简历：
---
{resume_text}
---

请从以下四个维度评分，每个维度 0-100 分，并给出简短理由：

1. 技能匹配度：候选人的技术栈与 JD 要求的技术栈的重叠程度
2. 经验相关性：候选人的项目经验、工作年限、职位级别是否匹配 JD 要求
3. 教育背景：学历、专业是否满足 JD 要求
4. 综合素养：沟通能力、团队协作、领导力等软素质

此外还需要给出：
- overall_score：综合评分（0-100），考虑各项权重（技能40%、经验30%、教育15%、综合15%）
- risks：潜在风险点列表（如缺失关键技能、经验不足、学历不符等）

只返回 JSON 对象，不要添加任何解释、注释或 Markdown 标记。

返回格式：
{{"overall_score": 85, "dimensions": [{{"name": "技能匹配度", "score": 90, "reason": "..."}}, ...], "risks": ["缺失技能：React", ...]}}"""


# ── Client ──

def _get_client() -> AsyncOpenAI:
    """Create OpenAI-compatible client based on LLM_PROVIDER config."""
    provider = settings.llm_provider
    cfg = PROVIDER_CONFIG.get(provider, {})

    base_url = settings.llm_base_url or cfg.get("base_url", "https://api.openai.com/v1")
    api_key = settings.effective_api_key

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


async def _call_llm(prompt: str, use_json_format: bool = True) -> str:
    """Call LLM with unified error handling and response_format gracefully.

    Args:
        prompt: The prompt to send.
        use_json_format: Whether to request json_object response format.
                         Some providers/models may not support this.

    Returns:
        Raw text response from the LLM.
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
        "max_tokens": 2000,
    }

    if use_json_format:
        kwargs["response_format"] = {"type": "json_object"}

    logger.info("Calling LLM: model=%s, provider=%s, json_format=%s",
                model, settings.llm_provider, use_json_format)

    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception as e:
        err_msg = str(e)
        # If response_format not supported, retry without it
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
    """Call LLM to extract candidate basic info (P0: name, phone, email, address)."""
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

    logger.info("Extraction OK: name=%s", result.get("name"))
    return result


async def match_resume_to_jd(resume_text: str, jd_text: str) -> dict:
    """LLM-based semantic matching (P1).

    Returns:
        dict with keys: overall_score, dimensions, risks
    """
    if not jd_text.strip():
        return {"overall_score": 0, "dimensions": [], "risks": ["未提供JD文本"]}

    prompt = MATCHING_PROMPT.format(resume_text=resume_text, jd_text=jd_text)
    raw_output = await _call_llm(prompt, use_json_format=True)
    logger.info("LLM matching raw output: %d chars", len(raw_output))

    cleaned = _clean_json_response(raw_output)
    try:
        result = _parse_with_retry(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse matching JSON: %s", e)
        raise LLMCallError(f"Failed to parse LLM matching JSON: {e}") from e

    # Ensure expected shape
    result.setdefault("overall_score", 0)
    result.setdefault("dimensions", [])
    result.setdefault("risks", [])

    # Clamp scores
    result["overall_score"] = max(0, min(100, int(result["overall_score"])))
    for dim in result["dimensions"]:
        dim["score"] = max(0, min(100, int(dim.get("score", 0))))

    logger.info("LLM matching OK: overall=%d, dimensions=%d, risks=%d",
                result["overall_score"], len(result["dimensions"]), len(result["risks"]))
    return result
