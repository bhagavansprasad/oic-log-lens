# =============================================================
# AIOps Platform — AIOpsService End-to-End Test
# Tests ingest_logs() and match_error() with realistic data
# Run from project root: python3 tests/test_aiops_service.py
# =============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import load_config
from db.connection import OracleConnectionPool
from services.semantic_text_builder import SemanticTextBuilder
from services.embedding_service import EmbeddingService
from services.oracle_semantic_repository import OracleSemanticRepository
from services.aiops_service import AIOpsService


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def ok(msg):   print(f"  ✅ {msg}")
def info(msg): print(f"  ℹ️  {msg}")
def fail(msg):
    print(f"  ❌ {msg}")
    sys.exit(1)


# ------------------------------------------------------------------ #
# Bootstrap all Phase 1 components
# ------------------------------------------------------------------ #
section("BOOTSTRAP — Initialising Phase 1 Components")
cfg = load_config()

pool = OracleConnectionPool(cfg.oracle)
pool.init()
ok("Oracle pool ready")

embedding_svc = EmbeddingService(cfg.gemini)
embedding_svc.init()
ok("EmbeddingService ready")

builder  = SemanticTextBuilder()
repo     = OracleSemanticRepository(pool)
service  = AIOpsService(
    builder       = builder,
    embedding_svc = embedding_svc,
    repository    = repo,
    threshold_known    = cfg.threshold_known,
    threshold_related  = cfg.threshold_related,
)
ok("AIOpsService ready")

# ------------------------------------------------------------------ #
# Sample log dataset — realistic OIC/integration errors
# ------------------------------------------------------------------ #
SAMPLE_LOGS = [
    {
        "eventId":       "EVT-001",
        "timestamp":     "2026-01-10T08:00:00Z",
        "flow_code":     "ORDER_TO_CASH",
        "action_name":   "INVOKE_ERP_API",
        "endpoint_name": "https://erp.internal/api/orders",
        "error_level":   "ERROR",
        "error_code":    "TIMEOUT_30000",
        "error_message": "Connection timeout to ERP endpoint after 30000ms",
        "order_id":      "ORD-1001",
    },
    {
        "eventId":       "EVT-002",
        "timestamp":     "2026-01-10T09:15:00Z",
        "flow_code":     "PAYMENT_PROCESSING",
        "action_name":   "CHARGE_CREDIT_CARD",
        "endpoint_name": "https://payment.gateway/charge",
        "error_level":   "ERROR",
        "error_code":    "CARD_DECLINED",
        "error_message": "Credit card payment declined by issuing bank",
        "transaction_id": "TXN-5001",
    },
    {
        "eventId":       "EVT-003",
        "timestamp":     "2026-01-10T10:30:00Z",
        "flow_code":     "INVENTORY_SYNC",
        "action_name":   "UPDATE_STOCK_LEVEL",
        "endpoint_name": "https://wms.internal/stock",
        "error_level":   "WARNING",
        "error_code":    "LOCK_TIMEOUT",
        "error_message": "Database lock timeout while updating stock level for SKU",
        "business_key":  "SKU-X200",
    },
    {
        "eventId":       "EVT-004",
        "timestamp":     "2026-01-10T11:45:00Z",
        "flow_code":     "CUSTOMER_NOTIFICATION",
        "action_name":   "SEND_EMAIL",
        "endpoint_name": "https://smtp.internal/send",
        "error_level":   "ERROR",
        "error_code":    "SMTP_CONN_REFUSED",
        "error_message": "SMTP connection refused by mail server on port 587",
        "customer_id":   "CUST-9001",
    },
    {
        "eventId":       "EVT-005",
        "timestamp":     "2026-01-10T12:00:00Z",
        "flow_code":     "ORDER_TO_CASH",
        "action_name":   "INVOKE_ERP_API",
        "endpoint_name": "https://erp.internal/api/orders",
        "error_level":   "ERROR",
        "error_code":    "TIMEOUT_30000",
        "error_message": "ERP service not responding, request timed out after 30 seconds",
        "order_id":      "ORD-1002",
    },
]

# ------------------------------------------------------------------ #
# TEST 1 — Bulk Ingestion
# ------------------------------------------------------------------ #
section("TEST 1 — ingest_logs() bulk ingestion")
try:
    result = service.ingest_logs(SAMPLE_LOGS)
    info(f"Processed : {result.processed}")
    info(f"Stored    : {result.stored}")
    info(f"Failed    : {result.failed}")
    info(f"Duration  : {result.duration_ms:.1f}ms")

    assert result.processed == 5,    f"Expected 5 processed, got {result.processed}"
    assert result.stored    == 5,    f"Expected 5 stored, got {result.stored}"
    assert result.failed    == 0,    f"Expected 0 failed, got {result.failed}"
    ok("All 5 logs ingested successfully")

except Exception as e:
    fail(f"ingest_logs failed: {e}")

