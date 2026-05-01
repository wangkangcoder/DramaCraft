from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI编剧协同创作系统"
    API_V1_STR: str = "/api"

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    OPENAI_API_KEY: Optional[str] = None
    ZHIPUAI_API_KEY: Optional[str] = "29a636d5b47c4ba78cbe1612e60d33cd.7DCz91mVvjYCCCYI"
    DEEPSEEK_API_KEY: Optional[str] = "sk-e6b306eac3f64011b7c59e09e5373f5c"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
