# OIC-LogLens 🔍

**AI-Powered Error Resolution Engine for Oracle Integration Cloud**

Transform OIC troubleshooting from reactive debugging to AI-driven resolution intelligence. OIC-LogLens automatically detects duplicate errors, suggests solutions from past incidents, and eliminates repeated manual investigations.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)](https://streamlit.io/)

---

## 📋 Table of Contents

- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Web UI](#web-ui)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Problem Statement

In complex Oracle Integration Cloud (OIC) environments, teams face recurring challenges:

### Repeated Errors Across Integrations
- Similar payload failures
- XSLT transformation errors
- API invocation issues (400/500)
- ESS job failures
- FBDI load errors
- Connectivity/authentication issues

### Manual Investigation Process
Teams often:
- ✗ Manually review logs
- ✗ Search old Jira tickets
- ✗ Ask senior developers
- ✗ Reinvestigate already-solved issues

### Impact
- ⏰ Wasted effort on duplicate investigations
- 🐌 Slow resolution times
- 👤 Dependency on SMEs
- ⬇️ Increased downtime and MTTR



### Log Data Characteristics

**Important Constraints:**
- Each log file represents a **single workflow execution**
- Each error log file results in **one record** in the database
- Log files are always provided in **valid JSON format**
- Each log file contains a **list of JSON objects**
- The structure of JSON objects is **not uniform** and may vary between log files (different keys and nesting)

**Implication:**  
Because the log structure is not fixed, the system must **normalize** the incoming log into a consistent schema before:
- Storing it in the database
- Generating embeddings
- Performing semantic search

---

## ✅ Solution

OIC-LogLens transforms troubleshooting with AI-powered semantic search:

### How It Works

```
New Error Occurs → Submit to OIC-LogLens → Get Similar Past Issues → Resolve in Minutes
```

**Instead of:**
- 30 min: Manual log review
- 20 min: Searching Jira tickets
- 45 min: Waiting for SME response
- **Total: ~2 hours MTTR**

**You Get:**
- 1 min: Submit log
- Instant: Get similar issues with Jira IDs
- 5 min: Apply known solution
- **Total: ~6 minutes MTTR** ⚡

---

## 🏗️ Architecture

### System Overview

```
┌─────────────┐
│   User      │
│ (OIC Admin) │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│         FastAPI REST API                │
│  ┌─────────────────────────────────┐   │
│  │  /ingest/file  /ingest/url      │   │
│  │  /ingest/raw   /ingest/database │   │
│  │  /search                         │   │
│  └─────────────────────────────────┘   │
└──────┬──────────────────────┬───────────┘
       │                      │
       ▼                      ▼
┌──────────────┐      ┌──────────────┐
│  Gemini AI   │      │ Oracle 26ai  │
│              │      │ Vector DB    │
│ • 2.0 Flash  │      │              │
│ • Embeddings │      │ OLL_LOGS     │
│   (3072 dim) │      │ • HNSW Index │
└──────────────┘      └──────────────┘
```

### Data Flow

**Use Case 1: Ingestion (Write Path)**
```
Raw Log → Normalize (LLM) → Generate Embedding → Store in Vector DB
```

**Use Case 2: Search (Read Path)**
```
New Log → Normalize (LLM) → Generate Embedding → Vector Similarity Search → Return Top-5 Matches
```

### RAG Architecture

OIC-LogLens implements **Retrieval Augmented Generation (RAG)**:
- **Retrieve:** Vector similarity search finds Top-5 similar logs
- **Augment:** Retrieved context (Jira IDs, error summaries)
- **Generate:** Present ranked results to user



### Storage Model

For each processed log, the system stores in **Oracle 26ai VectorDB**:

1. **Original Log** — Raw log file in native JSON format for traceability and reprocessing
2. **Normalized Log** — Structured and consistent representation generated after normalization
3. **Vector Embeddings** — Embeddings from selected critical fields of the normalized log
4. **Metadata** — LOG_HASH (SHA256), JIRA_ID, flow_code, error_code, timestamps

**Purpose:** This enables efficient semantic matching while preserving original data for audit and reprocessing.

---

## ✨ Features

### 🔐 Duplicate Detection
- **LOG_HASH check before LLM calls** — saves 10-15 seconds per duplicate
- Instant 409 Conflict response for duplicates
- SHA256 hash ensures uniqueness

### 📥 Multiple Ingestion Methods
1. **File Upload** — Browse and upload JSON files
2. **URL** — Fetch from HTTP/HTTPS (GCS, S3, GitHub)
3. **Raw Text** — Copy-paste JSON directly
4. **Database Query** — Load from Oracle/other DB (supports batch)

### 🔍 Semantic Search
- **Vector similarity** using cosine distance
- **Top-5 ranked results** with similarity scores
- **Jira ID linking** — instant access to past resolutions
- **Metadata filtering** — flow code, error code, trigger type

### 🤖 AI-Powered Normalization
- **LLM-based** log normalization (Gemini 2.0 Flash)
- Handles structural variability across OIC log formats
- Extracts: flow info, error details, tracking variables, user data

### 📊 Batch Processing
- Ingest multiple logs in one database query
- Summary with success/duplicate/failed counts
- Individual result tracking

### 🎨 Beautiful Web UI
- **Streamlit interface** — no coding required
- File upload with preview
- Real-time API status
- Color-coded results
- Expandable search results

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Backend** | FastAPI | REST API server |
| **UI** | Streamlit | Web interface |
| **LLM** | Gemini 2.0 Flash | Log normalization |
| **Embeddings** | gemini-embedding-001 | 3072-dim vectors |
| **Vector DB** | Oracle 26ai | Vector storage + search |
| **Vector Index** | HNSW | 95% accuracy, cosine distance |
| **Language** | Python 3.8+ | Core implementation |
| **API Docs** | Swagger/OpenAPI | Auto-generated docs |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.8+
python --version

# Oracle 26ai Database
docker ps | grep oracle

# Gemini API Key
export GOOGLE_API_KEY="your-api-key"
```

### Install

```bash
# Clone repository
git clone https://github.com/bhagavansprasad/oic-log-lens.git
cd oic-log-lens/src

# Install dependencies
pip install fastapi uvicorn oracledb google-generativeai streamlit requests --break-system-packages
```

### Run

```bash
# Terminal 1: Start API
python main.py
# API runs at http://localhost:8000

# Terminal 2: Start UI (optional)
streamlit run app.py
# UI runs at http://localhost:8501
```

### Test

```bash
# Health check
curl http://localhost:8000/health

# Ingest a log
curl -X POST http://localhost:8000/ingest/file \
  -H "Content-Type: application/json" \
  -d '{"file_path": "flow-logs/01_flow-log.json"}'

# Search for similar logs (using Python)
python tests/test_search_api.py
```

---

## 📦 Installation

### 1. System Requirements

- **Python:** 3.8 or higher
- **Database:** Oracle 26ai (Docker recommended)
- **Memory:** 4GB RAM minimum
- **Storage:** 2GB for models and data

### 2. Database Setup

```bash
# Pull Oracle 26ai Docker image
docker pull container-registry.oracle.com/database/free:latest

# Run Oracle 26ai
docker run -d \
  --name oracle26ai_db \
  -p 1521:1521 \
  -e ORACLE_PWD=YourPassword123 \
  container-registry.oracle.com/database/free:latest

# Create schema
cd OIC-LogLens/src
docker cp oll_schema.sql oracle26ai_db:/tmp/
docker exec -it oracle26ai_db sqlplus EA_APP/YourPassword@FREEPDB1 @/tmp/oll_schema.sql
```



### Database Connection

```bash
# Connect to Oracle 26ai via Docker
docker exec -it oracle26ai_db_bhagavan sqlplus EA_APP/jnjnuh@FREEPDB1

# Useful commands
SHOW USER;
SELECT table_name FROM user_tables;
SELECT * FROM OLL_LOGS;
SELECT COUNT(*) FROM OLL_LOGS;
TRUNCATE TABLE OLL_LOGS;

# Copy SQL file to container
docker cp oll_schema.sql oracle26ai_db_bhagavan:/tmp/oll_schema.sql
docker exec -it oracle26ai_db_bhagavan sqlplus EA_APP/jnjnuh@FREEPDB1 @/tmp/oll_schema.sql
```

### 3. Python Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

**requirements.txt:**
```
fastapi>=0.104.0
uvicorn>=0.24.0
oracledb>=1.4.0
google-generativeai>=0.3.0
pydantic>=2.5.0
requests>=2.31.0
streamlit>=1.32.0  # For UI only
```

### 4. Environment Configuration

```bash
# Set Gemini API key
export GOOGLE_API_KEY="your-gemini-api-key"

# Or create .env file
echo "GOOGLE_API_KEY=your-gemini-api-key" > .env
```

### 5. Verify Installation

```bash
# Check Python version
python --version

# Test imports
python -c "import fastapi, oracledb, google.generativeai; print('✅ All dependencies installed')"

# Test database connection
python -c "import oracledb; conn = oracledb.connect('EA_APP/password@localhost/FREEPDB1'); print('✅ Database connected')"
```

---

## 📖 Usage

### API Server

```bash
# Start server
cd OIC-LogLens/src
python main.py

# Server starts at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Web UI

```bash
# Start UI (in separate terminal)
streamlit run app.py

# UI opens at http://localhost:8501
```

### Command Line

```bash
# Run all tests
cd tests
bash test_api_examples.sh

# Test specific endpoint
python test_search_api.py
```

---

## 🌐 API Documentation

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/ingest/file` | Ingest from file path |
| `POST` | `/ingest/url` | Ingest from URL |
| `POST` | `/ingest/raw` | Ingest from raw JSON |
| `POST` | `/ingest/database` | Ingest from DB query (batch) |
| `POST` | `/search` | Search for similar logs |

### Example: Ingest from File

**Request:**
```bash
curl -X POST http://localhost:8000/ingest/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "flow-logs/01_flow-log.json"
  }'
