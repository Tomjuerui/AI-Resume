import json
import re
import logging

from openai import AsyncOpenAI
from core.config import settings
from core.exceptions import LLMCallError

logger = logging.getLogger(__name__)

MAX_RETRIES = 2

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


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


def _clean_json_response(raw: str) -> str:
    """Strip Markdown code fences and extra whitespace from LLM response."""

    # Remove thinking/scratchpad tags (DeepSeek-R1 style)
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)

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
    """Attempt to parse JSON from LLM output, with aggressive cleaning on retry."""
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


async def extract_resume_info(resume_text: str) -> dict:
    """Call LLM to extract candidate info (name, phone, email, address).

    Returns a dict with keys: name, phone, email, address.
    """
    if not settings.openai_api_key or settings.openai_api_key.startswith("sk-your-"):
        raise LLMCallError(
            "OpenAI API key not configured. Set OPENAI_API_KEY in backend/.env"
        )

    client = _get_client()
    prompt = EXTRACTION_PROMPT.format(resume_text=resume_text)

    logger.info("Sending LLM extraction request, model=%s", settings.llm_model)

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1000,
        )
    except Exception as e:
        logger.error("LLM API call failed: %s", e)
        raise LLMCallError(f"LLM API call failed: {e}") from e

    raw_output = response.choices[0].message.content or ""
    logger.info("LLM raw output length: %d", len(raw_output))

    cleaned = _clean_json_response(raw_output)

    try:
        result = _parse_with_retry(cleaned)
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Failed to parse LLM JSON after %d retries: %s", MAX_RETRIES, e)
        raise LLMCallError(f"Failed to parse LLM response JSON: {e}") from e

    # Ensure all expected fields exist
    for field in ("name", "phone", "email", "address"):
        if field not in result:
            result[field] = ""

    logger.info("Extraction complete: name=%s, phone=%s, email=%s",
                result.get("name"), result.get("phone"), result.get("email"))

    return result
