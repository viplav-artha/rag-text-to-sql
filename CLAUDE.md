# rag-text-to-sql — Project Memory

## What this project is
A production-intent RAG-based text-to-SQL system for financial data. A Neon Postgres
(the `RAG` branch specifically, not `dev`/`production` — set via `NEON_BRANCH=RAG` in
`.env`) database holds a company's financial metrics matrix. Users ask natural-language
financial questions (e.g. "what was YoY revenue growth last quarter?"); the system retrieves
grounding context — relevant schema/column descriptions and similar few-shot NL→SQL example
pairs — from a local SQLite store (`rag_store.db`, created automatically at server startup;
see below), then uses a LangGraph workflow (detect company → retrieve → generate SQL →
validate → execute → format) driven by an AWS Bedrock LLM to produce and run the SQL,
returning the answer. Embeddings for RAG retrieval use a local, open-source model
(`sentence-transformers/all-MiniLM-L6-v2`, 384-dim) — no AWS dependency for that part, only
the chat LLM uses Bedrock. The whole thing is exposed as a FastAPI service. There is
deliberately no caching layer — every request runs the real pipeline; Redis was removed
entirely at explicit user request, see Known gaps.
Tech stack: Python, LangChain, LangGraph, langchain-aws (Bedrock chat LLM), sentence-transformers
(local embeddings), FastAPI, SQLAlchemy, Neon Postgres (real financial data only), SQLite
(RAG bookkeeping), LangSmith (evals).

**Multi-tenant from the start:** every RAG knowledge row (`schema_chunks`, `few_shot_examples`,
`company_profiles` — all three live in the local SQLite file, not Neon; originally lived in a
dedicated `rag` Postgres schema on Neon, moved off it entirely at explicit user request — see
Known gaps) is scoped by an explicit `company` field, and retrieval always filters by it before
doing similarity search (now computed in Python via cosine similarity, not pgvector, since
SQLite has no vector column type). The caller doesn't even supply `company` anymore — the
pipeline detects it from the question text itself (`detect_company_node`, see the build-order
notes below). Only one company exists today — **Futwork** (a telecalling/voice-BPO platform;
see its stored profile in `company_profiles`), whose real data lives in
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

