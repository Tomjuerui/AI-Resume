from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o"

    # Redis
    redis_dsn: str = "redis://localhost:6379/0"
    redis_password: str = ""

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
