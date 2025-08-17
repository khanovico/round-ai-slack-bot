import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "App Analytics"
    VERSION: str = "0.1.0"
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432")) if os.getenv("DB_PORT") else 5432
    DB_USER: str = os.getenv("DB_USER")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD")
    DB_NAME: str = os.getenv("DB_NAME")
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

    # LangSmith for observability
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT")
    LANGCHAIN_ENDPOINT: str = os.getenv("LANGCHAIN_ENDPOINT")

    # Google Drive API
    GOOGLE_DRIVE_CREDENTIALS_FILE: str = os.getenv("GOOGLE_DRIVE_CREDENTIALS_FILE")
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID")  # Optional: specific folder to upload to

    # Chat config
    MAX_CHAT_HISTORY_CNT: int = 5
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379")) if os.getenv("REDIS_PORT") else 6379
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD")
    REDIS_DB: str = os.getenv("REDIS_DB", "0") if os.getenv("REDIS_DB") else 0
    REDIS_SSL: bool = False
    REDIS_USER: str = os.getenv("REDIS_USER")

    # Cache settings
    CACHE_BACKEND: str = os.getenv("CACHE_BACKEND", "redis")  # "redis", "memcache", "memory"
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default TTL
    CHAT_HISTORY_TTL: int = int(os.getenv("CHAT_HISTORY_TTL", "86400"))  # 24 hours for chat history
    CACHE_HEALTH_CHECK_TIMEOUT: int = int(os.getenv("CACHE_HEALTH_CHECK_TIMEOUT", "5"))  # Health check timeout in seconds
    
    # Slack Configuration
    SLACK_CLIENT_ID: str = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET: str = os.getenv("SLACK_CLIENT_SECRET")
    SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN")
    SLACK_REDIRECT_URI: str = os.getenv("SLACK_REDIRECT_URI")
    DEFAULT_SLACK_CHANNEL: str = os.getenv("DEFAULT_SLACK_CHANNEL")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def REDIS_URL(self) -> str:
        protocol = "rediss" if self.REDIS_SSL else "redis"
        password = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        user = f"{self.REDIS_USER}" if self.REDIS_USER else ""
        return f"{protocol}://{user}{password}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"


settings = Settings()