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
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    class Config:
        env_file = ".env"


settings = Settings()