No further lessons are currently planned — future work is genuinely new
scope beyond the original build order, decided as it comes up. First
addition post-build: a second endpoint, `POST /query/no-cache`, added at
the user's explicit request — same request/response shape as `/query`,
but deliberately bypasses Redis entirely (no `cache_get`/`cache_set`) so
it always hits the real pipeline and database, useful for testing/
debugging without a stale cached answer masking a real change. Backed by
a new `run_query_no_cache()` in `query_service.py`, reusing the same
`_extract_result()` shaping logic as `run_query()`. Verified for real:
two identical requests both took full pipeline latency (no speedup on the
second call, unlike `/query`'s ~0.065s cache-hit case), and a direct
Redis check confirmed no cache entry was ever written for that question.

Second post-build addition: reworked how the pipeline picks which database
table to query for a company. Previously `nodes.py` computed one hardcoded
`allowed_table` string per company and dictated it to the LLM; now each
company's data module (`data/companies/futwork.py`) exposes a `TABLES`
list (`{schema, table, description}` per table), `generate_sql_node` shows
the LLM the whole list and lets the LLM pick the matching one, and
`validate_sql_node` accepts SQL against any entry in that list instead of
one fixed string — see Known gaps for the full before/after and what's
still hardcoded (which companies exist at all, via `_COMPANY_DATA` in
`nodes.py`). Verified for real via `POST /query/no-cache` against live
Bedrock + Neon: the LLM, shown the new `TABLES` list, correctly picked
`portfolio.futwork_vs_aop` itself and produced valid, correct SQL on the
first try.

Third post-build addition: `company` is no longer a request field at all —
the pipeline now auto-detects it from the question text itself. A new
`detect_company_node` (in `nodes.py`) runs first in the graph, shows the
LLM every known company (name + one-line business summary, via a new
`_format_known_companies()` helper reading the same `_COMPANY_DATA`
registry), and asks it to pick which one the question is about (or
`UNKNOWN`). A match sets `company` in graph state and the pipeline
proceeds exactly as before; no match sets `company_detection_error` and
`graph.py`'s new conditional edge routes straight to `END`, so
`retrieve_node`/`generate_sql_node`/etc. never run for a request the
pipeline can't confidently attribute to a known company. `QueryRequest`
now only has `question`; `QueryResponse` gained `company` and
`company_detection_error`; `run_query()`/`run_query_no_cache()` dropped
their `company` parameter (cache key is now `question`-only); `routes.py`
checks `company_detection_error` and raises the same `404` as before,
replacing the old `except KeyError` (which is no longer reachable — see
Known gaps). Verified for real against live Bedrock + Neon: `{"question":
"tell me the revenue of the futwork for june 2026"}` (no `company` field)
correctly detected `futwork` and returned the right answer; a question
naming an unrecognized company correctly returned a `404` instead of a
guess or a crash.

Fourth post-build addition: the three RAG bookkeeping tables
(`schema_chunks`, `few_shot_examples`, `company_profiles`) moved off Neon
entirely, at explicit user request — they now live in a local SQLite file
(`rag_store.db`), created automatically the first time the server starts
(`app/main.py`'s `lifespan` hook now runs `RagBase.metadata.
create_all(rag_engine)` instead of `init_pgvector_extension()` +
`Base.metadata.create_all(engine)`, both deleted). Neon's only remaining
job is the real financial data table (`portfolio.futwork_vs_aop`),
queried directly with raw SQL — it no longer has any ORM models
registered on it at all. `app/core/db.py` now manages two databases:
the existing Neon `engine`/`SessionLocal`/`Base`/`db_session()`
(unchanged), plus new SQLite `rag_engine`/`RagSessionLocal`/`RagBase`/
`rag_db_session()`. Since SQLite has no pgvector, `SchemaChunk`/
`FewShotExample`'s `embedding` column changed from `Vector(384)` to a new
`VectorJSON` type (`app/rag/vector_utils.py` — a `TypeDecorator` that
JSON-encodes/decodes a `list[float]`), and `search_schema()`/
`search_examples()` now rank candidates by a plain-Python
`cosine_similarity()` instead of a pgvector `ORDER BY` clause — fine at
this data size (177 rows), see Known gaps for the scaling caveat.
`scripts/ingest_knowledge.py` now writes via `rag_db_session()` and calls
`RagBase.metadata.create_all(rag_engine)` itself, so it works standalone
even before the server has ever been started. `RAG_DATABASE_URL`
(optional, defaults to `sqlite:///./rag_store.db`) is the new setting;
`pgvector` was removed from `requirements.txt` and `*.db`/`*.sqlite3`
added to `.gitignore`. Verified for real: deleted `rag_store.db`, started
the server with no file present — it created the file and all three
tables itself — then ran `ingest_knowledge.py` (177 chunks + 5 examples,
matching the old Neon-era counts exactly) and confirmed a live
`/query/no-cache` request still retrieved correct context and answered
correctly. The old Neon `rag` schema tables were left in place, now
orphaned/unused — not dropped automatically (a destructive Neon change
wasn't part of this ask); worth cleaning up manually if desired.

Fifth post-build addition: Redis and all caching removed entirely, at
explicit user request ("we don't need caching anymore"). Deleted
`app/core/cache.py` outright (`get_redis_client()`, `make_cache_key()`,
`cache_get()`/`cache_set()` — all gone). `app/core/config.py`'s `Settings`
dropped `redis_url`/`cache_ttl_seconds`, and `_env_int()` was deleted too
since caching was its only caller. `app/services/query_service.py`
shrank back down to a single `run_query(question)` that just calls
`graph.invoke()` and shapes the result — no cache check, no
`_is_cacheable()`. Since a no-cache-vs-cached distinction no longer means
anything, `POST /query/no-cache` was removed too (it would've been byte-
for-byte identical to `/query` going forward) — `app/api/routes.py` is
back down to the one `POST /query` endpoint. `redis` removed from
`requirements.txt`; `REDIS_URL`/`CACHE_TTL_SECONDS` are no longer read by
anything (harmless if still present in `.env`, just unused).
`README.md`'s setup steps updated to drop the Redis/Docker step entirely
— running the server no longer needs Docker at all. Verified for real:
restarted the server with Docker not even running, confirmed clean
startup, and a live `/query` request for "what was the total revenue for
futwork in june 2026" returned the correct SQL and answer with zero Redis
involvement; confirmed `/query/no-cache` now correctly 404s (route no
longer exists).
Sixth post-build addition: `ARCHITECTURE.md`, at the user's request, reviewing
a hand-drawn architecture diagram they made and adding what it was missing —
most notably the entire `detect_company_node` stage (their diagram started at
`retrieve_node`), the conditional (not unconditional) retry loop, all three
external systems (Bedrock/Neon/SQLite), the offline ingestion pipeline that
populates the SQLite RAG store, the HTTP layer, and an explicit note that
there's deliberately no caching. Contains a corrected Mermaid flowchart of the
full request path plus the separate offline ingestion path.

`DATABASE_URL` is set in `.env`.

## Planned build order
Subject to adjustment as we go — update in place, don't just append.

1. **DONE** — `app/core/llm.py` — Bedrock chat LLM wrapper (`get_llm()`), user-supplied code
2. **DONE** — `app/core/config.py` — centralized settings (DB URL, embedding model, etc.)
3. **DONE** — `app/core/db.py` — Neon Postgres engine/session + pgvector extension bootstrap
4. **DONE, later REMOVED** — `app/core/cache.py` — Redis client wrapper (get/set with TTL helpers) — deleted post-build when caching was removed entirely; see Known gaps and Current status
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
   lesson 5 once embeddings moved off Bedrock to a local model).
   **Corrected post-hoc, RAG store moved off Neon entirely**: gained
   `rag_database_url` (see lesson 10's note).
   **Corrected post-hoc, Redis removed entirely**: `redis_url` and
   `cache_ttl_seconds` deleted from `Settings`, along with the
   `REDIS_URL`-missing validation and the now-unused `_env_int()` helper
   (it had no other caller). `Settings` is down to `database_url`,
   `embedding_model_name`, `rag_database_url`.
7. `app/core/db.py` — SQLAlchemy engine/session (psycopg v3 driver), `Base` for
   ORM models, `get_db()` (FastAPI dependency), `db_session()` (context manager),
   `init_pgvector_extension()`. **Corrected post-hoc**: `init_pgvector_extension()`
   deleted (nothing uses pgvector anymore); added a second, independent
   SQLite engine/session (`rag_engine`, `RagSessionLocal`, `RagBase`,
   `rag_db_session()`) for the RAG bookkeeping tables — see lesson 10's note.
   `engine`/`SessionLocal`/`Base`/`db_session()` (Neon) are otherwise
   unchanged and now used only for the real financial data table.
8. `app/core/cache.py` — Redis client singleton, `make_cache_key()`,
   `cache_get()`/`cache_set()` (JSON-encoded, TTL-backed). **[REMOVED,
   post-build]**: deleted entirely at explicit user request ("we don't
   need caching anymore") — see Current status and Known gaps for the
   full removal (also touched `config.py`, `query_service.py`,
   `routes.py`, `requirements.txt`).
9. `app/rag/embeddings.py` — `get_embeddings()`, cached `HuggingFaceEmbeddings`
   wrapper around `sentence-transformers/all-MiniLM-L6-v2` (local, 384-dim)
10. `app/rag/schema_store.py` — `SchemaChunk` ORM model (`vector(384)` column,
    lives in the `rag` Postgres schema via `__table_args__`), `add_schema_chunk()`,
    `search_schema()` (pgvector cosine-distance search). **Corrected post-hoc**:
    added `company` and `schema_name` fields/params so chunks record which
    company and which Postgres schema (`portfolio`, not `public` — this is a
    separate concept from the `rag` schema the table itself lives in, see
    above) they describe, and `search_schema()` filters by `company` before
    similarity ordering. **Corrected post-hoc, moved off Neon entirely**:
    now subclasses `RagBase` (SQLite) instead of `Base` (Neon), dropped
    `__table_args__` (no Postgres schema concept in SQLite), `embedding`
    changed from `Vector(384)` to the new `VectorJSON` type, and
    `search_schema()` ranks in Python via `cosine_similarity()` instead of
    a pgvector `ORDER BY` clause.
11. `app/rag/example_store.py` — `FewShotExample` ORM model (embeds `question`
    only, also in the `rag` schema), `add_example()`, `search_examples()`
    (top_k=3 by default). **Corrected post-hoc**: added `company` field/param,
    filtered the same way. **Corrected post-hoc, moved off Neon entirely**:
    same treatment as `schema_store.py` above — `RagBase`, no
    `__table_args__`, `VectorJSON`, Python-side `cosine_similarity()` ranking.
12. `app/rag/retriever.py` — `RetrievedContext` dataclass (+ `to_prompt_text()`),
    `retrieve_context()` combining schema + example search into one call.
    **Corrected post-hoc**: takes `company`, also fetches the company's business
    profile via `company_profile.py` and includes it as a "Business context"
    section in the prompt text; schema lines now show `schema_name.table_name.column`.
13. `app/rag/company_profile.py` — `CompanyProfile` ORM model (`company` primary
    key, `profile` text, no embedding column — fetched by exact company match,
    not similarity search, also in the `rag` schema), `get_company_profile()`,
    `upsert_company_profile()`. **Corrected post-hoc, moved off Neon
    entirely**: now subclasses `RagBase` instead of `Base`, dropped
    `__table_args__` — no embedding column to begin with, so no
    `VectorJSON` change needed here.
14. `data/companies/futwork.py` — Futwork's knowledge data: `PROFILE`,
    `EXCLUDED_COLUMNS`, `PER_CLIENT_TEMPLATES` (2), `METRIC_DESCRIPTIONS` (67),
    `FEW_SHOT_EXAMPLES` (5) — pure data, no logic. **Corrected post-hoc**:
    added `TABLES` (list of `{schema, table, description}` dicts, one entry
    today) — the query-time table registry `nodes.py` shows the LLM so it
    can pick the table itself; `SCHEMA_NAME`/`TABLE_NAME` are unchanged and
    still drive `ingest_knowledge.py`'s column introspection.
15. `scripts/ingest_knowledge.py` — introspects `portfolio.futwork_vs_aop`'s
    real columns, matches each against `futwork.py`'s data (per-client pattern
    or exact metric), and idempotently (re)populates all three RAG tables for
    company `futwork`. **Corrected post-hoc, moved off Neon entirely**:
    writes now go through `rag_db_session()` (SQLite) instead of
    `db_session()` (Neon); `engine` (Neon) is still used, only for
    `inspect(engine)`'s column introspection. Also now calls
    `RagBase.metadata.create_all(rag_engine)` itself at the start of
    `ingest()`, so it can run standalone on a machine that's never started
    the server (and therefore never had `rag_store.db` created yet).
16. `app/graph/state.py` — `GraphState` TypedDict, the shared object every
    LangGraph node reads/writes; only `question` is required, every other
    field is `NotRequired` and filled in as the graph runs.
    **Corrected post-hoc**: `company` moved from required to `NotRequired`
    and a new `company_detection_error` field was added — see lesson 17's
    note.
17. `app/graph/nodes.py` — `retrieve_node()`, `generate_sql_node()`,
    `validate_sql_node()` — the retrieve/generate/validate stages of the
    pipeline, verified end-to-end against real Bedrock + Neon.
    **Corrected post-hoc**: table selection redesigned so the LLM decides
    which table to query, instead of Python resolving one hardcoded
    `allowed_table` string. `generate_sql_node` now shows the LLM the
    company's whole `TABLES` list (via `_format_allowed_tables()`) and asks
    it to pick the matching one; `validate_sql_node` now accepts SQL that
    references *any* table in that list (via `_table_in_sql()`), not just
    one fixed string. `_COMPANY_DATA`/`_get_company_data()` — which company
    names exist at all — is unchanged.
    **Corrected post-hoc, company auto-detection**: added
    `detect_company_node()` — the pipeline's new first stage. Shows the LLM
    every known company (via a new `_format_known_companies()` helper) and
    asks it to pick the one the question is about, or reply `UNKNOWN`. Sets
    `company` in state on a match, `company_detection_error` otherwise —
    never both. `retrieve_node`/`generate_sql_node`/`validate_sql_node` are
    unchanged; they simply never run when detection fails (enforced by
    `graph.py`'s new conditional edge, see lesson 19). Verified for real:
    "tell me the revenue of the futwork for june 2026" (no `company` field
    anywhere in the request) correctly detected `futwork`.
    **Corrected post-hoc, RAG store moved off Neon entirely**:
    `retrieve_node()` now opens a `rag_db_session()` instead of a
    `db_session()` — `retrieve_context()`'s reads come from the new SQLite
    store, not Neon. Nothing else in this file changed for this move.
18. `app/graph/execute_node.py` — `execute_sql_node()` (statement timeout,
    automatic row limit, Decimal/date serialization, defense-in-depth
    validation guard), `format_answer_node()` (LLM narrates results into
    plain English) — full 5-stage pipeline now verified end-to-end
19. `app/graph/graph.py` — `build_graph()` assembles all 5 nodes into a
    compiled `StateGraph`, `_route_after_validation()` conditional edge
    (retry generate on validation failure, capped at `_MAX_RETRIES = 2`),
    module-level `graph` ready for `.invoke()`.
    **Corrected post-hoc, company auto-detection**: added a 6th node,
    `detect_company`, as the new entry point (`START → detect_company`),
    plus `_route_after_detect_company()` — a conditional edge that ends the
    graph immediately if `company_detection_error` is set, otherwise
    proceeds into the unchanged `retrieve → generate → validate → ... →
    format → END` chain. Verified for real: a request with no company field
    correctly ran the whole pipeline after auto-detecting `futwork`; a
    request naming an unrecognized company correctly stopped right after
    `detect_company` with no wasted retrieval/generation work.
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
    **Corrected post-hoc, RAG store moved off Neon entirely**: the
    lifespan hook now runs `RagBase.metadata.create_all(rag_engine)`
    instead of `init_pgvector_extension()` + `Base.metadata.create_all
    (engine)` — both deleted from `db.py`. Verified for real: deleted
    `rag_store.db`, started the server with no file present at all — it
    created the file and all three tables automatically on first boot.
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
    request 0.065s (cache hit). **Added post-build**: `run_query_no_cache()`
    — same shape, reuses `_extract_result()`, but skips every cache step
    entirely (no `cache_get`/`cache_set` at all), for the `/query/no-cache`
    endpoint below.
    **Corrected post-hoc, company auto-detection**: both functions dropped
    `company` — now `run_query(question)`/`run_query_no_cache(question)`.
    `_extract_result()` also returns `company`/`company_detection_error`;
    `_is_cacheable()` now also requires `company_detection_error is None`
    before caching. Cache key is now `question`-only.
    **Corrected post-hoc, Redis removed entirely**: back down to a single
    `run_query(question)` — `graph.invoke()` then `_extract_result()`,
    nothing else. `run_query_no_cache()` deleted (redundant once there's
    no cache to bypass); `_is_cacheable()` deleted; the `app.core.cache`
    import is gone. Verified live: a real `/query` request works correctly
    with no Redis process running at all.
28. `app/api/__init__.py` — empty package marker for the `app.api` package
29. `app/api/schemas.py` — `QueryRequest` (`company`/`question`, required,
    whitespace-stripped, rejected if blank, `question` capped at 500 chars
    via a `field_validator`) and `QueryResponse` (same 5 fields as before) —
    replaces the inline models that used to live in `app/main.py`. Verified
    live over HTTP: a blank question returns a clean `422`, a valid one
    still returns `200` with the correct answer.
    **Corrected post-hoc, company auto-detection**: `QueryRequest` dropped
    `company` — a request is now just `{"question": "..."}`.
    `QueryResponse` gained `company`/`company_detection_error`, both
    optional.
30. `app/api/routes.py` — `APIRouter` with the `POST /query` endpoint;
    wraps `run_query()` in `try`/`except KeyError` to turn an unknown
    company into a clean `404` instead of an unhandled `500`. `app/main.py`
    now mounts this router via `include_router()` instead of defining the
    endpoint itself. All three paths (unknown company, blank question,
    valid question) re-verified live over HTTP. **Added post-build**:
    `POST /query/no-cache` — identical shape and error handling to
    `/query`, calling `run_query_no_cache()` instead of `run_query()`.
    Verified live: two identical requests both took full pipeline latency
    (no cache-hit speedup), and a direct Redis check confirmed no cache
    entry was ever written; unknown-company `404` handling confirmed on
    this endpoint too.
    **Corrected post-hoc, company auto-detection**: both handlers dropped
    `request.company` (calling `run_query(request.question)`/
    `run_query_no_cache(request.question)` instead) and the `try`/`except
    KeyError` wrapper is gone — replaced with a check on
    `result["company_detection_error"]`, raising the same `404` as before
    when set. Verified live: `{"question": "tell me the revenue of the
    futwork for june 2026"}` (no `company` field) returned `200` with
    `company: "futwork"` correctly detected; a question naming an
    unrecognized company returned a clean `404` with the detection-failure
    message.
    **Corrected post-hoc, Redis removed entirely**: `POST /query/no-cache`
    deleted along with its `run_query_no_cache` import — with no cache
    left to bypass, it would've been identical to `/query`, so keeping
    both would just be dead duplication. `app/api/routes.py` is back down
    to the one `POST /query` handler. Verified live: `/query/no-cache` now
    correctly 404s (route no longer exists), `/query` still works.
31. `app/rag/vector_utils.py` — added post-build, when the RAG store moved
    off Neon/pgvector to a local SQLite file: `VectorJSON` (a
    `TypeDecorator` that JSON-encodes/decodes a `list[float]` embedding
    into a `Text` column, standing in for pgvector's `Vector(384)`) and
    `cosine_similarity()` (plain-Python dot-product/norm math, no numpy).
    Used by `schema_store.py`/`example_store.py` to rank candidates in
    Python instead of asking Postgres to order by `embedding <=> :vector`.
32. `ARCHITECTURE.md` — added post-build, at explicit user request: reviews
    a hand-drawn architecture diagram the user made, identifies what it's
    missing (the `detect_company_node` stage entirely, the conditional
    retry-vs-proceed logic, all three external systems — Bedrock/Neon/
    SQLite — the two-pool retrieval + table-selection nuance inside
    `retrieve_node`/`generate_sql_node`, the offline ingestion pipeline,
    the HTTP layer, and the deliberate absence of caching), and provides a
    corrected Mermaid flowchart covering the full request path plus the
    separate offline ingestion path.

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
  lesson 18, plus post-build additions: one endpoint, `POST /query`,
  taking just `{"question": "..."}` (no `company` field — the pipeline
  detects which company the question is about itself, via
  `detect_company_node`) — always runs the real pipeline, no caching —
  validated via `api/schemas.py`, routed via `api/routes.py`, with a
  `lifespan` startup hook that creates the local SQLite RAG store
  (`rag_store.db`) automatically on first boot — no pgvector/Neon
  bootstrap needed anymore for these tables, and no Docker/Redis needed
  to run the app at all anymore
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
    `NEON_BRANCH=RAG` in `.env`) — `DATABASE_URL`. Paste Neon's connection
    string as-is (`postgresql://...` or `postgres://...`); `app/core/db.py`
    rewrites it to `postgresql+psycopg://` automatically since the project
    uses the psycopg (v3) driver, not psycopg2. **Set in `.env` as of
    lesson 6.** Holds only the real financial data table
    (`portfolio.futwork_vs_aop`) now — pgvector is no longer used, and the
    three RAG bookkeeping tables moved to local SQLite (see below).
  - Local SQLite (RAG bookkeeping tables: `schema_chunks`,
    `few_shot_examples`, `company_profiles`) — `RAG_DATABASE_URL`,
    **optional**, defaults to `sqlite:///./rag_store.db`. No credentials,
    no server — the file is created automatically the first time the
    server starts (`app/main.py`'s `lifespan` hook), and by
    `scripts/ingest_knowledge.py` if run before the server ever has been.
    Not committed — covered by `.gitignore` (`*.db`).
  - Optional overrides: `EMBEDDING_MODEL_NAME` (default
    `sentence-transformers/all-MiniLM-L6-v2`, runs locally, no credentials
    needed)
  - **[REMOVED]** Redis (caching) — was `REDIS_URL`, set in `.env` as of
    lesson 6, pointing at a local Redis running in Docker. Deleted
    entirely at explicit user request ("we don't need caching anymore") —
    see Known gaps. Docker is no longer needed to run this app at all.
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
- **[MOOT — cache.py removed]** `cache_set()` (`app/core/cache.py`) JSON-encoded
  whatever it was given; callers had to pass plain JSON-serializable data
  (dicts/lists/strings/numbers), not raw DB row objects or datetimes. No
  longer relevant — `app/core/cache.py` was deleted entirely when Redis
  was removed (see the dedicated entry below).
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
- **[Fixed, lesson 17 — later superseded, see below]** `app/api/schemas.py`'s
  `QueryRequest` validated shape only (non-empty, length-capped), not
  whether `company` is one the pipeline actually knows about — an
  unrecognized company reached `nodes.py`'s `_get_company_data()`, which
  raised a plain `KeyError`. `app/api/routes.py` caught that specific
  exception and returned a clean `404 Unknown company: '...'` instead of an
  unhandled `500`. The previously-noted follow-up gap (catching bare
  `KeyError` is a little broad) is now moot: the company-auto-detection
  redesign below removed `company` from the request entirely, and with it
  the `try`/`except KeyError` — there's no longer a caller-supplied
  `company` value that could be wrong in this call path at all.
- **[Redesigned]** Table selection is now LLM-driven, not hardcoded in
  Python. Previously `generate_sql_node`/`validate_sql_node` computed one
  `allowed_table` string from `company_data.SCHEMA_NAME`/`TABLE_NAME` and
  either dictated it to the LLM or rejected SQL that didn't reference it —
  meaning Python decided the table, and the design silently assumed exactly
  one table per company. Now `data/companies/futwork.py` exposes `TABLES`
  (a list of `{schema, table, description}` dicts), `generate_sql_node`
  shows the LLM that whole list and asks it to pick the one that matches
  the question, and `validate_sql_node` accepts SQL referencing *any*
  entry in the list. This means a company with multiple tables just needs
  more `TABLES` entries — no code change. **What's still hardcoded**: which
  *companies* exist at all is still the `_COMPANY_DATA = {"futwork":
  futwork}` dict in `nodes.py` — adding a second company still means adding
  a line to that dict (and a new `data/companies/<company>.py` module with
  its own `TABLES`). That's the same normalization gap noted above (`company`
  as a plain string, not a proper registry/FK) — not fixed by this change,
  just no longer conflated with table selection. Verified locally first
  (`_get_company_data()`, `_format_allowed_tables()`, and `_table_in_sql()`
  all behave correctly in isolation — correct SQL matches, SQL against an
  unrelated table doesn't, unknown company still raises `KeyError`), then
  **verified for real** end-to-end via `POST /query/no-cache` against live
  Bedrock + Neon: "What was the total revenue in March 2026?" → the LLM,
  shown the new `TABLES` list instead of one dictated table string, picked
  `portfolio.futwork_vs_aop` itself and generated valid SQL against it on
  the first try (`validation_error: null`, no retry needed), with the
  correct answer ("INR 22,063,632").
- **[Redesigned]** `company` is no longer a request field — the pipeline
  detects it from `question` itself, via a new `detect_company_node`
  (first stage of the graph) that shows the LLM every entry in
  `_COMPANY_DATA` (name + a one-line business summary) and asks it to pick
  the matching one, or reply `UNKNOWN`. This means every `/query` request
  now costs **two** LLM calls on a cache miss instead of one (detect, then
  generate) — a real latency/cost tradeoff for the convenience of not
  having to pass `company` explicitly; worth watching if per-request cost
  ever matters. **What's still hardcoded**: exactly the same thing as the
  table-selection redesign above — which companies exist at all is still
  `_COMPANY_DATA` in `nodes.py`, and `detect_company_node`'s prompt is only
  as good as each company's `PROFILE`'s first sentence (used as the
  one-line summary shown to the LLM) at distinguishing it from every other
  company; this hasn't been stress-tested with more than one real company
  yet. **Also open**: a question that's ambiguous or names no company at
  all correctly falls back to `UNKNOWN`/`404` rather than guessing — this
  is deliberate (wrong-company silent misrouting would be worse than a
  clear rejection) but means a genuinely company-agnostic question (if one
  ever makes sense in this system) has no path to succeed today. Verified
  for real against live Bedrock + Neon: correct detection from a question
  naming the company in passing ("tell me the revenue of the futwork for
  june 2026"), and a clean `404` for a question naming an unrecognized
  company.
- **[Redesigned]** The three RAG bookkeeping tables (`schema_chunks`,
  `few_shot_examples`, `company_profiles`) moved off Neon/pgvector to a
  local SQLite file (`rag_store.db`), at explicit user request. Real
  tradeoffs worth tracking, not just upsides: (1) **not backed up or
  shared** — it's a plain file on whichever machine runs the app; a fresh
  clone or a new container has to re-run `scripts/ingest_knowledge.py`
  from scratch (fine today since that script is idempotent and fast, but
  worth remembering if this ever runs somewhere ephemeral/stateless, like
  a container that gets rebuilt often — the RAG knowledge would vanish
  with it unless the file is persisted separately); (2) **similarity
  search is now O(n) pure-Python** (fetch every candidate row for a
  company, rank by `cosine_similarity()` in-process) instead of an
  indexed pgvector `ORDER BY` — completely fine at 177 rows for one
  company, would need revisiting (a real vector index, or moving back to
  a vector-capable store) if that grew by a couple of orders of magnitude;
  (3) **SQLite's single-writer model** — fine for this app's actual write
  pattern (occasional re-ingestion, not concurrent request-time writes),
  but worth remembering if that ever changes; (4) the **old Neon `rag`
  schema tables were left in place**, now orphaned/unused — not dropped
  automatically, since that's a destructive Neon change outside the scope
  of what was asked; worth cleaning up manually if desired. Verified for
  real: deleted `rag_store.db`, started the server with no file
  present — it created the file and all three tables itself — then ran
  `ingest_knowledge.py` (177 chunks + 5 examples, matching the old
  Neon-era counts exactly) and confirmed a live `/query/no-cache` request
  still retrieved correct context and answered correctly.
  **Hit for real, not just theoretical**: in a later session, `rag_store.db`
  existed but was empty (0 rows) — the server booted fine (`create_all()`
  doesn't care if a table is empty) and `/query` returned `200`, but with
  `sql_result: null` and a real execution error: the LLM, given zero
  retrieved schema context, guessed a plausible-sounding but nonexistent
  column name (`revenue` instead of the real `total_revenue`) and Postgres
  rejected it (`UndefinedColumn`). This is exactly tradeoff (1) above,
  observed in practice rather than just predicted: unlike the old Neon
  setup, nothing here persists the ingested knowledge anywhere shared, so
  every fresh environment (new session, new clone, a deleted/reset file)
  silently starts with an empty RAG store until `python -m scripts.
  ingest_knowledge` is run again — there's no error at server-start time
  to flag it, only a downgraded, retrieval-less answer at query time. Fixed
  by re-running the ingestion script; re-verified the same question then
  correctly generated `SELECT total_revenue FROM portfolio.futwork_vs_aop
  ...` and returned the right number. Worth checking row counts first
  whenever a query returns a suspiciously generic/wrong-looking SQL.
- **[Redesigned]** Redis and all caching removed entirely, at explicit
  user request. **Real tradeoff, not a pure win**: every `/query` request
  now runs the full pipeline every time — two LLM calls (detect company,
  generate SQL) plus a live Neon execution, with no shortcut for a
  repeated or near-identical question. Before this, an identical repeat
  question was a ~0.065s cache hit; now it's full latency (many seconds)
  every time. This is the deliberate tradeoff the user asked for (`"we
  don't need caching anymore"`), not an oversight — worth revisiting if
  latency/cost on repeated questions becomes a real problem again, at
  which point `app/core/cache.py` (and the cache-aside pattern in
  `query_service.py`, both now deleted) would need to be rebuilt rather
  than un-deleted, since they're gone from the codebase, not just
  disabled. One upside beyond "the user asked for it": the app no longer
  needs Docker/Redis running at all to work — one less moving part for
  local dev and onboarding (see `README.md`'s simplified setup steps).
  Verified for real: restarted the server with Docker not running,
  confirmed clean startup and a correct `/query` response; confirmed
  `POST /query/no-cache` now correctly 404s since the route was removed
  (it would've been identical to `/query` with no cache to bypass).

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
