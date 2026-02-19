#!/bin/bash
# test_api_examples.sh
# -------------------
# Example API calls for OIC-LogLens REST API using curl.

# ============================================================
# START SERVER
# ============================================================
# python main.py
# Server runs on: http://localhost:8000
# Docs available at: http://localhost:8000/docs

# ============================================================
# HEALTH CHECK
# ============================================================

echo "=== Health Check ==="
curl -X GET http://localhost:8000/health
echo -e "\n"


# ============================================================
# INGEST FILE
# ============================================================

echo "=== Example 1: Ingest log (jira_id auto-extracted or generated) ==="
curl -X POST http://localhost:8000/ingest/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "flow-logs/01_flow-log.json"
  }'
echo -e "\n"


echo "=== Example 2: Ingest another log ==="
curl -X POST http://localhost:8000/ingest/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "flow-logs/02_flow-log.json"
  }'
echo -e "\n"


echo "=== Example 3: Test duplicate detection (run same file twice) ==="
curl -X POST http://localhost:8000/ingest/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "flow-logs/01_flow-log.json"
  }'
echo -e "\n"


echo "=== Example 4: Test error handling - file not found ==="
curl -X POST http://localhost:8000/ingest/file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/nonexistent/file.json"
  }'
echo -e "\n"


# ============================================================
# BATCH INGEST ALL TEST FILES
# ============================================================

echo "=== Batch ingest all test files ==="
for i in $(seq -w 1 8); do
  echo "Ingesting flow-logs/${i}_flow-log.json"
  curl -X POST http://localhost:8000/ingest/file \
    -H "Content-Type: application/json" \
    -d "{\"file_path\": \"flow-logs/${i}_flow-log.json\"}"
  echo ""
done


# ============================================================
# INTERACTIVE DOCS
# ============================================================
# Open browser: http://localhost:8000/docs
# FastAPI auto-generates interactive Swagger UI
# You can test all endpoints directly from the browser



# ============================================================
# SEARCH FOR DUPLICATES
# ============================================================
# Use the Python test script instead:
# python test_search_api.py


# ============================================================
# INGEST FROM URL
# ============================================================

curl -X POST http://localhost:8000/ingest/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://storage.googleapis.com/promptlyai-public-bucket/oci_logs/01_flow-log.json"
  }'

# ============================================================
# INGEST FROM RAW TEXT
# ============================================================

echo "=== Ingest from raw text ==="
LOG_CONTENT=$(cat flow-logs/03_flow-log.json)
curl -X POST http://localhost:8000/ingest/raw \
  -H "Content-Type: application/json" \
  -d "{\"log_content\": \"$(echo $LOG_CONTENT | sed 's/"/\\"/g' | tr -d '\n')\"}"
echo -e "\n"


# ============================================================
# INGEST FROM DATABASE
# ============================================================

echo "=== Ingest from database ==="
curl -X POST http://localhost:8000/ingest/database \
  -H "Content-Type: application/json" \
  -d '{
    "connection_string": "oracle://user:pass@host:1521/service",
    "query": "SELECT log_json FROM oic_logs WHERE log_id = 123"
  }'
echo -e "\n"