# 🚀 AIOps Semantic Error Intelligence — Architecture

---

## 1️⃣ 🎯 Objective

Build a platform that:

1. Ingests historical & live logs
2. Converts meaningful error context → embeddings
3. Stores in Oracle 26ai
4. On new error:

   * finds similar past issues
   * returns similarity score
   * enables auto-correlation / dedup / RCA

---

## 2️⃣ 🧠 Core Design Principles

### ✔ Only embed semantic signal — not raw JSON

We embed a **curated semantic text**, not the full log.

Why:

* stable similarity
* smaller vectors
* faster ANN search
* higher match accuracy

---

### ✔ Structured metadata stays relational

Used for:

* filtering
* analytics
* hybrid search
* dashboards

---

### ✔ One semantic store per domain (Approach A)

Example:

```
SS_ERROR_LOGS
```

---

## 3️⃣ 🗄️ Oracle Table Design

### 🔹 Table: SS_ERROR_LOGS

```sql
CREATE TABLE SS_ERROR_LOGS (
    LOG_ID            VARCHAR2(100) PRIMARY KEY,

    EVENT_TIME        TIMESTAMP,
    FLOW_CODE         VARCHAR2(200),
    ACTION_NAME       VARCHAR2(200),
    ENDPOINT_NAME     VARCHAR2(200),
    ERROR_LEVEL       VARCHAR2(50),
    ERROR_CODE        VARCHAR2(100),

    SEMANTIC_TEXT     CLOB,     -- text used for embedding
    RAW_JSON          CLOB,     -- full original log

    ATTRIBUTES        JSON,     -- dynamic metadata

    VECTOR            VECTOR(3072, FLOAT32)
);
```

---

### 🔹 Vector Index

```sql
CREATE VECTOR INDEX SS_ERROR_LOGS_VIDX
ON SS_ERROR_LOGS(VECTOR)
ORGANIZATION INMEMORY GRAPH
DISTANCE COSINE;
```

---

## 4️⃣ 🧬 What Goes Into the Embedding

Generated **semantic_text**:

```
flow: ALTERA_CREATE_SO_INTEGRAT
step: createSORest1
error: HTTP 500 BuyingPartyId not found
business_key: 100037
```

### Sources for this:

✅ integration error message
✅ fault text
✅ failed step
✅ business identifier involved

---

## 5️⃣ ⚙️ System Components

```
                ┌────────────────────┐
                │  Log Sources       │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │  Ingestion API     │
                │  (FastAPI)         │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │  Semantic Builder  │
                │  (JSON → text)     │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Embedding Service  │
                │ (Gemini / local)   │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Oracle 26ai        │
                │ Vector Store       │
                └────────────────────┘
```

---

### 🔎 Query Path

```
New error
   ↓
Semantic builder
   ↓
Embedding
   ↓
Vector similarity search
   ↓
Top matches + similarity %
```

---

# 6️⃣ 🔌 FASTAPI Design

---

## 🟢 API 1 — Bulk Log Ingestion

### Endpoint

```
POST /logs/ingest
```

### Input

```json
[
  { log json 1 },
  { log json 2 }
]
```

### Flow

```
parse → build semantic text → embed → MERGE into Oracle
```

### Output

```json
{
  "processed": 120,
  "stored": 118,
  "failed": 2
}
```

---

## 🟢 API 2 — Semantic Error Match

### Endpoint

```
POST /logs/match
```

### Supported inputs

#### Option A — raw error text

```json
{
  "error_text": "BuyingPartyId not found"
}
```

#### Option B — JSON log

```json
{
  "log": { ... }
}
```

#### Option C — file upload

```
multipart/form-data
```

---

### Output

```json
{
  "known": true,
  "top_match": {
    "log_id": "LOG_4567",
    "similarity": 0.92,
    "error": "BuyingPartyId not found",
    "flow": "ALTERA_CREATE_SO_INTEGRAT"
  },
  "alternatives": [...]
}
```

---

# 7️⃣ 🧠 Similarity Decision Logic

Example:

| Similarity | Meaning |
| ---------- | ------- |

> 0.90 | same incident |
> 0.75 – 0.90 | same error class |
> < 0.75 | new issue |

---

# 8️⃣ 🧩 Application Services

We will implement:

### 🔹 SemanticTextBuilder

```python
build_semantic_text(log_json)
```

---

### 🔹 EmbeddingService

```python
generate_vector(text)
```

---

### 🔹 OracleSemanticRepository

```python
store_log()
search_similar()
```

---

### 🔹 AIOpsService

```python
ingest_logs()
match_error()
```

---

# 9️⃣ 🔐 Non-Functional Requirements

### Performance

* ANN vector index
* batch ingestion
* connection pooling

### Accuracy

* curated embedding text
* hybrid filtering (flow_code, severity)

### Scalability

* partition by date (future)
* multi-store for domains

### Observability

* ingestion metrics
* match latency
* embedding latency

---

# 🔟 Future Enhancements

* RCA suggestion (RAG from resolution KB)
* auto-incident linking
* agent-triggered remediation
* anomaly clustering
* drift detection

---

# 🏁 ✅ YES — I understood your requirement

You are building:

> A real semantic AIOps error intelligence platform with Oracle Vector DB + FastAPI.

And the architecture above is aligned to that.

---

# 🚀 Next Step (Implementation Phase)

If you say:

```
Start implementation
```

I will generate:

### Phase 1 code:

* FastAPI app skeleton
* Pydantic models
* ingestion endpoint
* match endpoint
* service wiring

all compatible with your existing Oracle semantic store.

This will be your **first runnable AIOps semantic backend**.
