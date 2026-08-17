"""
documentos.py

Rota FastAPI que expõe o fluxo:

  1. GET  /Documentos            -> lista os arquivos disponíveis no Drive
  2. POST /Documentos/processar  -> baixa os arquivos pedidos, chama o
                                     processamento interno (fora deste
                                     fluxo) e envia o(s) arquivo(s)
                                     resultante(s) de volta pro Drive

O tratamento/processamento do conteúdo do arquivo (parsing, IA, etc.) NÃO
entra aqui — fica isolado em `processar_arquivos()`, que você deve
substituir pela sua lógica real. Esta rota só orquestra: buscar ->
entregar pro processamento -> pegar o resultado -> subir pro Drive.
"""

import os
import tempfile
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import src.script.Drive_service

router = APIRouter()
drive_service = src.script.Drive_service

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ArquivoDisponivel(BaseModel):
    id: str
    name: str
    mimeType: str
    modifiedTime: str | None = None
    size: str | None = None


class SolicitacaoProcessamento(BaseModel):
    # o agente/usuário informa quais arquivos do Drive quer processar
    file_ids: list[str]
    # opcional: pasta de destino no Drive para o(s) arquivo(s) resultante(s)
    folder_id: str | None = None


class ArquivoEnviado(BaseModel):
    id: str
    name: str
    webViewLink: str | None = None


class RespostaProcessamento(BaseModel):
    arquivos_enviados: list[ArquivoEnviado]


# ---------------------------------------------------------------------------
# 1) Listar arquivos disponíveis no Drive
# ---------------------------------------------------------------------------

@router.get("/Documentos", tags=["Documentos"], response_model=list[ArquivoDisponivel])
async def listar_documentos_processados(query: str | None = None):
    """
    Lista os arquivos disponíveis no Google Drive (que foram compartilhados
    com a service account do agente).

    `query` (opcional) aceita a sintaxe de busca da Drive API, por exemplo:
      - name contains 'relatorio'
      - '<ID_DA_PASTA>' in parents
    """
    try:
        arquivos = await drive_service.listar_arquivos(query=query)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao listar arquivos no Drive: {e}")

    return arquivos


# ---------------------------------------------------------------------------
# 2) Baixar os arquivos solicitados, processar e devolver pro Drive
# ---------------------------------------------------------------------------

def processar_arquivos(caminhos_locais: list[str]) -> list[str]:
    """
    >>> SUBSTITUA esta função pela sua lógica real de tratamento <<<

    Recebe os caminhos locais dos arquivos baixados do Drive e deve
    retornar uma lista de caminhos locais dos arquivos resultantes
    (podem ser os mesmos arquivos alterados, ou arquivos novos gerados).

    Este é o único ponto que este módulo delega para fora do fluxo do
    FastAPI — aqui você pluga seu agente/pipeline de tratamento.
    """
    # Placeholder: apenas devolve os mesmos arquivos recebidos.
    return caminhos_locais


@router.post("/Documentos/processar", tags=["Documentos"], response_model=RespostaProcessamento)
async def processar_documentos(solicitacao: SolicitacaoProcessamento):
    """
    Fluxo completo:
      1. Baixa cada arquivo pedido (por file_id) do Drive para uma pasta
         temporária local.
      2. Chama `processar_arquivos()` com os caminhos locais (a lógica de
         tratamento em si vive fora deste arquivo).
      3. Envia o(s) arquivo(s) resultante(s) de volta para o Drive.
    """
    if not solicitacao.file_ids:
        raise HTTPException(status_code=400, detail="Nenhum file_id informado.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        caminhos_baixados = []

        # --- 2.1) baixar cada arquivo pedido -------------------------------
        for file_id in solicitacao.file_ids:
            destino = os.path.join(tmp_dir, f"{uuid.uuid4().hex}_{file_id}")
            try:
                caminho = await drive_service.baixar_arquivo(file_id, destino)
            except Exception as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"Erro ao baixar arquivo {file_id} do Drive: {e}",
                )
            caminhos_baixados.append(caminho)

        # --- 2.2) processamento interno (fora deste fluxo) -----------------
        try:
            caminhos_resultantes = processar_arquivos(caminhos_baixados)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro no processamento: {e}")

        if not caminhos_resultantes:
            raise HTTPException(
                status_code=500, detail="Processamento não retornou nenhum arquivo."
            )

        # --- 2.3) enviar resultado(s) de volta pro Drive --------------------
        arquivos_enviados = []
        for caminho in caminhos_resultantes:
            try:
                resultado = await drive_service.enviar_arquivo(
                    caminho_local=caminho,
                    folder_id=solicitacao.folder_id,
                )
            except Exception as e:
                raise HTTPException(
                    status_code=502, detail=f"Erro ao enviar arquivo para o Drive: {e}"
                )
            arquivos_enviados.append(resultado)

    return RespostaProcessamento(arquivos_enviados=arquivos_enviados)