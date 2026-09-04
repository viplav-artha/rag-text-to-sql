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
(local embeddings), FastAPI, SQLAlchemy, Neon Postgres + pgvector, Redis, LangSmith (evals).

**Multi-tenant from the start:** every RAG knowledge row (`rag.schema_chunks`, `rag.few_shot_examples`,
`rag.company_profiles` — all three live in a dedicated `rag` Postgres schema, not `public`) is
scoped by an explicit `company` field, and retrieval always filters by it before doing similarity
search. Only one company exists today — **Futwork** (a telecalling/
voice-BPO platform; see its stored profile in `rag.company_profiles`), whose real data lives in
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
**Stage: Lesson 18 (`app/main.py` final rewrite) done and verified for
real — this was the last lesson in the planned build order. The build is
complete.**

`app/main.py` now has a real `lifespan` context manager (the modern
FastAPI startup-hook pattern, not the soft-deprecated `@app.on_event`
style) that runs `init_pgvector_extension()` and `Base.metadata.
create_all(engine)` once at app boot — an explicit `import app.rag` right
before it guarantees all three RAG models are registered first. Verified
for real: server restarted cleanly, row counts in `rag.schema_chunks`/
`rag.few_shot_examples`/`rag.company_profiles` were unchanged after
restart (177/5/1 — confirming `create_all()` never touches existing
tables), and the `/query` endpoint still returned a correct, real answer.

Every planned lesson (1 through 18) is now done, plus everything built
outside the numbered sequence at explicit user request along the way: the
`rag`-schema move for the RAG bookkeeping tables, and the LangSmith eval
infrastructure (2 datasets + 2 experiment runners, which already found and
fixed one real pipeline bug — see Known gaps). See "Files created so far"
below and `NOTES.md` for the full file-by-file history.

No further lessons are currently planned — future work would be genuinely
new scope (e.g. a second company, hardening one of the logged Known gaps,
or something the user decides next), not a continuation of this build
order.
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
15. **DONE** — `app/services/query_service.py` — orchestration: Redis cache check → run graph → cache write
16. **DONE** — `app/api/schemas.py` — FastAPI request/response Pydantic models
17. **DONE** — `app/api/routes.py` — FastAPI router: `POST /query` endpoint
18. **DONE** — `app/main.py` — FastAPI app instance, mounts router, `lifespan`
    startup hook (`init_pgvector_extension()` + `Base.metadata.create_all()`).
    Started as an early minimal test harness at lesson 12 and was
    incrementally completed in place across lessons 15-18 (caching, schema
    validation, router structure, startup hooks) rather than rewritten from
    scratch — **this is now the real, finished file**.

**Build order complete — all 18 planned lessons done.**

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
10. `app/rag/schema_store.py` — `SchemaChunk` ORM model (`vector(384)` column,
    lives in the `rag` Postgres schema via `__table_args__`), `add_schema_chunk()`,
    `search_schema()` (pgvector cosine-distance search). **Corrected post-hoc**:
    added `company` and `schema_name` fields/params so chunks record which
    company and which Postgres schema (`portfolio`, not `public` — this is a
    separate concept from the `rag` schema the table itself lives in, see
    above) they describe, and `search_schema()` filters by `company` before
    similarity ordering.
11. `app/rag/example_store.py` — `FewShotExample` ORM model (embeds `question`
    only, also in the `rag` schema), `add_example()`, `search_examples()`
    (top_k=3 by default). **Corrected post-hoc**: added `company` field/param,
    filtered the same way.
12. `app/rag/retriever.py` — `RetrievedContext` dataclass (+ `to_prompt_text()`),
    `retrieve_context()` combining schema + example search into one call.
    **Corrected post-hoc**: takes `company`, also fetches the company's business
    profile via `company_profile.py` and includes it as a "Business context"
    section in the prompt text; schema lines now show `schema_name.table_name.column`.
