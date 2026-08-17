import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Agente Jurídico API"
    ENVIRONMENT: str = "development"
    
    # Chaves e URLs (lerão do arquivo .env)
    GOOGLE_API_KEY: str = ""
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_INSTANCE_NAME: str = "agente_escritorio"
    EVOLUTION_API_KEY: str = ""
    GOTENBERG_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()