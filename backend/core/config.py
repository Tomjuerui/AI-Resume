from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"

    # Redis
    redis_dsn: str = "redis://localhost:6379/0"
    redis_password: str = ""

    # OSS (Alibaba Cloud Object Storage)
    oss_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"
    max_upload_size_mb: int = 10

    @property
    def oss_configured(self) -> bool:
        return bool(self.oss_endpoint and self.oss_bucket
                    and self.oss_access_key_id and self.oss_access_key_secret)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