13. `app/rag/company_profile.py` — `CompanyProfile` ORM model (`company` primary
    key, `profile` text, no embedding column — fetched by exact company match,
    not similarity search, also in the `rag` schema), `get_company_profile()`,
    `upsert_company_profile()`
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
20. `app/main.py` — started at lesson 12 as an early minimal test harness
    (built ahead of build order, at the user's explicit request, calling
    `graph.invoke()` directly), then incrementally completed in place
    rather than rewritten from scratch: **lesson 15** switched it to
    `run_query()` for caching; **lesson 16** moved its inline
    `QueryRequest`/`QueryResponse` out to `api/schemas.py`; **lesson 17**
    replaced its own `@app.post` endpoint with `app.include_router(router)`;
    **lesson 18** added the `lifespan` startup hook
    (`init_pgvector_extension()` + `Base.metadata.create_all()`, guarded by
    an explicit `import app.rag` for model registration). **This is now
    the real, finished file** — verified for real: clean restart, row
    counts in all three RAG tables unchanged after restart (confirming
    `create_all()` never touches existing data), `/query` still correct.
21. `evals/__init__.py` — empty package marker for the `evals` package
22. `evals/create_financial_qa_dataset.py` — idempotent script that syncs the
    `financial-qa-eval-futwork` LangSmith dataset (7 question/expected_sql/
    expected_columns examples) — powers execution-accuracy, retrieval-recall,
    and answer-groundedness evals
23. `evals/create_sql_safety_dataset.py` — idempotent script that syncs the
    `sql-safety-eval-futwork` LangSmith dataset (10 adversarial
    candidate_sql examples that `validate_sql_node` must reject) — powers
    the SQL-safety eval
24. `evals/run_financial_qa_eval.py` — runs the full graph against every
    example in `financial-qa-eval-futwork` via `langsmith.evaluate()`;
    three evaluators — `execution_accuracy` (projects actual/expected rows
    down to just `expected_columns` before comparing, so harmless extra
    columns aren't penalized), `retrieval_recall` (are `expected_columns`
    present in `retrieved_columns`?), `answer_groundedness` (does
    `final_answer` state a number within tolerance of the reference value,
    without the wrong currency?) — run for real: 7/7 on all three metrics
    after the `schema_top_k` fix (see Known gaps)
25. `evals/run_sql_safety_eval.py` — runs `validate_sql_node` directly
    against every example in `sql-safety-eval-futwork`; one evaluator,
    `safety_rejection`, checks `validation_error` came back non-`None` —
    run for real: 10/10
26. `app/services/__init__.py` — empty package marker for the `app.services` package
27. `app/services/query_service.py` — `run_query(company, question)`:
    Redis cache check via `make_cache_key()`/`cache_get()`, `graph.invoke()`
    on a miss, narrows the state to 5 JSON-safe fields, only caches genuine
    successes (`validation_error`/`execution_error` both `None`). Verified
    live over HTTP via `app/main.py` (now calling `run_query()` instead of
    `graph.invoke()` directly): first request 22.6s, identical second
    request 0.065s (cache hit).
28. `app/api/__init__.py` — empty package marker for the `app.api` package
29. `app/api/schemas.py` — `QueryRequest` (`company`/`question`, required,
    whitespace-stripped, rejected if blank, `question` capped at 500 chars
    via a `field_validator`) and `QueryResponse` (same 5 fields as before) —
    replaces the inline models that used to live in `app/main.py`. Verified
    live over HTTP: a blank question returns a clean `422`, a valid one
    still returns `200` with the correct answer.
30. `app/api/routes.py` — `APIRouter` with the `POST /query` endpoint;
    wraps `run_query()` in `try`/`except KeyError` to turn an unknown
    company into a clean `404` instead of an unhandled `500`. `app/main.py`
    now mounts this router via `include_router()` instead of defining the
    endpoint itself. All three paths (unknown company, blank question,
    valid question) re-verified live over HTTP.

(Package markers actually created, for completeness, but untracked by the
numbering above: `app/__init__.py`, `app/core/__init__.py`,
`app/rag/__init__.py` — no longer empty as of the multi-tenancy correction,
imports the three RAG store modules for table registration —
`data/__init__.py`, `data/companies/__init__.py`, `scripts/__init__.py`,
`app/graph/__init__.py`.)

