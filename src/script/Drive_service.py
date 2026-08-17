"""
drive_service.py

Camada de integração com o Google Drive via Service Account.
Responsável por: autenticar, listar arquivos, baixar arquivos e enviar
(upload) arquivos de volta para o Drive.

Todas as chamadas da biblioteca google-api-python-client são SÍNCRONAS,
então elas são executadas em um threadpool (run_in_executor) para não
bloquear o event loop do FastAPI.
"""

import io
import os
import asyncio
from functools import lru_cache

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")

# Se o agente só precisa ler + escrever nos arquivos que foram compartilhados
# com ele, "drive.file" é mais restrito que "drive" (acesso total).
SCOPES = ["https://www.googleapis.com/auth/drive"]

# ID da pasta do Drive onde os arquivos processados devem ser enviados.
# Pode vir de variável de ambiente ou ser passado explicitamente na chamada.
DEFAULT_UPLOAD_FOLDER_ID = os.getenv("GOOGLE_DRIVE_UPLOAD_FOLDER_ID","11YIFfzWiArV041eG7-XTuMKva1UpGEVR")


@lru_cache(maxsize=1)
def _get_service():
    """
    Cria (uma única vez, graças ao lru_cache) o client autenticado do
    Google Drive usando a Service Account.
    """
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# Funções síncronas (rodam no threadpool)
# ---------------------------------------------------------------------------

def _listar_arquivos_sync(query: str | None = None, page_size: int = 50) -> list[dict]:
    """
    Lista arquivos disponíveis no Drive (que foram compartilhados com a
    service account). `query` segue a sintaxe de busca da Drive API, ex:
        "name contains 'relatorio'"
        "'ID_DA_PASTA' in parents"
        None ou "" para listar todos os arquivos e pastas.
    """
    service = _get_service()
    resultados = []
    page_token = None

    while True:
        response = service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
            pageSize=page_size,
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        resultados.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return resultados

#ler conteudo do arquivo

def _baixar_arquivo_sync(file_id: str, destino_local: str) -> str:
    """
    Baixa um arquivo comum (upload binário: pdf, docx, imagem, etc.)
    pelo seu ID e salva em destino_local. Retorna o caminho salvo.
    """
    service = _get_service()
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    with open(destino_local, "wb") as f:
        f.write(fh.getvalue())

    return destino_local


def _exportar_arquivo_google_sync(
    file_id: str, destino_local: str, mime_type: str = "application/pdf"
) -> str:
    """
    Exporta um arquivo nativo do Google (Docs, Sheets, Slides) para um
    formato comum (pdf, docx, etc.), já que esses arquivos não podem ser
    baixados com get_media diretamente.
    """
    service = _get_service()
    request = service.files().export_media(fileId=file_id, mimeType=mime_type)

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    with open(destino_local, "wb") as f:
        f.write(fh.getvalue())

    return destino_local


def _enviar_arquivo_sync(
    caminho_local: str,
    nome_no_drive: str | None = None,
    folder_id: str | None = None,
    mime_type: str | None = None,
) -> dict:
    """
    Envia (upload) um arquivo local para o Google Drive.
    Retorna metadados do arquivo criado (id, name, webViewLink).
    """
    service = _get_service()

    nome_final = nome_no_drive or os.path.basename(caminho_local)
    pasta_destino = folder_id or DEFAULT_UPLOAD_FOLDER_ID

    file_metadata = {"name": nome_final}
    if pasta_destino:
        file_metadata["parents"] = [pasta_destino]

    media = MediaFileUpload(caminho_local, mimetype=mime_type, resumable=True)

    arquivo_criado = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink",
        supportsAllDrives=True,
    ).execute()

    return arquivo_criado


# ---------------------------------------------------------------------------
# Wrappers assíncronos — são estes que a rota do FastAPI deve chamar
# ---------------------------------------------------------------------------

async def listar_arquivos(query: str | None = None) -> list[dict]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _listar_arquivos_sync, query)


async def baixar_arquivo(file_id: str, destino_local: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _baixar_arquivo_sync, file_id, destino_local)


async def exportar_arquivo_google(
    file_id: str, destino_local: str, mime_type: str = "application/pdf"
) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _exportar_arquivo_google_sync, file_id, destino_local, mime_type
    )


async def enviar_arquivo(
    caminho_local: str,
    nome_no_drive: str | None = None,
    folder_id: str | None = None,
    mime_type: str | None = None,
) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _enviar_arquivo_sync, caminho_local, nome_no_drive, folder_id, mime_type
    )


""" r = _listar_arquivos_sync(query= "mimeType != 'application/vnd.google-apps.folder'")
print(r)  """
""" r = _listar_arquivos_sync("name contains 'Currículo'")  # Exemplo de filtro para listar arquivos cujo nome contém "Currículo" """
""" r = _baixar_arquivo_sync("1X9g0k5J3l8v9Q2R3T4U5V6W7X8Y9Z0A","./curriculum.pdf")  # Exemplo de download de arquivo pelo ID
print(r)  # Exibe o resultado da listagem de arquivos   """