from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── LLM Provider ──
    # openai | deepseek | qianwen
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = ""               # auto-filled from provider defaults if empty
    llm_base_url: str = ""            # override auto-detected base URL

    # ── Redis ──
    redis_dsn: str = "redis://localhost:6379/0"
    redis_password: str = ""

    # ── OSS (Alibaba Cloud Object Storage) ──
    oss_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""

    # ── App ──
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"
    max_upload_size_mb: int = 10

    # ── Backward compat (legacy keys, fallback to llm_api_key) ──
    openai_api_key: str = ""
    openai_base_url: str = ""

    @property
    def effective_api_key(self) -> str:
        return self.llm_api_key or self.openai_api_key

    @property
    def oss_configured(self) -> bool:
        return bool(self.oss_endpoint and self.oss_bucket
                    and self.oss_access_key_id and self.oss_access_key_secret)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# ── Provider presets ──

PROVIDER_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    "qianwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
    },
}

settings = Settings()
