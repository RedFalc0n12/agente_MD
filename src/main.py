import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Importação dos roteadores das pastas dedicadas
from src.routers import whatsapp,documentos

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="API do Agente Jurídico para processamento de documentos e automação WhatsApp"
)

# Configuração de CORS (libera acesso para testes locais ou dashboards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro das Rotas Modularizadas
app.include_router(whatsapp.router, prefix="/webhook", tags=["WhatsApp Webhook"])
app.include_router(documentos.router, prefix="/api/v1/documentos", tags=["Documentos"])


@app.get("/", tags=["Health Check"])
async def root():
    """Endpoint básico para verificar se a API está online."""
    return {
        "status": "online",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health", tags=["Health Check"])
async def health_check():
    """Checagem de saúde do sistema."""
    return {"status": "healthy"}