```

**Response:**
```json
{
  "log_id": "9f9da348-963c-41fe-8c61-3ec23dbb3c13",
  "jira_id": "https://promptlyai.atlassian.net/browse/OLL-4FF0674A",
  "status": "success",
  "message": "Log ingested successfully"
}
```

### Example: Search for Duplicates

**Request:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "log_content": "[{...log json...}]"
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Found 5 similar logs",
  "matches": [
    {
      "jira_id": "https://promptlyai.atlassian.net/browse/OLL-4FF0674A",
      "similarity_score": 100.0,
      "flow_code": "RH_NAVAN_DAILY_INTEGR_SCHEDU",
      "trigger_type": "scheduled",
      "error_code": "Execution failed",
      "error_summary": "oracle.cloud.connector.api.CloudInvocationException"
    }
  ]
}
```

**Interactive API Docs:** Open browser → `http://localhost:8000/docs`

---

## 🎨 Web UI

### Features

- **📥 Ingest Page** — 4 tabs (Upload, URL, Raw, Database)
- **🔍 Search Page** — File upload + text input
- **📊 Dashboard** — System overview
- **✅ Real-time status** — API health indicator
- **🎯 One-click actions** — No command line needed

### Screenshots

Coming soon! (Add screenshots of your UI here)

### Usage

