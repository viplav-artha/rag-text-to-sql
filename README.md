# rag-text-to-sql

A retrieval-augmented generation system that converts natural language questions into SQL queries, using retrieved schema/context to improve accuracy.

## Getting Started

### 1. Clone and install

```bash
git clone https://github.com/viplav-artha/rag-text-to-sql.git
cd rag-text-to-sql

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure `.env`

Create a `.env` file in the project root (never committed — it's git-ignored) with:

```
DATABASE_URL=<your Neon Postgres connection string, RAG branch>
REDIS_URL=<your Redis connection string, e.g. redis://localhost:6379>
AWS_PROFILE=<your AWS SSO profile with Bedrock access>
AWS_REGION=<e.g. us-east-1>
LANGCHAIN_API_KEY=<your LangSmith API key, only needed for running evals>
```

`RAG_DATABASE_URL` is optional and defaults to `sqlite:///./rag_store.db` — no need to set it unless you want the local RAG store somewhere else.

### 3. Start dependencies

- **Redis** (required for the cached `/query` endpoint):
  ```bash
  docker run -d --name rag-redis -p 6379:6379 redis:alpine
  # if the container already exists: docker start rag-redis
  ```
- **AWS Bedrock access** (required for every request — this is the LLM): make sure your SSO session is active:
  ```bash
  aws sso login --profile <your AWS_PROFILE>
  ```

### 4. First time only — seed the local RAG knowledge store

The app stores its RAG bookkeeping (schema descriptions, few-shot examples, company profiles) in a local SQLite file (`rag_store.db`), created automatically the first time the server starts — but that file starts **empty**. Before your first query will work, populate it:

```bash
python -m scripts.ingest_knowledge
```

Run this again any time the underlying data/company knowledge changes (it's idempotent — safe to re-run), or if `rag_store.db` is ever deleted/reset (a fresh clone, a new machine, a new session on an ephemeral environment). Skipping this step doesn't break the server — it starts fine — but the LLM will have no real schema to ground on and will guess column names that don't exist.

### 5. Run the server

```bash
uvicorn app.main:app --reload --port 8010
```

The API is now available at `http://localhost:8010` (Swagger docs at `/docs`). Two endpoints, both taking just `{"question": "..."}`:

```bash
curl -X POST http://localhost:8010/query \
  -H "Content-Type: application/json" \
  -d '{"question": "what was the total revenue for futwork in june 2026"}'
```

- `POST /query` — Redis-cached.
- `POST /query/no-cache` — always hits the real pipeline/database, skipping the cache (useful for testing).
