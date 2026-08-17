from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder,PromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.tools import tool
from langchain.agents import create_agent
from tools import tools
import asyncio


""" 5 RAG - Recuperação de informações a partir de documentos """


""" 6 Tools - Criação de ferramentas para o agente interagir com o mundo externo"""


def tempo (city: str) -> str:
    """fala as condições do tempo atual na cidede x"""
    return f"O tempo em {city} é ensolarado e quente."





tools = tools

""" 1 Modelagem -criamos o modelo de linguagem e algumas configurações basicas para o modelo de linguagem """
modelo = ChatOpenAI(
    model="llama-3.2-3b-instruct",
    base_url="http://127.0.0.1:1234/v1",
    api_key="sk-lm-O2Vq123l:daSmS4LpiknlCuYDacI6",
    temperature=0,
    max_tokens=4000,
   
)

agent = create_agent(model=modelo, tools=tools)

""" 2. Prompt - Criamos o prompt que será usado para interagir com o modelo de linguagem. O prompt é uma string que contém instruções para o modelo de linguagem, como por exemplo, "Responda à pergunta abaixo com base no documento fornecido pela ferramenta acessar_documento." """


Prompt = ChatPromptTemplate.from_messages([
    ("system", """Você é Eli, um agente que interage com o Google Drive.

### Suas responsabilidades:
trabalhar com listagem de arquivos, baixar arquivos e enviar arquivos de volta para o Drive e diretamente pro usuario via whatsapp. Use as ferramentas disponíveis para realizar essas ações. fluxo de trabalho sugerido: Você é um agente especialista em automação e gerenciamento de arquivos no Google Drive e envio via WhatsApp. Seu objetivo é ajudar o usuário a listar, baixar e enviar arquivos.

### REGRAS CRÍTICAS DE FLUXO DE TRABALHO:
1. ANÁLISE INICIAL: Quando o usuário pedir para buscar, listar ou fazer algo com um arquivo/pasta (mesmo que ele forneça um nome), você NUNCA deve tentar adivinhar ou inventar filtros na primeira tentativa.
2. PASSO OBRIGATÓRIO: Sempre execute primeiro a ferramenta `listar_arquivos_drive` com o argumento de query totalmente vazio: `query=""`.
3. SELEÇÃO DE ARQUIVO: Analise o retorno da lista vazia, localize o arquivo correto pelo nome exato ou pelo ID retornado e, só então, prossiga com a ação solicitada (baixar ou enviar).
4. REQUISIÇÕES ESPECÍFICAS: Se precisar criar um filtro avançado posteriormente, use a sintaxe exata da ferramenta (ex: "name contains 'termo'"). Nunca traduza campos para o português (use sempre 'name', nunca 'nome') e nunca adicione barras invertidas ou caracteres de escape.

### DIRETRIZES DE COMUNICAÇÃO:
- Seja direto, prestativo e informe ao usuário o que está fazendo em cada etapa.
- Se o arquivo solicitado não for encontrado na listagem geral, informe ao usuário e peça o nome exato.
 
Contexto: {contexto}"""),

    MessagesPlaceholder(variable_name="historico_da_conversa"),
    ("human", "{pergunta_atual}")
])



""" 3 - chain - Criamos a chain que será usada para interagir com o modelo de linguagem. A chain é uma sequência de passos que serão executados pelo modelo de linguagem, como por exemplo, "Receba a pergunta do usuário, acesse o documento e retorne a resposta."""
# metodo para extrair a resposta do agente, que é uma string, a partir da resposta do modelo de linguagem, que é um objeto complexo.
parse = StrOutputParser()

chain = Prompt| agent 

#texto = chain.invoke(mensagem)

""" 4 Memoria - Criamos a memória que será usada para armazenar o histórico de conversas do agente. A memória é um objeto que armazena informações sobre o estado do agente, como por exemplo, o histórico de conversas, o contexto atual, etc. """

# Criamos um "arquivo" (dicionário) para guardar o histórico de diferentes usuários
historicos_salvos = {}

# Função para pegar a "pasta" certa do arquivo baseado no ID da sessão
def pegar_historico(session_id: str):
    if session_id not in historicos_salvos:
        historicos_salvos[session_id] = ChatMessageHistory()
    return historicos_salvos[session_id]

# Colocamos a "mochila" na nossa chain básica
chain_com_memoria = RunnableWithMessageHistory(
    chain,
    pegar_historico, # A função que ensinamos acima
    input_messages_key="pergunta_atual",       # Qual variável é a pergunta nova?
    history_messages_key="historico_da_conversa" # Onde eu injeto as antigas?
)


while True:
    pergunta = input("\nDigite sua pergunta (ou 'sair' para encerrar): ")
    if pergunta.lower() == "sair":
        break

    resposta = chain_com_memoria.invoke(
        {"contexto": "", "pergunta_atual": pergunta},
        config={"configurable": {"session_id": "usuario_123"}} # Passando a etiqueta da pasta!
    )
    print(f"\nResposta do agente: {resposta['messages'][-1].content}")
    print(f"\nDetalhes da resposta: {resposta['tool_calls']}")  # Aqui está a ordem para o nosso script agir