1. Start API server: `python main.py`
2. Start UI: `streamlit run app.py`
3. Open browser: `http://localhost:8501`
4. Upload a log or paste JSON
5. Get results instantly!

---

## 🧪 Testing

See [TESTING.md](TESTING.md) for comprehensive testing guide.

### Quick Test

```bash
# Health check
curl http://localhost:8000/health

# Ingest all test logs
cd tests
bash test_api_examples.sh

# Search test
python test_search_api.py
```

### Test Data

8 sample OIC error logs in `flow-logs/`:
- CloudInvocationException (404)
- SQL table not found
- HTTP 503 service unavailable
- ERP SOAP fault
- Supplier creation error (400)
- Authentication failure (401)
- REST endpoint 406 error
- FTP file not found

---

## 📁 Project Structure

```
OIC-LogLens/
├── src/
│   ├── main.py                 # FastAPI application
│   ├── app.py                  # Streamlit UI
│   ├── models.py               # Pydantic models
│   ├── config.py               # Configuration
│   ├── prompts.py              # LLM prompts
│   ├── normalizer.py           # Log normalization
│   ├── embedder.py             # Embedding generation
│   ├── ingestion_service.py    # Ingestion pipeline
│   ├── search_service.py       # Search pipeline
│   ├── db.py                   # Database operations
│   ├── oll_schema.sql          # Database schema
│   ├── flow-logs/              # Test log files
│   └── tests/                  # Test scripts
│       ├── test_api_examples.sh
│       ├── test_search_api.py
│       ├── test_normalize.py
│       └── load_logs_to_db.py
├── docs/
│   ├── NORMALIZATION.md        # Normalization docs
│   ├── usecase1-ingestion.png  # Architecture diagram
│   └── usecase2-search.png     # Architecture diagram
├── README.md                   # This file
├── TESTING.md                  # Testing guide
├── UI-README.md                # UI guide
└── requirements.txt            # Dependencies
```

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Gemini** — LLM and embedding models
- **Oracle** — Oracle 26ai Vector Database
- **FastAPI** — Modern API framework
- **Streamlit** — Beautiful UI framework

---

## 📞 Contact

**Project Maintainer:** Bhagavan Prasad  
**GitHub:** [@bhagavansprasad](https://github.com/bhagavansprasad)  
**Repository:** [oic-log-lens](https://github.com/bhagavansprasad/oic-log-lens)

---

## 🚀 What's Next?

- [ ] LLM re-ranking for smarter duplicate classification
- [ ] Docker deployment setup
- [ ] Performance optimization (caching, connection pooling)
- [ ] Monitoring and analytics dashboard
- [ ] Multi-tenancy support
- [ ] Scheduled log polling from OIC


---

## 📝 TODO / Known Issues

- [ ] **Sequence diagrams** — Add detailed RAG flow diagrams
- [ ] **Data masking** — Implement PII masking (email IDs, user IDs, credentials)
- [ ] **Table naming** — Consider renaming `OLL_LOGS` to more descriptive name
- [ ] **Similarity threshold** — Define automatic deduplication threshold
- [ ] **LLM re-ranking** — Implement re-ranking after vector search
- [ ] **Monitoring** — Add observability and performance metrics

