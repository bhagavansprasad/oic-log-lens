# OIC-LogLens — Testing Guide

Complete guide for testing all endpoints and functionality of the OIC-LogLens API.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Starting the Server](#starting-the-server)
3. [Test Files Overview](#test-files-overview)
4. [Testing Endpoints](#testing-endpoints)
5. [Quick Tests](#quick-tests)

---

## Prerequisites

**Install Dependencies:**
```bash
pip install fastapi uvicorn oracledb requests google-generativeai --break-system-packages
```

**Database Setup:**
- Oracle 26ai running with `OLL_LOGS` table
- Connection: `EA_APP/jnjnuh@localhost/FREEPDB1`

**Environment Variables:**
```bash
export GOOGLE_API_KEY="your-gemini-api-key"
# or
export GEMINI_API_KEY="your-gemini-api-key"
```

---

## Starting the Server

```bash
cd OIC-LogLens/src
python main.py
```

Server runs at: `http://localhost:8000`

**Interactive API Docs:** Open browser → `http://localhost:8000/docs`

---

## Test Files Overview

All test files are in the `tests/` directory:

| File | Purpose |
|---|---|
| `test_api_examples.sh` | Shell script with curl examples for all endpoints |
| `test_search_api.py` | Python script to test `/search` endpoint |
| `test_normalize.py` | Unit test for normalization + embedding + DB insert |
| `test_search.py` | Original search test (command line) |
| `load_logs_to_db.py` | Load all 8 log files into TEST_LOGS table for DB testing |

---

## Testing Endpoints

### 1. Health Check

**Purpose:** Verify server is running

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{"status": "healthy", "service": "OIC-LogLens"}
```

---

### 2. POST /ingest/file

**Purpose:** Ingest log from local file path

```bash
curl -X POST http://localhost:8000/ingest/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "flow-logs/01_flow-log.json"
  }'
```

**Expected Response:**
```json
{
  "log_id": "9f9da348-963c-41fe-8c61-3ec23dbb3c13",
  "jira_id": "https://promptlyai.atlassian.net/browse/OLL-4FF0674A",
  "status": "success",
  "message": "Log ingested successfully"
}
```

**Test Duplicate Detection:**
Run the same command twice → Second attempt returns `409 Conflict`

---

### 3. POST /ingest/url

**Purpose:** Ingest log from HTTP/HTTPS URL

**Setup:** Upload a log file to a public URL (GCS, S3, GitHub raw, etc.)

```bash
curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://storage.googleapis.com/promptlyai-public-bucket/oci_logs/01_flow-log.json"
  }'
```

**Expected Response:** Same as `/ingest/file`

---

### 4. POST /ingest/raw

**Purpose:** Ingest log from raw JSON text

**Python Test:**
```python
import requests

with open('flow-logs/05_flow-log.json', 'r') as f:
    log_content = f.read()

response = requests.post(
    'http://localhost:8000/ingest/raw',
    json={'log_content': log_content}
)

print(response.json())
```

**Shell Test:**
```bash
LOG_CONTENT=$(cat flow-logs/05_flow-log.json)

curl -X POST http://localhost:8000/ingest/raw \
  -H "Content-Type: application/json" \
  --data-binary @- << EOF
{
  "log_content": $(echo "$LOG_CONTENT" | jq -Rs .)
}
EOF
```

---

### 5. POST /ingest/database

**Purpose:** Ingest log from database query

**Setup:** Load test data into Oracle
```bash
cd tests
python load_logs_to_db.py
```

This creates `TEST_LOGS` table with 8 log files.

**Test:**
```bash
curl -X POST http://localhost:8000/ingest/database \
  -H "Content-Type: application/json" \
  -d '{
    "connection_string": "EA_APP/jnjnuh@localhost/FREEPDB1",
    "query": "SELECT LOG_JSON FROM TEST_LOGS WHERE LOG_ID = 1"
  }'
```

**Expected Response:** Same as other ingest endpoints

---

### 6. POST /search

**Purpose:** Search for duplicate/similar logs

**Python Test (Recommended):**
```bash
cd tests
python test_search_api.py
```

**Expected Output:**
```
=== Searching for similar logs ===

Status Code: 200

Status: success
Message: Found 5 similar logs

Rank 1:
  Jira ID    : https://promptlyai.atlassian.net/browse/OLL-4FF0674A
  Similarity : 100.0%
  Flow Code  : RH_NAVAN_DAILY_INTEGR_SCHEDU
  Trigger    : scheduled
  Error Code : Execution failed
  Summary    : oracle.cloud.connector.api.CloudInvocationException

Rank 2:
  Jira ID    : https://promptlyai.atlassian.net/browse/OLL-866F9103
  Similarity : 73.35%
  ...
```

**Manual Test with curl:**
```python
import requests

with open('flow-logs/01_flow-log.json', 'r') as f:
    log_content = f.read()

response = requests.post(
    'http://localhost:8000/search',
    json={'log_content': log_content}
)

print(response.json())
```

---

## Quick Tests

### Run All Tests at Once

**Shell Script:**
```bash
cd tests
bash test_api_examples.sh
```

This runs:
- Health check
- File ingestion (Examples 1-4)
- Batch ingestion (all 8 files)
- Duplicate detection tests
- Error handling tests

**Python Tests:**
```bash
cd tests

# Test normalization + embedding + DB insert
python test_normalize.py

# Test search endpoint
python test_search_api.py
```

---

## Testing with Swagger UI

**Easiest Method — No coding required!**

1. Open browser: `http://localhost:8000/docs`
2. Click on any endpoint (e.g., `/ingest/file`)
3. Click **"Try it out"**
4. Fill in the request body
5. Click **"Execute"**
6. See response in the browser

All 6 endpoints available with live testing!

---

## Common Issues

### Issue 1: 409 Duplicate Error
**Cause:** Log already ingested  
**Solution:** This is expected behavior. Use a different log file or clear the database.

### Issue 2: File Not Found (404)
**Cause:** Incorrect file path  
**Solution:** Ensure file path is relative to where the server is running (`cd OIC-LogLens/src`)

### Issue 3: Database Connection Failed
**Cause:** Invalid connection string or database not running  
**Solution:** Verify Oracle 26ai is running and connection details are correct

### Issue 4: Invalid JSON
**Cause:** Log file is not valid JSON or not an array  
**Solution:** Verify log file starts with `[` and ends with `]`

---

## Test Data

Test logs are in `flow-logs/` directory:

- `01_flow-log.json` — CloudInvocationException / 404 error
- `02_flow-log.json` — SQL table not found error
- `03_flow-log.json` — HTTP 503 service unavailable
- `04_flow-log.json` — ERP SOAP fault
- `05_flow-log.json` — Supplier creation error (400)
- `06_flow-log.json` — Authentication failure (401)
- `07_flow-log.json` — REST endpoint 406 error
- `08_flow-log.json` — FTP file not found

All logs have different error signatures for testing semantic similarity.

---

## Expected Test Results

### Ingestion
- ✅ First ingestion: `200 OK` with `log_id` and `jira_id`
- ✅ Duplicate ingestion: `409 Conflict` with duplicate message
- ✅ Invalid file: `404 Not Found`
- ✅ Invalid JSON: `400 Bad Request`

### Search
- ✅ Returns Top-5 matches
- ✅ Self-match has 100% similarity
- ✅ Similar errors have 70-80% similarity
- ✅ Different errors have 60-70% similarity

---

