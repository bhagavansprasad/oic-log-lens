# OIC-LogLens - Current Project State

**Date:** 2026-02-19  
**Status:** Phase 6 Complete + Performance Optimization In Progress

---

## ✅ Completed Features

### Core System (Phases 1-6)
- ✅ Log Normalization (Gemini 2.0 Flash)
- ✅ Embedding Generation (gemini-embedding-001, 3072 dims)
- ✅ Vector Database (Oracle 26ai with HNSW index)
- ✅ Duplicate Detection (LOG_HASH before LLM)
- ✅ REST API (6 endpoints: health, 4x ingest, search)
- ✅ Batch Database Ingestion
- ✅ LLM Re-ranking with Structured Output (100% confidence for exact duplicates)
- ✅ Streamlit Web UI with file upload
- ✅ Performance Optimization (connection pooling + caching)

---

## 🏗️ Architecture

```
User → Streamlit UI (8501) → FastAPI (8000) → Oracle 26ai (1521)
                                ↓
                            Gemini API
                         (Normalize + Embed + Rerank)
```

---

## 📁 Key Files

### Core Backend
- `main.py` - FastAPI app with 6 endpoints + cache stats
- `config.py` - Configuration and Gemini client
- `db.py` - Oracle 26ai operations with connection pooling
- `cache.py` - TTL cache with LRU eviction
- `normalizer.py` - Gemini normalization
- `embedder.py` - Embedding generation
- `ingestion_service.py` - 4 ingestion loaders
- `search_service.py` - Search pipeline with LLM re-ranking
- `models.py` - Pydantic request/response models
- `prompts.py` - LLM prompts with structured output schema

### Frontend
- `app.py` - Streamlit UI with 3 pages

### Database
- `oll_schema.sql` - Database schema
- Table: `OLL_LOGS` (may rename to `OIC_ISSUE_KNOWLEDGE_BASE`)

### Documentation
- `README.md` - Complete project overview with Quick Start
- `TESTING.md` - Testing guide
- `UI-README.md` - UI usage guide

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/ingest/file` | Ingest from file path |
| POST | `/ingest/url` | Ingest from URL |
| POST | `/ingest/raw` | Ingest raw JSON |
| POST | `/ingest/database` | Batch ingest from DB |
| POST | `/search` | Semantic search with LLM re-ranking |
| GET | `/stats/cache` | Cache statistics |
| POST | `/admin/clear-cache` | Clear all caches |

---

## 🚀 Quick Start Commands

```bash
# 1. Start database
docker start oracle26ai_db_bhagavan

# 2. Start API (Terminal 1)
cd ~/aura/oci-log-lens/src
python main.py

# 3. Start UI (Terminal 2)
streamlit run app.py
```

**Access:**
- UI: http://localhost:8501
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

---

## 💾 Database

**Connection:**
```bash
docker exec -it oracle26ai_db_bhagavan sqlplus EA_APP/jnjnuh@FREEPDB1
```

**Schema:** `OLL_LOGS`
- LOG_ID (PK)
- LOG_HASH (unique)
- JIRA_ID
- FLOW_CODE, TRIGGER_TYPE, ERROR_CODE, ERROR_SUMMARY
- RAW_JSON, NORMALIZED_JSON
- VECTOR (3072 dims, HNSW index)
- CREATED_AT, UPDATED_AT

---

## 🎯 Performance Optimization (Just Added)

### What Was Implemented
1. **Connection Pooling** (db.py)
   - Min: 2, Max: 10 connections
   - Reuses connections (~100ms saved)

2. **TTL Cache** (cache.py)
   - normalized_cache: 500 items, 1 hour
   - embedding_cache: 500 items, 1 hour
   - search_cache: 200 items, 30 mins

3. **Cache Integration** (search_service.py)
   - Checks cache before LLM calls
   - Stores results after generation

### Expected Performance
- First search: ~12 seconds
- Cached search: ~50ms (240x faster!)
- Cache hit rate visible at: GET /stats/cache

---

## ⚠️ Current Issue

**Problem:** Search returning 0 results after adding performance optimization

**Debug Steps:**
```bash
# 1. Check if database has data
docker exec oracle26ai_db_bhagavan sqlplus -s EA_APP/jnjnuh@FREEPDB1 << EOF
SELECT COUNT(*) FROM OLL_LOGS;
EXIT;
EOF

# 2. If empty, ingest test data
curl -X POST http://localhost:8000/ingest/file \
  -H "Content-Type: application/json" \
  -d '{"file_path": "flow-logs/01_flow-log.json"}'

# 3. Check API logs for errors
# Look at terminal where "python main.py" is running

# 4. Test search
python test.py
```

**Possible Causes:**
- Empty database
- Connection pool not initialized properly
- Cache key mismatch
- Search query issue

---

## 📊 Git Status

**Current Branch:** refactor/cleanup-debug-logging  
**Recent Commits:**
- LLM re-ranking with structured output
- Cleanup debug logging
- Performance optimization (connection pooling + caching)

**Pending:** Debug search issue, commit performance optimization

---

## 🔮 Next Steps

1. **Immediate:** Fix search returning 0 results
2. **Short-term:** 
   - Test cache performance (first vs second search)
   - Verify connection pooling works
   - Commit performance optimization
3. **Medium-term:**
   - Docker deployment
   - PII masking
   - Table renaming (OLL_LOGS → OIC_ISSUE_KNOWLEDGE_BASE)

---

## 📝 Important Notes

- LLM re-ranking shows 100% confidence for exact duplicates (same flow + error + root cause)
- Classification types: EXACT_DUPLICATE, SIMILAR_ROOT_CAUSE, RELATED, NOT_RELATED
- Full normalized log context (including root_cause) used in re-ranking
- Streamlit deprecation warnings fixed (use_container_width → width)
- All debug logging cleaned up

---

## 🔑 Connection Details

**Database:** `EA_APP/jnjnuh@localhost:1521/FREEPDB1`  
**API:** `http://localhost:8000`  
**UI:** `http://localhost:8501`  

---

**Last Updated:** 2026-02-19 23:30 IST
