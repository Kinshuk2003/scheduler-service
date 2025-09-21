"""
Application settings using Pydantic BaseSettings.

This module follows the Single Responsibility Principle by handling only configuration.
It uses the Factory pattern for creating settings instances and Dependency Injection
for providing configuration to other components.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    This class follows the Configuration Object pattern and provides
    a centralized place for all application configuration.
    """
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://scheduler:scheduler@localhost:5432/scheduler_db"
    database_url_sync: str = "postgresql://scheduler:scheduler@localhost:5432/scheduler_db"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "your-secret-api-key-here"
    
    # Security
    secret_key: str = "your-secret-key-here"
    
    # Logging
    log_level: str = "INFO"
    
    # Environment
    environment: str = "development"
    
    # CORS Configuration
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]
    
    # Job Configuration
    max_job_retries: int = 3
    default_retry_delay: int = 60
    job_timeout: int = 1800  # 30 minutes
    
    # Cleanup Configuration
    cleanup_old_runs_days: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton instance of settings
# This follows the Singleton pattern for configuration
settings = Settings()
