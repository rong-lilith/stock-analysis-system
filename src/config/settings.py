"""
配置管理模块

使用 pydantic-settings 从环境变量加载配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # 数据库
    database_url: str = "postgresql://admin:changeme@localhost:5432/market_data"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # 币安
    binance_api_key: str = ""
    binance_api_secret: str = ""

    # OKX
    okx_api_key: str = ""
    okx_api_secret: str = ""
    okx_passphrase: str = ""

    # 应用
    log_level: str = "INFO"
    debug: bool = False


# 全局配置实例
settings = Settings()