## Environment
- Activate venv: `source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run: `uvicorn app.main:app --reload` — the real, finished app as of
  lesson 18: one `POST /query` endpoint
  (`{"company": "futwork", "question": "..."}`), Redis-cached via
  `query_service.py`, validated via `api/schemas.py`, routed via
  `api/routes.py`, with a `lifespan` startup hook that bootstraps the
  pgvector extension and RAG tables automatically
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
  - LangSmith (evals) — `LANGCHAIN_API_KEY`. **Set in `.env`**. The `langsmith`
    `Client()` reads this automatically; no code in this project needs to
    reference it directly.

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
  want real migrations instead of `create_all()` — this has bitten us three
  times now: once for the multi-tenancy correction (empty tables, no data
  lost), again in lesson 12 for the `is_per_entity` column, and again when
  the three RAG tables were moved from `public` into a dedicated `rag`
  schema (177 real rows existed each time — DROP + recreate + re-run
  `ingest_knowledge.py` worked cleanly only because that script is
  idempotent; this would be a real migration in any system with actual
  production data at stake).
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
- **LangSmith example IDs are permanently non-reusable within a dataset**,
  even after a hard delete (`delete_examples(..., hard_delete=True)`) —
  confirmed via live testing while building the eval dataset sync scripts.
  A deterministic-UUID-based upsert design (generate the same ID from the
  same content every run) does **not** work here: deleting then recreating
  an example with that same ID throws a `409 Conflict`. The working pattern
  is to match existing examples by their actual content (`question`/
  `candidate_sql` text) and always let the server assign fresh IDs on
  create — see `evals/create_financial_qa_dataset.py` and
  `evals/create_sql_safety_dataset.py`. Also note `delete_examples()`
  defaults to a *soft* delete (`hard_delete=False`), which hides an example
  from `list_examples()` but still doesn't free its ID — always pass
  `hard_delete=True` when the intent is a real sync.
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
- **[Fixed, eval-driven]** `retrieve_context()`'s `schema_top_k` default was
  raised from 5 to 8 after the financial-QA eval showed a real bug: a
  question needing all 6 AR-aging columns could only ever get 5 of them
  under the old default, regardless of ranking quality — a capacity
  problem, not a ranking problem. Fixed for real (re-run confirmed
  `retrieval_recall`/`execution_accuracy` both hit 1.0 for that question).
- **Still open, minor, non-urgent**: for "How does actual EBITDA compare to
  the AOP target for June 2026?", plain `ebitda` doesn't rank in the
  retrieved top-15 at all — `ebitda_targetted`/`ebitda_pct_targetted`/
  `ebitda_margin_pct` all rank highly (their descriptions share vocabulary
  with "AOP target"), but `ebitda`'s own description doesn't overlap with
  the question's wording. This is a genuine embedding-similarity quirk, not
  something `schema_top_k` can fix by brute force. Didn't cause a wrong
  answer in practice (the near-identical few-shot example carried the LLM
  through), so left as a monitored gap rather than chased further — revisit
  if it ever causes an actual wrong-SQL generation.
- **[Fixed, lesson 17]** `app/api/schemas.py`'s `QueryRequest` validates
  shape only (non-empty, length-capped), not whether `company` is one the
  pipeline actually knows about — an unrecognized company reaches
  `nodes.py`'s `_get_company_data()`, which raises a plain `KeyError`.
  `app/api/routes.py` now catches that specific exception and returns a
  clean `404 Unknown company: '...'` instead of an unhandled `500`.
  **Still an open, smaller gap**: catching bare `KeyError` is a little
  broad — some unrelated bug could theoretically also raise a `KeyError`
  in this call path and get misreported as "unknown company." A more
  precise fix would expose a dedicated `is_known_company()` check from
  `nodes.py`'s `_COMPANY_DATA` registry and validate *before* calling the
  graph at all. Not urgent since there's currently no other source of
  `KeyError` in this path, but worth doing if/when that stops being true.

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
