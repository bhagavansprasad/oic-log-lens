# =============================================================
# AIOps Platform — Phase 1 End-to-End Test
# Tests all components: config, connection, embedding, repository
# Run from project root: python3 tests/test_phase1.py
# =============================================================

import sys
import os
import json
import hashlib
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(msg: str):
    print(f"  ✅ {msg}")

def fail(msg: str):
    print(f"  ❌ {msg}")
    sys.exit(1)

def info(msg: str):
    print(f"  ℹ️  {msg}")

# ------------------------------------------------------------------ #
# Test 1 — Config Loading
# ------------------------------------------------------------------ #
section("TEST 1 — Config Loading")
try:
    from config.settings import load_config
    cfg = load_config()
    ok(f"Oracle DSN     : {cfg.oracle.dsn}")
    ok(f"Oracle User    : {cfg.oracle.user}")
    ok(f"Gemini Model   : {cfg.gemini.model}")
    ok(f"Embedding Dim  : {cfg.gemini.embedding_dim}")
    ok(f"Threshold Known   : {cfg.threshold_known}")
    ok(f"Threshold Related : {cfg.threshold_related}")
except Exception as e:
    fail(f"Config load failed: {e}")

# ------------------------------------------------------------------ #
# Test 2 — SemanticTextBuilder
# ------------------------------------------------------------------ #
section("TEST 2 — SemanticTextBuilder")
try:
    from services.semantic_text_builder import SemanticTextBuilder

    builder = SemanticTextBuilder()

    # Test with realistic OIC/integration error log
    sample_log = {
        "eventId":       "EVT-20240114-001",      # must be excluded
        "timestamp":     "2024-01-14T10:30:00Z",  # must be excluded
        "flow_code":     "ORDER_TO_CASH",
        "action_name":   "INVOKE_ERP_API",
        "error_message": "Connection timeout to ERP endpoint after 30000ms",
        "order_id":      "ORD-98765",
        "payload_size":  4096,                     # must be excluded
    }

    text = builder.build_from_log(sample_log)
    info(f"Semantic text built:\n{text}")
    print()

    assert "flow: ORDER_TO_CASH"         in text, "Missing flow"
    assert "step: INVOKE_ERP_API"        in text, "Missing step"
    assert "error: Connection timeout"   in text, "Missing error"
    assert "business_key: ORD-98765"     in text, "Missing business_key"
    assert "EVT-20240114-001"        not in text, "eventId leaked!"
    assert "2024-01-14"              not in text, "timestamp leaked!"
    assert "4096"                    not in text, "payload_size leaked!"

    ok("All fields mapped correctly")
    ok("Excluded fields NOT in output")

except Exception as e:
    fail(f"SemanticTextBuilder failed: {e}")

# ------------------------------------------------------------------ #
# Test 3 — EmbeddingService (live Gemini call)
# ------------------------------------------------------------------ #
section("TEST 3 — EmbeddingService (live Gemini API call)")
try:
    from services.embedding_service import EmbeddingService

    svc = EmbeddingService(cfg.gemini)
    svc.init()
    ok("EmbeddingService initialised")

    # Use the semantic text we built above
    vector = svc.generate_vector(text)

    ok(f"Vector generated | dim={len(vector)}")
    assert len(vector) == 3072, f"Expected 3072 dims, got {len(vector)}"
    ok("Dimension check passed (3072)")

    # Sanity: values should be floats between -1 and 1
    assert all(isinstance(v, float) for v in vector[:10]), "Values not floats"
    assert all(-1.0 <= v <= 1.0 for v in vector[:10]), "Values out of [-1, 1] range"
    ok("Value range check passed")

    info(f"First 5 values: {[round(v, 6) for v in vector[:5]]}")

except Exception as e:
    fail(f"EmbeddingService failed: {e}")

# ------------------------------------------------------------------ #
# Test 4 — Oracle Connection Pool
# ------------------------------------------------------------------ #
section("TEST 4 — Oracle Connection Pool")
try:
    from db.connection import OracleConnectionPool

    pool = OracleConnectionPool(cfg.oracle)
    pool.init()
    ok("Connection pool initialised")

    # Simple ping
    with pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 'CONNECTED' FROM DUAL")
            row = cur.fetchone()
            assert row[0] == "CONNECTED"
    ok("Oracle ping successful")

except Exception as e:
    fail(f"Oracle connection failed: {e}")

# ------------------------------------------------------------------ #
# Test 5 — OracleSemanticRepository: merge + search
# ------------------------------------------------------------------ #
section("TEST 5 — OracleSemanticRepository (merge + search)")
try:
    from services.oracle_semantic_repository import (
        OracleSemanticRepository,
        LogRecord,
    )

    repo = OracleSemanticRepository(pool)

    # Build a test record
    test_log_id = "TEST-" + hashlib.md5(text.encode()).hexdigest()[:10].upper()

    record = LogRecord(
        log_id        = test_log_id,
        event_time    = datetime.now(),
        flow_code     = "ORDER_TO_CASH",
        action_name   = "INVOKE_ERP_API",
        endpoint_name = "https://erp.internal/api/orders",
        error_level   = "ERROR",
        error_code    = "TIMEOUT_30000",
        semantic_text = text,
        raw_json      = json.dumps(sample_log),
        attributes    = {"retry_count": 3, "region": "us-east-1"},
        vector        = vector,
    )

    # Merge (upsert)
    repo.merge_content(record)
    ok(f"merge_content OK | log_id={test_log_id}")

    # Search using same vector — should find itself as top match
    results = repo.semantic_search(query_vector=vector, top_k=3)
    assert len(results) > 0, "No results returned"
    ok(f"semantic_search returned {len(results)} result(s)")

    top = results[0]
    info(f"Top match     : {top.log_id}")
    info(f"Similarity    : {top.similarity:.4f}")
    info(f"Flow          : {top.flow_code}")
    info(f"Action        : {top.action_name}")

    assert top.log_id == test_log_id,       "Top match is not our inserted record"
    assert top.similarity > 0.99,           f"Self-similarity should be ~1.0, got {top.similarity}"
    ok("Top match is our inserted record ✓")
    ok(f"Self-similarity = {top.similarity:.4f} (expected ~1.0)")

except Exception as e:
    fail(f"OracleSemanticRepository failed: {e}")

# ------------------------------------------------------------------ #
# Test 6 — Store Stats
# ------------------------------------------------------------------ #
section("TEST 6 — Store Stats")
try:
    stats = repo.get_store_stats()
    ok(f"Store         : {stats.store_name}")
    ok(f"Total records : {stats.total_records}")
    ok(f"Oldest event  : {stats.oldest_event}")
    ok(f"Newest event  : {stats.newest_event}")
    assert stats.total_records >= 1, "Should have at least 1 record"

except Exception as e:
    fail(f"get_store_stats failed: {e}")

# ------------------------------------------------------------------ #
# Done
# ------------------------------------------------------------------ #
section("ALL PHASE 1 TESTS PASSED 🎉")
pool.close()