"""
whatsapp.py

Rota FastAPI que recebe o webhook da Evolution API, repassa o texto da
mensagem pro agente (que decide sozinho quais tools chamar) e devolve
a resposta de volta pro número do remetente no WhatsApp.
"""

import logging

from fastapi import APIRouter, Request

from src.agente.ai_server import executar_agente
from src.script.evolution_service import enviar_mensagem_texto

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/WhatsApp")
async def whatsapp_webhook(request: Request):
    """
    Payload esperado (formato padrão do evento `messages.upsert` da
    Evolution API):

        {
          "data": {
            "key": {
              "remoteJid": "5511999999999@s.whatsapp.net",
              "fromMe": false
            },
            "message": {"conversation": "texto da mensagem"}
          }
        }

    Se o formato da sua instância for diferente, ajuste a extração
    abaixo.
    """
    payload = await request.json()
    dados = payload.get("data", {})
    chave = dados.get("key", {})

    # Ignora mensagens que o próprio bot enviou (eco), senão ele
    # poderia acabar respondendo pra si mesmo em loop.
    if chave.get("fromMe"):
        return {"status": "ignorado", "motivo": "mensagem enviada pelo próprio bot"}

    remote_jid = chave.get("remoteJid", "")
    numero = remote_jid.split("@")[0] if remote_jid else ""

    # Ignora mensagens de grupo (remoteJid termina em @g.us) -- remova
    # este bloco se o agente também deve responder em grupos.
    if remote_jid.endswith("@g.us"):
        return {"status": "ignorado", "motivo": "mensagem de grupo"}

    texto_mensagem = dados.get("message", {}).get("conversation", "")

    if not texto_mensagem or not numero:
        return {"status": "ignorado", "motivo": "mensagem vazia ou formato inesperado"}

    # --- 1) roda o agente -------------------------------------------------
    try:
        resposta = await executar_agente(texto_mensagem)
    except Exception:
        logger.exception("Erro ao executar o agente para %s", numero)
        resposta = (
            "Desculpe, tive um problema para processar sua mensagem. "
            "Pode tentar novamente em instantes?"
        )

    # --- 2) envia a resposta de volta pro WhatsApp -------------------------
    try:
        await enviar_mensagem_texto(numero, resposta)
    except Exception:
        logger.exception("Erro ao enviar resposta via Evolution API para %s", numero)
        return {
            "status": "erro",
            "motivo": "agente respondeu, mas falhou ao enviar pro WhatsApp",
            "resposta": resposta,
        }

    return {"status": "processado", "resposta": resposta}