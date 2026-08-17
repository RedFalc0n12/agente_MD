from langchain.tools import tool
from langchain_core.messages import ToolMessage
import Drive_service as drive_service
from httpx import HTTPError

import os
import tempfile
import uuid

from src.script.extrair_doc import extrair_texto


# Pasta temporária de trabalho do agente (arquivos baixados e gerados).
# Em produção pode valer a pena isolar por conversa/usuário.
PASTA_TRABALHO = os.path.join(tempfile.gettempdir(), "agente_documentos")
os.makedirs(PASTA_TRABALHO, exist_ok=True)
@tool
def listar_arquivos_drive(query: str = "") -> list[dict]:
    """
    Lista arquivos e pastas do Google Drive com suporte a filtros avançados.

    IMPORTANT RULES:
        1. Se o usuario mencionou um nome de arquivo ou pasta, IGNORE o filtro name e use query="" primeiro.
        2- caso não saiba qual usar, use sempre "" (string vazia).

    Argumento:
        query: argumento de pesquisa para filtrar dentro do google drive

    Sintaxe permitida para o argumento query:
    None ou "" para listar todos os arquivos e pastas.
    Só pastas: "mimeType = 'application/vnd.google-apps.folder'"
    Só arquivos: "mimeType != 'application/vnd.google-apps.folder'"
    Só PDFs: "mimeType = 'application/pdf'"
    Só Docs: "mimeType = 'application/vnd.google-apps.document'"
    Só Planilhas: "mimeType = 'application/vnd.google-apps.spreadsheet'"
    Filtrar por nome do arquivo: "name contains 'nome do arquivo'" (substitua 'nome do arquivo' pelo nome real)
    """

    try:
        # Validação de segurança contra placeholders
        if query and any(p in query for p in ['<', '>', 'FOLDER_ID', 'ID_DO'""]):
            return [{"error": "Query inválida: contém placeholders. Substitua por valores reais ou rode sem filtro primeiro."}]
        
        arquivos = drive_service._listar_arquivos_sync(query=query or None)
        return [
            {"id": a["id"], "name": a["name"], "mimeType": a["mimeType"]}
            for a in arquivos
        ]
    except HTTPError as e:
        return [{"error": f"Falha na API do Drive: {e}. Verifique a sintaxe da query."}]

def baixar_arquivo_drive(file_id: str, destino_local: str) -> str:
    """
    Baixa um arquivo do Google Drive para o caminho local especificado.

    Argumentos:
        file_id: ID do arquivo no Google Drive.
        destino_local: Caminho local onde o arquivo será salvo.

    Retorna:
        Caminho completo do arquivo baixado.
    """
    try:
        caminho_baixado = drive_service._baixar_arquivo_sync(file_id, destino_local)
        return caminho_baixado
    except HTTPError as e:
        return f"Falha na API do Drive ao baixar o arquivo: {e}. Verifique se o ID está correto."

def exportar_arquivo_google_drive(file_id: str, destino_local: str, mime_type: str = "application/pdf") -> str:
    """
    Exporta um arquivo nativo do Google (Docs, Sheets, Slides) para um formato comum (pdf, docx, etc.)
    e salva no caminho local especificado.

    Argumentos:
        file_id: ID do arquivo no Google Drive.
        destino_local: Caminho local onde o arquivo exportado será salvo.
        mime_type: Tipo MIME para exportação (ex: "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document").

    Retorna:
        Caminho completo do arquivo exportado.
    """
    try:
        caminho_exportado = drive_service._exportar_arquivo_google_sync(file_id, destino_local, mime_type)
        return caminho_exportado
    except HTTPError as e:
        return f"Falha na API do Drive ao exportar o arquivo: {e}. Verifique se o ID está correto e se o tipo MIME é suportado."

@tool
def ler_conteudo_arquivo(caminho_local: str) -> dict:
    """
    Extrai o texto de um arquivo já baixado localmente (pdf, docx, txt
    ou md). Use o `caminho_local` retornado por baixar_arquivo_drive.
    Retorna o texto extraído, para você (o agente) usar como base ao
    escrever o novo conteúdo.
    """
    texto = extrair_texto(caminho_local)
    return {"texto": texto}


@tool
async def enviar_arquivo_drive(
    caminho_local: str, nome_no_drive: str = "", folder_id: str = ""
) -> dict:
    """
    Envia (upload) um arquivo local para o Google Drive — normalmente o
    arquivo que você acabou de gerar com gerar_documento.
    `nome_no_drive` é opcional (usa o nome do arquivo local se vazio).
    `folder_id` é opcional (usa a pasta padrão do .env se vazio).
    Retorna id, name e webViewLink do arquivo criado no Drive.
    """
    resultado = await drive_service.enviar_arquivo(
        caminho_local=caminho_local,
        nome_no_drive=nome_no_drive or None,
        folder_id=folder_id or None,
    )
    return resultado


""" r = listar_arquivos_drive(query="name contains 'teste'")
print(r)  # Exibe o resultado da listagem de arquivos  """


tools = [listar_arquivos_drive,baixar_arquivo_drive,exportar_arquivo_google_drive,ler_conteudo_arquivo,enviar_arquivo_drive]

