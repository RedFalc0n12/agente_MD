from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder,PromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.tools import tool
from langchain.agents import create_agent


# 5.Criando um "documento" simulado que a IA nunca viu antes 
# Documento (Fase 5 - RAG)
meu_documento = Document(
    page_content="A linguagem Python foi criada em 2004 por felipe gijsen downs. O mascote da linguagem foi inspirado em um grupo de comédia britânico chamado Monty Python.",
    metadata={"fonte": "manual_interno.txt"}
)

#6. criando ferramenta para a IA acessar o documento (Fase 6 - tools)
@tool
def acessar_documento(query: str):
    """Acessa o documento e retorna o conteúdo"""
    return meu_documento.page_content

# 1. O Modelo (Fase 1 - O mesmo de sempre)
llm = ChatOpenAI(
    base_url="http://localhost:1234/v1", # Ou remova o base_url para usar a OpenAI real
    api_key="local", 
    temperature=0.0,
    model="phi-3.5-mini-instruct"
)
#llm_ferramenta = llm.bind_tools([acessar_documento])

agente = create_agent(
    llm, 
    tools=[acessar_documento], 
    
)

# 2. O Gabarito (Fase 2 - Agora com um espaço para o histórico)
# Note que mudamos para ChatPromptTemplate para separar quem está falando (sistema vs humano)
prompt = ChatPromptTemplate.from_messages([
    ("system", """Responda à pergunta abaixo com base no documento fornecido pela ferramenta acessar_documento.
    Contexto: {contexto}"""),
    
    # Esta é a gaveta mágica onde o LangChain vai injetar as mensagens antigas!
    MessagesPlaceholder(variable_name="historico_da_conversa"),
    
    ("human", "{pergunta_atual}")
])

parse = StrOutputParser()

# 3. A Corrente (Fase 3)
chain_basica = prompt | agente 

# ==========================================
# 🌟 A MÁGICA DA FASE 4: O GERENCIADOR DE MEMÓRIA
# ==========================================

# Criamos um "arquivo" (dicionário) para guardar o histórico de diferentes usuários
historicos_salvos = {}

# Função para pegar a "pasta" certa do arquivo baseado no ID da sessão
def pegar_historico(session_id: str):
    if session_id not in historicos_salvos:
        historicos_salvos[session_id] = ChatMessageHistory()
    return historicos_salvos[session_id]

# Colocamos a "mochila" na nossa chain básica
chain_com_memoria = RunnableWithMessageHistory(
    chain_basica,
    pegar_historico, # A função que ensinamos acima
    input_messages_key="pergunta_atual",       # Qual variável é a pergunta nova?
    history_messages_key="historico_da_conversa" # Onde eu injeto as antigas?
)






# ==========================================
# TESTANDO A MEMÓRIA e ferramenta (Fase 6)
# ==========================================

# Pergunta 1
print("\n--- RODADA 1 ---")
resposta_1 = chain_com_memoria.invoke(
    
    {"contexto": "","pergunta_atual": "segundo o documento qual o assunto deste?"},
    config={"configurable": {"session_id": "usuario_123"}} # Passando a etiqueta da pasta!
)
print(resposta_1["messages"][-1].content) 
#print(resposta_1.content) # Estará vazio!
#print(resposta_1.tool_calls) # Aqui está a ordem para o nosso script agir
# Pergunta 2 (O modelo precisa lembrar!)
print("\n--- RODADA 2 ---")
resposta_2 = chain_com_memoria.invoke(
    {"contexto": "","pergunta_atual": "segundo o documento quem criou a linguagem Python e em que ano?"},
    config={"configurable": {"session_id": "usuario_123"}} # Mesma pasta!
)
print(resposta_2["messages"][-1].content)
#print(resposta_2.content)
#print(resposta_2.tool_calls) # Aqui está a ordem para o nosso script agir