# rag-text-to-sql — Project Memory

## What this project is
A production-intent RAG-based text-to-SQL system for financial data. A Neon Postgres
(the `RAG` branch specifically, not `dev`/`production` — set via `NEON_BRANCH=RAG` in
`.env`) database holds a company's financial metrics matrix. Users ask natural-language
financial questions (e.g. "what was YoY revenue growth last quarter?"); the system retrieves
grounding context — relevant schema/column descriptions and similar few-shot NL→SQL example
pairs — via pgvector similarity search inside that same Neon database, then uses a LangGraph
workflow (retrieve → generate SQL → validate → execute → format) driven by an AWS Bedrock LLM
to produce and run the SQL, returning the answer. Embeddings for RAG retrieval use a local,
open-source model (`sentence-transformers/all-MiniLM-L6-v2`, 384-dim) — no AWS dependency for
that part, only the chat LLM uses Bedrock. Redis caches LLM output and SQL results to cut
latency/cost on repeated or similar questions. The whole thing is exposed as a FastAPI service.
Tech stack: Python, LangChain, LangGraph, langchain-aws (Bedrock chat LLM), sentence-transformers
(local embeddings), FastAPI, SQLAlchemy, Neon Postgres + pgvector, Redis.

**Multi-tenant from the start:** every RAG knowledge row (`schema_chunks`, `few_shot_examples`,
`company_profiles`) is scoped by an explicit `company` field, and retrieval always filters by it
before doing similarity search. Only one company exists today — **Futwork** (a telecalling/
voice-BPO platform; see its stored profile in `company_profiles`), whose real data lives in
`portfolio.futwork_vs_aop` in Neon — but the schema is built so a second company's data can be
added later (a similarly-shaped view joining that company's MIS/AOP tables) without one
company's questions ever retrieving another's context.

This is explicitly a **production-intent** build — real error handling, validation, and
tests are expected, not just a working demo.

## Repo
- GitHub: https://github.com/viplav-artha/rag-text-to-sql (public, account `viplav-artha`, no org)
- Local path: /Users/viplavsingh/Desktop/project/rag-text-to-sql

## How this project is being taught/built (rules for any session, including a fresh one)
- Teacher/student mode. Before writing any new file: explain WHY the file needs to
  exist and WHAT logic goes in it, in plain language. Analogies are fine and encouraged
  in chat explanations.
- One file at a time. Do not start the next file until the user has studied the
  current one and explicitly says they're ready to move on. Never auto-chain
  multiple files in one turn. Empty package-marker files (`__init__.py`) created
  alongside a real lesson file are supporting scaffolding, not separate lessons —
  same exception as adding a new dependency line to `requirements.txt`.
- After every file is created: update this file's "Current status" and
  "Files created so far" sections, AND add a matching entry to NOTES.md
  (Timeline graph + Routes Graph if applicable + logic/motive note). Do this
  immediately, without being asked again each time.
- NOTES.md must never use analogies — plain logic/motive explanations only.
  (This file, CLAUDE.md, and chat teaching CAN use analogies.)
- The repo is **public** — never put real secrets/credentials in any tracked file.
  `.env` stays git-ignored (already covered by `.gitignore`); only a future
  `.env.example` with placeholder values should ever be committed.
- Git/GitHub commands (init, repo create, add, commit, push) always get explicit
  user go-ahead before running, regardless of permission mode — show the exact
  command first.

## Current status
Stage: Lesson 14 (`app/graph/graph.py`) done — `langgraph` installed and
wired for real. All 5 nodes (retrieve, generate, validate, execute, format)
are now assembled into a compiled `StateGraph` with a conditional
validate→(generate|execute) retry edge, capped at `_MAX_RETRIES = 2`.
Verified two ways: `graph.invoke({...})` end-to-end on a real question
(correctly answered "INR 22,063,632" via the single `.invoke()` call, no
manual node chaining needed), and the routing function's boundary conditions
tested directly (no-error → execute, error-with-retries-left → generate,
error-retries-exhausted → execute, where lesson 13's defense-in-depth guard
catches it). The full retrieve → generate → validate → execute → format
pipeline this represents was itself verified end-to-end in lessons 12-13,
with two real bugs found and fixed there: lowercase `month_name` values, and
`format_answer_node` originally defaulting to USD instead of INR.
Additionally, `app/main.py` was built early (out of build order, at the
user's request) as a minimal FastAPI test harness — one `POST /query`
endpoint calling `graph.invoke()` directly, verified with a real HTTP
request. This is not the final lesson-18 file (no caching/schemas/routing
yet). Waiting on user review/go-ahead before starting lesson 15
(`app/services/query_service.py`), which wraps the compiled graph with
Redis cache check/write.
`DATABASE_URL` and `REDIS_URL` are both set in `.env`.

## Planned build order
Subject to adjustment as we go — update in place, don't just append.

1. **DONE** — `app/core/llm.py` — Bedrock chat LLM wrapper (`get_llm()`), user-supplied code
2. **DONE** — `app/core/config.py` — centralized settings (DB URL, Redis URL, embedding model, etc.)
3. **DONE** — `app/core/db.py` — Neon Postgres engine/session + pgvector extension bootstrap
4. **DONE** — `app/core/cache.py` — Redis client wrapper (get/set with TTL helpers)
5. **DONE** — `app/rag/embeddings.py` — open-source local embedding model wrapper (`all-MiniLM-L6-v2`, 384-dim)
6. **DONE** — `app/rag/schema_store.py` — pgvector store for financial schema/column descriptions
   (corrected post-hoc: added `company` + `schema_name` fields, see lesson 9 note)
7. **DONE** — `app/rag/example_store.py` — pgvector store for few-shot NL→SQL example pairs
   (corrected post-hoc: added `company` field)
8. **DONE** — `app/rag/retriever.py` — combines schema + example retrieval into one grounding context
   (corrected post-hoc: added company scoping + business-context section)
9. **DONE** — `app/rag/company_profile.py` — one-row-per-company business narrative (no embedding;
   exact fetch by company, not similarity search) — inserted into the build order once the need
   for multi-tenancy and business-context grounding became clear
10. **DONE** — `scripts/ingest_knowledge.py` + `data/companies/futwork.py` — idempotent script +
    data module that populate all three RAG stores with real Futwork data (67 confirmed metric
    descriptions + per-client billing/minutes columns via live column introspection + 5 few-shot
    examples). Run for real; 177 schema chunks + 5 examples ingested, zero skipped columns.
11. **DONE** — `app/graph/state.py` — LangGraph shared state schema (TypedDict)
12. **DONE** — `app/graph/nodes.py` — LangGraph nodes: retrieve context, generate SQL, validate SQL
13. **DONE** — `app/graph/execute_node.py` — LangGraph node: execute validated SQL, format result
14. **DONE** — `app/graph/graph.py` — assembles the StateGraph, wires nodes + conditional routing
15. **NEXT** — `app/services/query_service.py` — orchestration: Redis cache check → run graph → cache write
16. `app/api/schemas.py` — FastAPI request/response Pydantic models
17. `app/api/routes.py` — FastAPI router: `POST /query` endpoint
18. `app/main.py` — FastAPI app instance, mounts routers, startup/shutdown hooks.
    **A minimal early version already exists** (built ahead of schedule as a
    manual test harness — see "Files created so far" below); this lesson
    still needs to happen for real, to add Redis caching via
    `query_service.py`, proper request/response validation via
    `api/schemas.py`, and router structure via `api/routes.py`.

## Files created so far (chronological)
Matches NOTES.md's Timeline numbering exactly — empty/near-empty `__init__.py`
package markers are omitted from both (see the Maintenance instructions below).

1. `.gitignore` — standard Python ignore rules (created via init-project skill)
2. `README.md` — starter project README (created via init-project skill)
3. `requirements.txt` — dependency manifest, empty initially (created via init-project skill)
4. `.env` — local credentials file (git-ignored), created by the user, populated as
   each service's credentials are provided
5. `app/core/llm.py` — `get_llm()`, builds a `ChatBedrockConverse` LLM client from
   env-configured model ID / region / AWS profile
6. `app/core/config.py` — `get_settings()`, a cached `Settings` dataclass holding
   `DATABASE_URL`, `REDIS_URL`, `EMBEDDING_MODEL_NAME`, `CACHE_TTL_SECONDS`
   (field renamed from `embedding_model_id`/`BEDROCK_EMBEDDING_MODEL_ID` in
   lesson 5 once embeddings moved off Bedrock to a local model)
7. `app/core/db.py` — SQLAlchemy engine/session (psycopg v3 driver), `Base` for
   ORM models, `get_db()` (FastAPI dependency), `db_session()` (context manager),
   `init_pgvector_extension()`
8. `app/core/cache.py` — Redis client singleton, `make_cache_key()`,
   `cache_get()`/`cache_set()` (JSON-encoded, TTL-backed)
9. `app/rag/embeddings.py` — `get_embeddings()`, cached `HuggingFaceEmbeddings`
   wrapper around `sentence-transformers/all-MiniLM-L6-v2` (local, 384-dim)
10. `app/rag/schema_store.py` — `SchemaChunk` ORM model (`vector(384)` column),
    `add_schema_chunk()`, `search_schema()` (pgvector cosine-distance search).
    **Corrected post-hoc**: added `company` and `schema_name` fields/params so
    chunks record which company and which Postgres schema (`portfolio`, not
    `public`) they describe, and `search_schema()` filters by `company` before
    similarity ordering.
11. `app/rag/example_store.py` — `FewShotExample` ORM model (embeds `question`
    only), `add_example()`, `search_examples()` (top_k=3 by default).
    **Corrected post-hoc**: added `company` field/param, filtered the same way.
12. `app/rag/retriever.py` — `RetrievedContext` dataclass (+ `to_prompt_text()`),
    `retrieve_context()` combining schema + example search into one call.
    **Corrected post-hoc**: takes `company`, also fetches the company's business
    profile via `company_profile.py` and includes it as a "Business context"
    section in the prompt text; schema lines now show `schema_name.table_name.column`.
13. `app/rag/company_profile.py` — `CompanyProfile` ORM model (`company` primary
    key, `profile` text, no embedding column — fetched by exact company match,
    not similarity search), `get_company_profile()`, `upsert_company_profile()`
14. `data/companies/futwork.py` — Futwork's knowledge data: `PROFILE`,
    `EXCLUDED_COLUMNS`, `PER_CLIENT_TEMPLATES` (2), `METRIC_DESCRIPTIONS` (67),
    `FEW_SHOT_EXAMPLES` (5) — pure data, no logic
15. `scripts/ingest_knowledge.py` — introspects `portfolio.futwork_vs_aop`'s
    real columns, matches each against `futwork.py`'s data (per-client pattern
    or exact metric), and idempotently (re)populates all three RAG tables for
    company `futwork`
16. `app/graph/state.py` — `GraphState` TypedDict, the shared object every
    LangGraph node reads/writes; only `company`/`question` are required,
    every other field is `NotRequired` and filled in as the graph runs
17. `app/graph/nodes.py` — `retrieve_node()`, `generate_sql_node()`,
    `validate_sql_node()` — the retrieve/generate/validate stages of the
    pipeline, verified end-to-end against real Bedrock + Neon
18. `app/graph/execute_node.py` — `execute_sql_node()` (statement timeout,
    automatic row limit, Decimal/date serialization, defense-in-depth
    validation guard), `format_answer_node()` (LLM narrates results into
    plain English) — full 5-stage pipeline now verified end-to-end
19. `app/graph/graph.py` — `build_graph()` assembles all 5 nodes into a
    compiled `StateGraph`, `_route_after_validation()` conditional edge
    (retry generate on validation failure, capped at `_MAX_RETRIES = 2`),
    module-level `graph` ready for `.invoke()`
20. `app/main.py` — **early/minimal test harness**, built out of build-order
    ahead of lesson 15-17, at the user's explicit request, to manually test
    the compiled graph over HTTP. A `FastAPI` app with one `POST /query`
    endpoint that calls `graph.invoke()` directly — no Redis caching, no
    `api/schemas.py`/`api/routes.py` layering yet. Verified for real: a
    live POST request correctly returned "INR 22,063,632" for a real
    question. Will be substantially rewritten at lesson 18.

(Package markers actually created, for completeness, but untracked by the
numbering above: `app/__init__.py`, `app/core/__init__.py`,
`app/rag/__init__.py` — no longer empty as of the multi-tenancy correction,
imports the three RAG store modules for table registration —
`data/__init__.py`, `data/companies/__init__.py`, `scripts/__init__.py`,
`app/graph/__init__.py`.)

## Environment
- Activate venv: `source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run: `uvicorn app.main:app --reload` — currently the early/minimal test
  harness (see "Files created so far"), one `POST /query` endpoint
  (`{"company": "futwork", "question": "..."}`), no caching yet
- External services required, credentials supplied via `.env`:
  - AWS Bedrock (chat LLM only — embeddings are local, see lesson 5) —
    `BEDROCK_CHAT_MODEL_ID`, `BEDROCK_REGION`/`AWS_REGION`, `AWS_PROFILE`,
    `LLM_TEMPERATURE`. **Set in `.env` as of lesson 12**: `AWS_PROFILE=
    "Artha-stg-dev"`, `BEDROCK_CHAT_MODEL_ID="amazon.nova-pro-v1:0"` (not the
    `us.`-prefixed cross-region inference profile ID — the direct model ID,
    since that's what this account/role has `bedrock:InvokeModel` access to),
    `AWS_REGION="us-east-1"`. The `Artha-stg-dev` role initially had zero
    Bedrock permissions (`AccessDeniedException` on both `InvokeModel` and
    `ListFoundationModels`) — required an IAM policy update before this
    worked; if credentials/permissions ever need rotating, re-verify with
    `aws sts get-caller-identity --profile Artha-stg-dev` first.
  - Neon Postgres (`RAG` branch specifically, not `dev`/`production` —
    `NEON_BRANCH=RAG` in `.env`; pgvector extension enabled) — `DATABASE_URL`.
    Paste Neon's connection string as-is (`postgresql://...` or `postgres://...`);
    `app/core/db.py` rewrites it to `postgresql+psycopg://` automatically since
    the project uses the psycopg (v3) driver, not psycopg2. **Set in `.env` as of
    lesson 6.**
  - Redis (caching) — `REDIS_URL`. **Set in `.env`** as of lesson 6, pointing at
    a local Redis running in Docker (`docker run -d --name rag-redis -p
    6379:6379 redis:alpine`). Restart that container (`docker start rag-redis`)
    if it's not running — data is not persisted across container removal.
  - Optional overrides: `EMBEDDING_MODEL_NAME` (default
    `sentence-transformers/all-MiniLM-L6-v2`, runs locally, no credentials
    needed), `CACHE_TTL_SECONDS` (default `3600`)

## Known gaps / deliberately deferred (be honest, don't hide these)
- `get_llm()` validates config only at call-time, not at app startup — a misconfigured
  `.env` (missing `BEDROCK_CHAT_MODEL_ID`/region) won't surface until the first request
  that needs the LLM. A production version would add a startup health check.
- `_env`/`_env_int`/`_env_float` env-parsing helpers are duplicated between `llm.py`
  and `config.py` rather than shared from one utility module. Left as-is since
  `llm.py` is fixed user-supplied code; a natural later cleanup is a shared
  `app/core/env_utils.py` both files import from.
- `cache_set()` (`app/core/cache.py`) JSON-encodes whatever it's given; callers
  must pass plain JSON-serializable data (dicts/lists/strings/numbers), not raw
  DB row objects or datetimes. Worth double-checking when `query_service.py`
  (lesson 15) starts calling it.
- `sentence-transformers`/`torch` are heavy dependencies (torch alone ~100MB+
  download, plus the ~80MB model weights downloaded on first run and cached in
  `~/.cache/huggingface`) — fine for a dev/prototype box, but worth remembering
  for container image size / cold-start time if this is ever containerized.
- No migrations tool yet (e.g. Alembic) — `schema_chunks` (and future tables)
  were created ad hoc via `Base.metadata.create_all(engine)` during lesson 6's
  verification, run manually rather than as part of an app startup hook (that
  hook is still planned for `main.py`, lesson 18). A production version would
  want real migrations instead of `create_all()` — this has bitten us twice
  now: once for the multi-tenancy correction (empty tables, no data lost),
  and again in lesson 12 for the `is_per_entity` column (177 real rows
  existed by then — DROP + recreate + re-run `ingest_knowledge.py` worked
  cleanly only because that script is idempotent; this would be a real
  migration in any system with actual production data at stake).
- `Base.metadata.create_all()` only creates tables for models that have
  actually been imported somewhere first (that's what registers them on
  `Base.metadata`). `app/rag/__init__.py` now imports all three RAG store
  modules specifically so `import app.rag` always registers every table —
  discovered the hard way when `company_profiles` silently didn't exist after
  a `create_all()` call that never imported `company_profile.py`.
- `company` is a plain string column on `schema_chunks`/`few_shot_examples`/
  `company_profiles`, not a foreign key into a dedicated `companies` table —
  fine while there's one company (Futwork), but worth normalizing if/when
  the number of companies grows and needs real referential integrity or
  per-company metadata beyond a name.
- `FEW_SHOT_EXAMPLES` in `data/companies/futwork.py` deliberately starts small
  (5 examples) and avoids "most recent month" style queries, since
  `month_name` is text (not a date/number) and sorts alphabetically, not
  chronologically — a real trend/"last N months" query needs a month-name-
  to-number `CASE` mapping. Lesson 12 (`generate_sql_node`) does not yet
  solve this — a question asking for "the last 3 months" would currently
  risk generating an `ORDER BY month_name` that sorts wrong. Still open;
  revisit when trend/date-range queries are actually needed.
- **[Corrected, was previously mis-assessed]** Retrieval quality was
  initially thought to just have "weaker matches further down top_k" — lesson
  12's live testing proved this wrong: for "total revenue in March 2026,"
  `total_revenue` did not appear even at `top_k=15` — all 15 slots were
  `billing_amount_<client>` columns. Root cause: 55 near-identical per-client
  descriptions cluster so tightly that they can completely crowd out a
  genuinely more relevant distinct metric, no matter how large `top_k` is.
  **Fixed** by adding `SchemaChunk.is_per_entity` (set at ingestion time) and
  splitting `retrieve_context()` into two independent pool searches —
  distinct metrics (`is_per_entity=False`) and per-entity columns
  (`is_per_entity=True`) — so a distinct metric can never be crowded out by
  per-client noise. Re-verified: revenue, per-client billing, caller churn,
  and runway questions all now generate correct SQL.
- `db.py`'s `SessionLocal` needed `expire_on_commit=False`, added during
  lesson 12 verification — without it, ORM objects returned from a
  `db_session()` block (e.g. `RetrievedContext`'s `SchemaChunk`/
  `FewShotExample` lists, returned by `retrieve_node()`) raised
  `DetachedInstanceError` the moment their attributes were accessed outside
  that session (e.g. inside `generate_sql_node()`). Any future node that
  returns ORM objects across a `db_session()` boundary relies on this
  setting — worth remembering if a new detached-instance error appears.
- **[Fixed, lesson 13]** `month_name` in the real data is lowercase
  (`'march'`, not `'March'`) — the 5 few-shot examples used capitalized
  month names, and Postgres string comparison is case-sensitive, so every
  date-filtered query silently returned zero rows rather than erroring
  (caught when "total revenue in March 2026" returned `[]` despite that
  exact month/year existing in the data). Fixed in two places: the few-shot
  examples in `data/companies/futwork.py` (re-ingested), and an explicit
  instruction added to `generate_sql_node`'s system prompt in `nodes.py`, so
  the convention holds even for questions with no matching few-shot example.
- **[Fixed, lesson 13]** `format_answer_node()` (`execute_node.py`)
  originally only received the question and raw SQL result rows — no
  business context. Since nothing in the raw numbers says what currency
  they're in, the LLM defaulted to USD ("$22,063,632") for data that's
  actually INR. Fixed by passing `retrieved_context.company_profile` into
  its prompt. Worth remembering for any future formatting/narration step:
  raw numbers need currency/unit context explicitly stated, never assumed.

## Companion file
See `NOTES.md` for the plain-language, no-analogy study notes, the file-creation
Timeline graph, and the import-dependency Routes Graph.

## Maintenance instructions — MUST run after every new file is created
1. **Update `CLAUDE.md`** (this file): move the finished item's build-order entry
   to done, mark the new next item, update "Current status", append to "Files
   created so far".
2. **Update `NOTES.md` — Timeline graph**: append the new file as the next node,
   connected with `|` / `v` to the previous node, in strict creation order —
   except empty/near-empty `__init__.py` package markers, which are omitted
   entirely (no Timeline node, no File notes entry) since there's nothing in
   them worth studying.
3. **Update `NOTES.md` — Routes Graph**: only touch this if the new file contains
   actual import-relevant logic (skip config/text files and any `__init__.py`,
   even one with imports for side effects like table registration — that's
   plumbing, not something a reader needs to trace). This is a Mermaid (` ```mermaid graph TD `) diagram, rendered as a
   real flowchart by GitHub/VS Code — do not use hand-drawn ASCII arrows, they
   don't scale. There is exactly ONE Routes Graph diagram in NOTES.md — add the
   new node and its edges to that SAME diagram in place; never create a second,
   separate one elsewhere in the file. Assign the next number in the Routes
   Graph's OWN sequence as part of the node's label (independent from the
   Timeline number for the same file — the two graphs use different numbering,
   and NOTES.md must say so explicitly). Label each new edge with what it
   imports (e.g. `n2 -->|get_db| n6`) instead of maintaining a separate
   connections list.
4. **Update `NOTES.md` — File notes**: add a new `### [N] filename` entry with a
   `Motive` line and a `Logic` line. No analogies, short and factual.

Do all four every time, without waiting to be asked again.
