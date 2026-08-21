from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量 / .env 读取。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "GEAP"
    API_PREFIX: str = "/api"

    # 数据库：默认 SQLite（零依赖快速启动），Docker 下覆盖为 PostgreSQL
    DATABASE_URL: str = "sqlite:///./geap.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "geap-dev-secret"

    STORAGE_DIR: str = "./storage"
    UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    CORS_ORIGINS: str = "*"

    # DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    BACKUP_DIR: str = "./backups"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
