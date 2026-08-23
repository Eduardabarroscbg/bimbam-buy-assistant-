"""
BimBam Buy Assistant - Agente de IA com RAG
Responde perguntas sobre políticas de envio, reembolso, garantia,
pagamento e programa de afiliados da BimBam Buy, com base nos
documentos oficiais da empresa (PDFs).
"""

import os
import glob
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DOCS_PATH = os.getenv("DOCS_PATH", "./docs")
INDEX_PATH = os.getenv("INDEX_PATH", "./data/faiss_index")

if not GEMINI_API_KEY:
    raise RuntimeError("Defina a variável de ambiente GEMINI_API_KEY (veja .env.example)")

os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

app = FastAPI(
    title="BimBam Buy Assistant",
    description="Agente de IA (RAG) que responde perguntas sobre as políticas da BimBam Buy",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

retriever = None
llm = None

PROMPT_TEMPLATE = """Você é o assistente virtual da BimBam Buy. Responda à pergunta do
cliente em português, de forma clara e objetiva, usando APENAS as informações
do contexto abaixo. Se a resposta não estiver no contexto, diga que não encontrou
essa informação nos documentos disponíveis.

Contexto:
{context}

Pergunta: {question}

Resposta:"""


# ---------------------------------------------------------------------------
# Construção / carregamento do índice vetorial
# ---------------------------------------------------------------------------
def build_or_load_vectorstore() -> FAISS:
    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

    if os.path.exists(INDEX_PATH):
        return FAISS.load_local(
            INDEX_PATH, embeddings, allow_dangerous_deserialization=True
        )

    pdf_files = glob.glob(os.path.join(DOCS_PATH, "*.pdf"))
    if not pdf_files:
        raise RuntimeError(
            f"Nenhum PDF encontrado em {DOCS_PATH}. Coloque os documentos da "
            "BimBam Buy (ou os seus próprios) nessa pasta."
        )

    all_chunks = []
    # chunks maiores = menos pedaços = menos chamadas à API (evita estourar a quota gratuita)
    splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)

    for pdf_path in pdf_files:
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()
        chunks = splitter.split_documents(pages)
        for c in chunks:
            c.metadata["source"] = os.path.basename(pdf_path)
        all_chunks.extend(chunks)

    print(f"Gerando embeddings para {len(all_chunks)} pedaços de texto...")

    # processa em lotes pequenos, com espera entre eles e retry automático
    # em caso de limite de requisições da camada gratuita do Gemini (erro 429)
    batch_size = 10
    vectordb = None
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        attempt = 0
        while True:
            try:
                if vectordb is None:
                    vectordb = FAISS.from_documents(batch, embeddings)
                else:
                    vectordb.add_documents(batch)
                break
            except Exception as e:
                attempt += 1
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    wait = min(30, 5 * attempt)
                    print(f"Quota atingida, esperando {wait}s antes de tentar de novo...")
                    time.sleep(wait)
                    if attempt >= 6:
                        raise
                else:
                    raise
        print(f"  {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} processados")
        time.sleep(1)  # pequena pausa entre lotes para não bater no limite por minuto

    os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
    vectordb.save_local(INDEX_PATH)
    return vectordb


@app.on_event("startup")
def startup_event():
    global retriever, llm
    vectordb = build_or_load_vectorstore()
    retriever = vectordb.as_retriever(search_kwargs={"k": 4})
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", temperature=0.2)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    sources: list[str]


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    if not retriever or not llm:
        raise HTTPException(status_code=503, detail="Agente ainda não inicializado.")
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="A pergunta não pode estar vazia.")

    docs = retriever.invoke(payload.question)
    context = "\n\n".join(doc.page_content for doc in docs)
    sources = sorted({doc.metadata.get("source", "desconhecido") for doc in docs})

    prompt = PROMPT_TEMPLATE.format(context=context, question=payload.question)
    response = llm.invoke(prompt)

    # Nas versões novas da lib, response.content pode ser uma string OU uma
    # lista de blocos (ex: [{"type": "text", "text": "..."}]). Tratamos os dois casos.
    if isinstance(response.content, str):
        answer_text = response.content
    else:
        answer_text = "".join(
            block.get("text", "")
            for block in response.content
            if isinstance(block, dict) and block.get("type") == "text"
        )

    return AskResponse(answer=answer_text, sources=sources)