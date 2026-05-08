from openai import AsyncOpenAI
from core.config import settings


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )


async def extract_resume_info(resume_text: str, jd_text: str) -> dict:
    """Call LLM to extract structured resume info and match against JD."""
    client = get_client()
    # TODO: implement actual prompt and parsing
    return {}
