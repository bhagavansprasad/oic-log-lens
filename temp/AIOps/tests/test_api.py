# =============================================================
# AIOps Platform — FastAPI Endpoint Tests
# Uses TestClient (no real HTTP server needed)
# Run from project root: python3 tests/test_api.py
# =============================================================

import sys
import os
import json
import io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(msg):   print(f"  ✅ {msg}")
def info(msg): print(f"  ℹ️  {msg}")
def fail(msg):
    print(f"  ❌ {msg}")
    sys.exit(1)


# TestClient must be used as context manager to trigger lifespan
with TestClient(app) as client:

    # ------------------------------------------------------------------ #
    # TEST 1 — Health check
    # ------------------------------------------------------------------ #
    section("TEST 1 — GET /health")
    try:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        ok(f"Status: {r.status_code} | {r.json()}")
    except Exception as e:
        fail(str(e))

    # ------------------------------------------------------------------ #
    # TEST 2 — POST /logs/ingest
    # ------------------------------------------------------------------ #
    section("TEST 2 — POST /logs/ingest")
    try:
        logs = [
            {
                "eventId":       "API-EVT-001",
                "timestamp":     "2026-02-14T10:00:00Z",
                "flow_code":     "INVOICE_PROCESSING",
                "action_name":   "VALIDATE_INVOICE",
                "error_level":   "ERROR",
                "error_code":    "SCHEMA_VALIDATION_FAILED",
                "error_message": "Invoice schema validation failed, missing mandatory field amount",
                "business_key":  "INV-3001",
            },
            {
                "eventId":       "API-EVT-002",
                "timestamp":     "2026-02-14T10:05:00Z",
                "flow_code":     "SUPPLIER_ONBOARDING",
                "action_name":   "VERIFY_BANK_DETAILS",
                "error_level":   "ERROR",
                "error_code":    "BANK_API_TIMEOUT",
                "error_message": "Bank verification API timed out after 10 seconds",
                "business_key":  "SUP-7001",
            },
        ]

        r = client.post("/logs/ingest", json=logs)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

        body = r.json()
        info(f"Response: {body}")
        assert body["processed"] == 2
        assert body["stored"]    == 2
        assert body["failed"]    == 0
        ok(f"Ingested {body['stored']} logs in {body['duration_ms']}ms")

    except Exception as e:
        fail(str(e))

    # ------------------------------------------------------------------ #
    # TEST 3 — POST /logs/match — Option A (error_text)
    # ------------------------------------------------------------------ #
    section("TEST 3 — POST /logs/match (Option A — error_text)")
    try:
        r = client.post("/logs/match", json={
            "error_text": "flow: INVOICE_PROCESSING\nstep: VALIDATE_INVOICE\nerror: Invoice validation failed missing amount field"
        })
        assert r.status_code == 200, f"{r.status_code}: {r.text}"

        body = r.json()
        info(f"Status     : {body['status']}")
        info(f"Known      : {body['known']}")
        info(f"Similarity : {body['similarity']}")
        info(f"Top match  : {body['top_match']['log_id'] if body['top_match'] else None}")
        info(f"Duration   : {body['duration_ms']}ms")

        assert body["top_match"] is not None
        assert body["similarity"] > 0.75
        ok(f"Match found | status={body['status']} similarity={body['similarity']}")

    except Exception as e:
        fail(str(e))

    # ------------------------------------------------------------------ #
    # TEST 4 — POST /logs/match — Option B (log dict)
    # ------------------------------------------------------------------ #
    section("TEST 4 — POST /logs/match (Option B — log dict)")
    try:
        r = client.post("/logs/match", json={
            "log": {
                "flow_code":     "INVOICE_PROCESSING",
                "action_name":   "VALIDATE_INVOICE",
                "error_message": "Schema validation error on invoice document",
                "business_key":  "INV-9999",
            }
        })
        assert r.status_code == 200, f"{r.status_code}: {r.text}"

        body = r.json()
        info(f"Status     : {body['status']}")
        info(f"Similarity : {body['similarity']}")
        info(f"Alternatives: {len(body['alternatives'])}")

        assert body["top_match"] is not None
        assert body["similarity"] > 0.75
        ok(f"Match found | status={body['status']} similarity={body['similarity']}")

    except Exception as e:
        fail(str(e))

    # ------------------------------------------------------------------ #
    # TEST 5 — POST /logs/match/file — Option C (file upload)
    # ------------------------------------------------------------------ #
    section("TEST 5 — POST /logs/match/file (Option C — file upload)")
    try:
        log_file_content = json.dumps({
            "flow_code":     "SUPPLIER_ONBOARDING",
            "action_name":   "VERIFY_BANK_DETAILS",
            "error_message": "Bank API not responding, request timed out",
            "business_key":  "SUP-8888",
        }).encode()

        r = client.post(
            "/logs/match/file",
            files={"file": ("error_log.json", io.BytesIO(log_file_content), "application/json")},
            params={"top_k": 3},
        )
        assert r.status_code == 200, f"{r.status_code}: {r.text}"

        body = r.json()
        info(f"Status     : {body['status']}")
        info(f"Similarity : {body['similarity']}")
        info(f"Top match  : {body['top_match']['log_id'] if body['top_match'] else None}")

        assert body["top_match"] is not None
        ok(f"File upload match | status={body['status']} similarity={body['similarity']}")

    except Exception as e:
        fail(str(e))

    # ------------------------------------------------------------------ #
    # TEST 6 — Validation errors
    # ------------------------------------------------------------------ #
    section("TEST 6 — Validation error handling")
    try:
        # Empty array
        r = client.post("/logs/ingest", json=[])
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"
        ok(f"Empty ingest array → 422 ✓")

        # No input fields
        r = client.post("/logs/match", json={})
        assert r.status_code == 422, f"Expected 422, got {r.status_code}"
        ok(f"Empty match body → 422 ✓")

        # Wrong file type
        r = client.post(
            "/logs/match/file",
            files={"file": ("log.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert r.status_code == 415, f"Expected 415, got {r.status_code}"
        ok(f"Non-JSON file → 415 ✓")

    except Exception as e:
        fail(str(e))

    # ------------------------------------------------------------------ #
    # Done
    # ------------------------------------------------------------------ #
    section("ALL API TESTS PASSED 🎉")