# ------------------------------------------------------------------ #
# TEST 2 — match_error: KNOWN incident (same error)
# ------------------------------------------------------------------ #
section("TEST 2 — match_error() → expected: KNOWN")
try:
    # Nearly identical to EVT-001 — should be known
    decision = service.match_error(log={
        "flow_code":     "ORDER_TO_CASH",
        "action_name":   "INVOKE_ERP_API",
        "error_message": "Connection timeout to ERP endpoint after 30000ms",
        "order_id":      "ORD-9999",
    })

    info(f"Status     : {decision.status}")
    info(f"Similarity : {decision.similarity:.4f}")
    info(f"Top match  : {decision.top_match.log_id}")
    info(f"Duration   : {decision.duration_ms:.1f}ms")

    assert decision.status == "known", f"Expected 'known', got '{decision.status}'"
    assert decision.similarity > 0.90, f"Expected >0.90, got {decision.similarity}"
    ok(f"Correctly identified as KNOWN (similarity={decision.similarity:.4f})")

except Exception as e:
    fail(f"match_error KNOWN test failed: {e}")

# ------------------------------------------------------------------ #
# TEST 3 — match_error: RELATED incident (similar but different)
# ------------------------------------------------------------------ #
section("TEST 3 — match_error() → expected: RELATED or KNOWN")
try:
    # Similar timeout error but different flow — expect related or known
    decision = service.match_error(log={
        "flow_code":     "ORDER_TO_CASH",
        "action_name":   "INVOKE_ERP_API",
        "error_message": "ERP backend service timeout, no response within 30s",
        "order_id":      "ORD-2000",
    })

    info(f"Status     : {decision.status}")
    info(f"Similarity : {decision.similarity:.4f}")
    info(f"Top match  : {decision.top_match.log_id}")

    assert decision.status in ("known", "related"), \
        f"Expected known or related, got '{decision.status}'"
    assert decision.similarity > 0.75, \
        f"Expected >0.75, got {decision.similarity}"
    ok(f"Correctly identified as {decision.status.upper()} (similarity={decision.similarity:.4f})")

except Exception as e:
    fail(f"match_error RELATED test failed: {e}")

# ------------------------------------------------------------------ #
# TEST 4 — match_error: NEW incident (unrelated error)
# ------------------------------------------------------------------ #
section("TEST 4 — match_error() → expected: NEW")
try:
    decision = service.match_error(log={
        "flow_code":     "HR_PAYROLL",
        "action_name":   "CALCULATE_TAX",
        "error_message": "Tax calculation engine returned null for employee bracket",
        "business_key":  "EMP-5050",
    })

    info(f"Status     : {decision.status}")
    info(f"Similarity : {decision.similarity:.4f}")
    info(f"Top match  : {decision.top_match.log_id if decision.top_match else 'None'}")

    assert decision.status == "new", \
        f"Expected 'new', got '{decision.status}' (similarity={decision.similarity:.4f})"
    ok(f"Correctly identified as NEW (similarity={decision.similarity:.4f})")

except Exception as e:
    fail(f"match_error NEW test failed: {e}")

# ------------------------------------------------------------------ #
# TEST 5 — match_error: via raw error_text
# ------------------------------------------------------------------ #
section("TEST 5 — match_error() via raw error_text input")
try:
    decision = service.match_error(
        error_text="flow: PAYMENT_PROCESSING\nstep: CHARGE_CREDIT_CARD\nerror: Credit card declined by bank"
    )

    info(f"Status     : {decision.status}")
    info(f"Similarity : {decision.similarity:.4f}")
    info(f"Semantic   : {decision.semantic_text}")

    assert decision.top_match is not None, "Should have a match"
    assert decision.similarity > 0.75,     "Should be at least related"
    ok(f"Raw text match worked | status={decision.status} similarity={decision.similarity:.4f}")

except Exception as e:
    fail(f"match_error raw text test failed: {e}")

# ------------------------------------------------------------------ #
# TEST 6 — Alternatives list
# ------------------------------------------------------------------ #
section("TEST 6 — Alternatives in match result")
try:
    decision = service.match_error(log={
        "flow_code":     "ORDER_TO_CASH",
        "action_name":   "INVOKE_ERP_API",
        "error_message": "Timeout connecting to ERP system",
        "order_id":      "ORD-3000",
    }, top_k=5)

    info(f"Top match    : {decision.top_match.log_id} ({decision.similarity:.4f})")
    info(f"Alternatives : {len(decision.alternatives)}")
    for alt in decision.alternatives:
        info(f"  - {alt.log_id} ({alt.similarity:.4f})")

    assert decision.top_match is not None
    ok(f"Got top match + {len(decision.alternatives)} alternative(s)")

except Exception as e:
    fail(f"Alternatives test failed: {e}")

# ------------------------------------------------------------------ #
# Done
# ------------------------------------------------------------------ #
section("ALL AIOPS SERVICE TESTS PASSED 🎉")
pool.close()
