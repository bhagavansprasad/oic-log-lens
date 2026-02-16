**Step 1 — DB Init Script**
**Step 2 — Config & Connection Pool**
**Step 3 — SemanticTextBuilder**
**Step 4 — EmbeddingService (Gemini)**
**Step 5 — OracleSemanticRepository**
**Step 6 — Tests for each component**
**Step 7 — .env template + requirements + package init files**

### What was built

| File | What it does |
|------|-------------|
| `db/init_schema.sql` | Run once against your Docker Oracle — creates table + HNSW vector index + metadata indexes |
| `config/settings.py` | Loads all config from `.env` — Oracle DSN, Gemini key, pool sizes, similarity thresholds |
| `db/connection.py` | Oracle connection pool with `acquire()` context manager — auto commit/rollback |
| `services/semantic_text_builder.py` | Pure logic — alias resolution, excluded field enforcement, canonical text format |
| `services/embedding_service.py` | Gemini `gemini-embedding-001` wrapper — single + batch, dim validation |
| `services/oracle_semantic_repository.py` | `merge_content()`, `semantic_search()`, `get_store_stats()` against Oracle |
| `.env.template` | Copy → `.env`, fill your Oracle DSN + Gemini key |

---
