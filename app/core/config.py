from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "App Analytics"
    VERSION: str = "0.1.0"
    
    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "app_analytics"
    
    # OpenAI
    OPENAI_API_KEY: str = ""

    # LangSmith for observability
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "app-analytics-agent"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # Chat config
    MAX_CHAT_HISTORY_CNT: int = 5
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_SSL: bool = False
    
    # Cache settings
    CACHE_BACKEND: str = "redis"  # "redis", "memcache", "memory"
    CACHE_TTL: int = 3600  # 1 hour default TTL
    CHAT_HISTORY_TTL: int = 86400  # 24 hours for chat history
    CACHE_HEALTH_CHECK_TIMEOUT: int = 5  # Health check timeout in seconds
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def REDIS_URL(self) -> str:
        protocol = "rediss" if self.REDIS_SSL else "redis"
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"{protocol}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    class Config:
        env_file = ".env"


settings = Settings()