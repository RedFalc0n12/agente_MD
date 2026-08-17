"""
text_extractor.py

Extrai texto puro de arquivos baixados do Drive (pdf, docx, txt), pra
poder passar esse conteúdo como contexto pro LLM.
"""

import os
import pdfplumber
from docx import Document


def extrair_texto(caminho_arquivo: str) -> str:
    """
    Detecta o tipo do arquivo pela extensão e extrai o texto.
    Lança ValueError se a extensão não for suportada.
    """
    extensao = os.path.splitext(caminho_arquivo)[1].lower()

    if extensao == ".pdf":
        return _extrair_texto_pdf(caminho_arquivo)
    elif extensao == ".docx":
        return _extrair_texto_docx(caminho_arquivo)
    elif extensao in (".txt", ".md"):
        with open(caminho_arquivo, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        raise ValueError(
            f"Extensão '{extensao}' não suportada para extração de texto. "
            "Suportadas: .pdf, .docx, .txt, .md"
        )


def _extrair_texto_pdf(caminho: str) -> str:
    partes = []
    with pdfplumber.open(caminho) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                partes.append(texto)
    return "\n\n".join(partes)


def _extrair_texto_docx(caminho: str) -> str:
    doc = Document(caminho)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())