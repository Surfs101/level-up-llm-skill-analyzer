# Phase 2 — Course corpus + RAG retrieval

What Phase 2 added: a queryable course corpus and the retrieval/ranking that turns a
skill gap into two recommended courses.

- **DB foundation** — `courses`, `course_skills`, `course_embeddings` (+ pgvector
  extension and an HNSW cosine index), first Alembic migration.
- **DeepLearning.AI corpus** — a saved-HTML parser (the live site is behind a
  Cloudflare managed challenge) + a loader. **One source this phase: DeepLearning.AI
  only.**
- **Course → skill mapping** — `gpt-4o-mini`, precision-tuned, every id validated
  against the taxonomy. `course_skills` holds only canonical taxonomy slugs — the
  same ids the matcher produces, so retrieval is symmetric.
- **Embeddings** — `text-embedding-3-small` (1536-d) into `course_embeddings`,
  **embedded once** (no refresh cron this phase).
- **RAG** — `app/rag/retriever.py` (gap → embed → pgvector cosine top-50) and
  `app/rag/ranker.py` (priority-weighted coverage → Course A / Course B).

## Offline pipeline (rebuild the corpus)

`scrapers/` is offline-only: **`app/` never imports it** (the reverse is fine — the
loader/seeders import `app.*`). Raw data (`scrapers/input/`, `scrapers/output/`) is
gitignored; only the code is committed.

```bash
docker compose up -d                              # Postgres (pgvector) + Redis
uv run alembic upgrade head                       # schema + pgvector + HNSW
# (human) save the rendered courses page into scrapers/input/*.html
uv run python scrapers/deeplearning_ai.py         # parse saved HTML -> output JSON
uv run python scrapers/load_courses.py            # JSON -> courses (upsert)
uv run python scripts/map_course_skills.py        # courses -> course_skills (LLM, validated)
uv run python scripts/embed_courses.py            # courses -> course_embeddings
```

All four seeders are idempotent: the loader upserts, the mapper maps only courses
lacking skills (or `--course-id` to redo), the embedder embeds only courses lacking
a vector (`--refresh` to redo all).

## Corpus snapshot

- **112 courses** (`platform=deeplearning_ai`), every one with title + description and
  a `level`; `duration_hours` is NULL for all (absent from the listing).
- **231 `course_skills` rows**, **57 distinct taxonomy ids**, avg **2.06** skills/course,
  **7** courses with no skills (genuinely non-technical or too niche).
- **112 `course_embeddings`** — including the 7 skill-less courses (empty skill set ≠
  empty text; they stay retrievable).
- **Coverage is GenAI/LLM-weighted** (top ids: `large-language-models`,
  `generative-ai`, `machine-learning`, `agentic-ai`, `rag`, `vector-search`). The
  corpus serves AI/LLM gaps well and is thin for non-AI gaps — expected for this
  source.

## Retrieve → rank → select (`app/rag/`)

1. **Retrieve** — build a query from the missing skills' display names, embed it with
   the same model the corpus used, pull the cosine-nearest 50 courses over the HNSW
   index, each carrying its mapped skill set.
2. **Rank** — score each candidate by priority-weighted coverage of the gap
   (`weight = {1:4, 2:3, 3:2, 4:1}` by `priority_rank`); drop courses that cover
   nothing.
3. **Select** — Course A = highest, Course B = second. Tie-break: more skills covered,
   then shorter duration, then `external_id` (so the same gap always yields the same
   two courses).

## Ranking limitations on the current corpus

Honest assessment of how ranking behaves on *this* corpus (the framework is correct;
the corpus is what limits it):

- The corpus is **almost entirely rank-3/rank-4 skills** (techniques/libraries), so
  the priority weighting `{1:4,2:3,3:2,4:1}` **rarely differentiates** — most gaps
  produce ties.
- **`duration_hours` is NULL for all 112 courses** (not in the DeepLearning.AI
  listing), so the "shorter course wins" tie-break is currently **inert**.
- **Net:** among equally-relevant courses, final A/B selection falls to `external_id`
  (alphabetical) — **deterministic but not quality-ranked**. Acceptable for a v1 /
  narrow corpus.
- **Mitigation path (future, not now):** add a real ranking signal — course
  rating / enrollment / recency, or recover `duration_hours` from course detail
  pages — which the existing weight + tie-break framework will use without redesign.
  Coursera/Udemy would also add rank-1/2 (language/framework) courses that make the
  priority weighting actually fire.
