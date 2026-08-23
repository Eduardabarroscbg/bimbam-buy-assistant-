# BimBam Buy Assistant 🛍️🤖

Agente de Inteligência Artificial com **RAG (Retrieval-Augmented Generation)** que responde, em linguagem natural, perguntas sobre as políticas oficiais da BimBam Buy (pagamento, garantia, envios, reembolsos e programa de afiliados), com base nos documentos internos da empresa.

Projeto desenvolvido como desafio final do **Challenge RAG — Alura / Oracle Next Education**.

---

## 📌 Descrição geral do projeto

Empresas como a BimBam Buy possuem diversos documentos internos (políticas de pagamento, garantia, envio, reembolso, afiliados) e seus times e clientes gastam tempo procurando informações manualmente nesses arquivos. Este projeto resolve esse problema com um agente de IA que:

1. Lê e processa os documentos em PDF da empresa;
2. Gera embeddings vetoriais do conteúdo;
3. Permite que qualquer pessoa faça perguntas em linguagem natural e receba respostas diretas, com indicação da fonte usada.

---

## 🏗️ Arquitetura da solução

```
Usuário (pergunta em linguagem natural)
            │
            ▼
      FastAPI (endpoint /ask)
            │
            ▼
   LangChain RetrievalQA Chain
     ┌──────────┴──────────┐
     ▼                     ▼
FAISS Vector Store   Google Gemini
(embeddings dos       (gemini-1.5-flash)
PDFs da BimBam Buy)   gera a resposta final
     ▲
     │
PyPDF + RecursiveCharacterTextSplitter
(carrega e "fatia" os PDFs na inicialização)
```

**Fluxo:**
1. Na inicialização, a aplicação lê todos os PDFs da pasta `docs/`.
2. O texto é dividido em pedaços (*chunks*) e transformado em vetores com o modelo de embeddings do Gemini (`text-embedding-004`).
3. Os vetores são armazenados no **FAISS** (índice salvo localmente para não reprocessar a cada reinício).
4. Quando o usuário envia uma pergunta em `POST /ask`, o retriever busca os trechos mais relevantes e o **Gemini** gera a resposta final com base neles.

---

## 🧰 Tecnologias utilizadas

| Camada | Tecnologia |
|---|---|
| API | FastAPI (Python 3.11) |
| Orquestração RAG | LangChain |
| LLM | Google Gemini (`gemini-1.5-flash`) |
| Embeddings | Google Generative AI Embeddings (`text-embedding-004`) |
| Banco vetorial | FAISS |
| Leitura de PDF | PyPDF |
| Containerização | Docker |
| Deploy | Oracle Cloud Infrastructure (OCI Compute) |

---

## 📁 Documentos utilizados

Documentos oficiais da BimBam Buy (fornecidos como material de apoio do desafio):

- FAQ Métodos de Pagamento
- Manual de Garantia
- Guia de Envios
- Programa de Afiliados
- Política de Reembolsos e Devoluções

> Coloque os arquivos PDF dentro da pasta `docs/` antes de subir a aplicação.

---

## 🚀 Como executar localmente

### 1. Clonar o repositório
```bash
git clone https://github.com/SEU-USUARIO/bimbam-buy-assistant.git
cd bimbam-buy-assistant
```

### 2. Configurar variáveis de ambiente
```bash
cp .env.example .env
```
Edite o `.env` e insira sua chave da API do Gemini:
```
GEMINI_API_KEY=sua_chave_gemini_aqui
```

### 3. Colocar os documentos
Coloque os PDFs da BimBam Buy dentro da pasta `docs/`.

### 4. Rodar com Docker
```bash
docker compose up --build
```
A API estará disponível em `http://localhost:8000`.

### 5. Rodar sem Docker (ambiente virtual)
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## 📡 Endpoints da API

### `GET /health`
Verifica se o agente está no ar.
```json
{ "status": "healthy" }
```

### `POST /ask`
Envia uma pergunta ao agente.

**Request:**
```json
{
  "question": "Quais são as formas de pagamento aceitas na BimBam Buy?"
}
```

**Response:**
```json
{
  "answer": "A BimBam Buy aceita cartão de crédito, débito, Pix e boleto bancário...",
  "sources": ["FAQ Métodos de Pagamento - BimBam Buy (PT-BR).pdf"]
}
```

Documentação interativa (Swagger UI): `http://localhost:8000/docs`

---

## 💬 Exemplos de perguntas e respostas

| Pergunta | Resposta esperada (resumo) |
|---|---|
| "Quais formas de pagamento a BimBam Buy aceita?" | Lista os métodos descritos no FAQ de pagamentos |
| "Quanto tempo tenho para pedir reembolso?" | Prazo descrito na Política de Reembolsos |
| "Como funciona o programa de afiliados?" | Regras e comissões do programa |
| "Minha garantia cobre defeito de fabricação?" | Trecho relevante do Manual de Garantia |
| "Qual o prazo de entrega para minha região?" | Informação do Guia de Envios |

---

## ☁️ Deploy na Oracle Cloud Infrastructure (OCI)

1. Criar uma instância **OCI Compute** (Always Free — Ampere/VM.Standard.E2.1.Micro).
2. Instalar Docker na instância:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-plugin
   ```
3. Copiar o projeto para a instância (via `git clone` ou `scp`).
4. Configurar o `.env` com a `GEMINI_API_KEY`.
5. Liberar a porta 8000 na *Security List* / *Network Security Group* da VCN.
6. Subir a aplicação:
   ```bash
   docker compose up -d --build
   ```
7. Acessar publicamente via `http://<IP-PUBLICO-DA-INSTANCIA>:8000/docs`.

> 🔗 **URL de produção:** `http://<IP-PUBLICO>:8000`
> 📸 Captura de tela do deploy: *(adicionar print da aplicação rodando na OCI)*

---

## 📂 Estrutura do repositório

```
bimbam-buy-assistant/
├── app/
│   └── main.py
├── docs/                  # PDFs da BimBam Buy
├── data/                  # índice FAISS (gerado automaticamente)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 👤 Autor

Projeto desenvolvido para o **Challenge RAG — Alura / Oracle Next Education**.
