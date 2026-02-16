# 🧠 AIOps Semantic Error Intelligence Platform

## Architecture & Implementation Context — v1

---

## 1️⃣ 🎯 Goal

Build an **AIOps semantic error intelligence system** that:

* Ingests historical and live log data (JSON)
* Extracts meaningful error context
* Generates embeddings using **Gemini (3072-dim)**
* Stores in **Oracle AI Database 26ai Vector DB**
* Performs real-time semantic similarity matching for new errors
* Exposes ingestion & search capabilities via **FastAPI**

---

## 2️⃣ ✅ Current Implementation Status

### ✔ Already Implemented

* Oracle AI Database 26ai running in Docker
* Vector-enabled table
* HNSW vector index (INMEMORY GRAPH)
* Python semantic store service
* MERGE-based upsert
* Gemini embedding integration
* Working semantic search with similarity score
* Multi-store dynamic table resolution pattern

### 🔜 To Be Implemented

* FastAPI application layer
* JSON → semantic text builder
* Bulk log ingestion API
* Real-time error match API
* File upload support
* Similarity decision logic

---

## 3️⃣ 🧰 Fixed Technology Stack (Non-Negotiable)

| Layer           | Technology                           |
| --------------- | ------------------------------------ |
| Database        | Oracle AI Database 26ai              |
| Vector index    | HNSW (INMEMORY GRAPH)                |
| Embedding model | Gemini `gemini-embedding-001` (3072) |
| Backend         | Python                               |
| API layer       | FastAPI                              |
| Driver          | python-oracledb thin mode            |
| Deployment mode | Docker (local for now)               |

⚠️ Do **NOT** replace with Pinecone / Chroma / FAISS.

---

## 4️⃣ 🧱 Core Design Principles

### 4.1 Embedding Policy (Critical Rule)

We **DO NOT embed raw JSON**.

We embed only **curated semantic error context**.

#### ✅ Included in embedding text

* Error / fault message
* Failed step / action
* Business identifier involved in failure
* Integration / flow name (optional if meaningful)

#### ❌ NEVER embedded

* eventId
* timestamps
* OCIDs
* payload size
* instance IDs
* connection IDs

These are stored as structured metadata.

---

### 4.2 Hybrid Storage Model

| Data type                       | Storage                   |
| ------------------------------- | ------------------------- |
| Semantic meaning                | VECTOR                    |
| Curated text used for embedding | CLOB                      |
| Full original log               | CLOB                      |
| Filterable metadata             | JSON + relational columns |

---

### 4.3 Store Strategy

One semantic store per domain:

Example:

```
SS_ERROR_LOGS
```

Dynamic resolution pattern already implemented in Python service.

---

## 5️⃣ 🗄️ Oracle Table Schema

```sql
CREATE TABLE SS_ERROR_LOGS (

    LOG_ID            VARCHAR2(100) PRIMARY KEY,

    EVENT_TIME        TIMESTAMP,
    FLOW_CODE         VARCHAR2(200),
    ACTION_NAME       VARCHAR2(200),
    ENDPOINT_NAME     VARCHAR2(200),
    ERROR_LEVEL       VARCHAR2(50),
    ERROR_CODE        VARCHAR2(100),

    SEMANTIC_TEXT     CLOB,
    RAW_JSON          CLOB,
    ATTRIBUTES        JSON,

    VECTOR            VECTOR(3072, FLOAT32)
);
```

### Vector Index

```sql
CREATE VECTOR INDEX SS_ERROR_LOGS_VIDX
ON SS_ERROR_LOGS(VECTOR)
ORGANIZATION INMEMORY GRAPH
DISTANCE COSINE;
```

---

## 6️⃣ 🧬 Semantic Text Construction

Generated per log using:

```
flow: <FLOW_CODE>
step: <ACTION_NAME>
error: <ERROR_MESSAGE>
business_key: <IMPORTANT_IDENTIFIER>
```

This is the **exact text used for embedding**.

---

## 7️⃣ 🔎 Similarity Interpretation Policy

| Similarity | Meaning |
| ---------- | ------- |

> 0.90 | Known incident |
> 0.75 – 0.90 | Related issue |
> < 0.75 | New issue |

This logic will be implemented in the service layer.

---

## 8️⃣ ⚙️ System Logical Architecture

### Ingestion Flow

```
JSON logs
   ↓
Semantic Text Builder
   ↓
Gemini Embedding
   ↓
Oracle MERGE (vector + metadata)
```

### Match Flow

```
New error
   ↓
Semantic Text Builder
   ↓
Embedding
   ↓
Vector similarity search
   ↓
Top matches + similarity score
```

---

## 9️⃣ 🧩 Application Services

### SemanticTextBuilder

```
build_semantic_text(log_json) → str
```

---

### EmbeddingService

```
generate_vector(text) → 3072-dim vector
```

---

### OracleSemanticRepository

Already exists conceptually:

* merge_content()
* semantic_search()
* get_store_stats()

---

### AIOpsService

To be implemented:

* ingest_logs()
* match_error()

---

## 🔟 🔌 FASTAPI API Contracts

---

### 🟢 API 1 — Bulk Log Ingestion

#### Endpoint

```
POST /logs/ingest
```

#### Input

```json
[
  { log object },
  { log object }
]
```

#### Processing

* extract semantic text
* generate embedding
* MERGE into Oracle

#### Response

```json
{
  "processed": int,
  "stored": int,
  "failed": int
}
```

---

### 🟢 API 2 — Semantic Match

#### Endpoint

```
POST /logs/match
```

#### Supported Inputs

##### Option A — raw error text

```json
{
  "error_text": "string"
}
```

##### Option B — JSON log

```json
{
  "log": {}
}
```

##### Option C — file upload

multipart/form-data

---

#### Response

```json
{
  "known": true,
  "similarity": 0.92,
  "top_match": {
    "log_id": "LOG_123",
    "error": "...",
    "flow_code": "...",
    "first_seen": "timestamp"
  },
  "alternatives": []
}
```

---

## 1️⃣1️⃣ Non-Functional Requirements

### Performance

* ANN vector search
* batch ingestion
* DB connection pooling

### Scalability (future)

* partition by date
* multi-domain stores

### Observability

* ingestion latency
* embedding latency
* match latency

---

## 1️⃣2️⃣ Future Roadmap

* RCA retrieval via RAG
* Auto-incident linking
* Agent-triggered remediation
* Error clustering
* Drift detection

---

# 🏁 End of Context

---

# ✅ How to Use in New Chat

Paste this and say:

```
Use this as system context.
Start implementing the FastAPI ingestion and match APIs.
```

