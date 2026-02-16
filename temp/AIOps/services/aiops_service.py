# =============================================================
# AIOps Platform — AIOps Service
#
# Business logic layer that wires together:
#   - SemanticTextBuilder
#   - EmbeddingService
#   - OracleSemanticRepository
#
# Exposes two core operations:
#   - ingest_logs()   → bulk upsert logs into Oracle
#   - match_error()   → semantic similarity match for new error
# =============================================================

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from services.semantic_text_builder import SemanticTextBuilder
from services.embedding_service import EmbeddingService
from services.oracle_semantic_repository import (
    OracleSemanticRepository,
    LogRecord,
    SearchResult,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Result Models
# ------------------------------------------------------------------ #

@dataclass
class IngestionResult:
    """Result of a bulk log ingestion operation."""
    processed: int
    stored: int
    failed: int
    duration_ms: float


@dataclass
class MatchDecision:
    """
    Similarity decision for a new error.

    status values:
        'known'   → similarity > threshold_known   (>0.90)
        'related' → similarity > threshold_related (>0.75)
        'new'     → similarity <= threshold_related
        'empty'   → no records in store yet
    """
    status: str                        # known | related | new | empty
    similarity: float                  # top match similarity score
    top_match: SearchResult | None     # best matching record
    alternatives: list[SearchResult]   # next best matches
    semantic_text: str                 # what was actually embedded
    duration_ms: float


# ------------------------------------------------------------------ #
# AIOpsService
# ------------------------------------------------------------------ #

class AIOpsService:
    """
    Core business logic service for AIOps semantic error intelligence.

    Requires all three Phase 1 components to be initialised before use.
    """

    def __init__(
        self,
        builder: SemanticTextBuilder,
        embedding_svc: EmbeddingService,
        repository: OracleSemanticRepository,
        threshold_known: float = 0.90,
        threshold_related: float = 0.75,
    ):
        self._builder = builder
        self._embedding = embedding_svc
        self._repo = repository
        self._threshold_known = threshold_known
        self._threshold_related = threshold_related

    # ------------------------------------------------------------------ #
    # Ingestion
    # ------------------------------------------------------------------ #

    def ingest_logs(self, logs: list[dict[str, Any]]) -> IngestionResult:
        """
        Bulk ingest a list of raw log dicts into Oracle.

        For each log:
          1. Build semantic text (excluded fields stripped)
          2. Generate Gemini embedding
          3. MERGE into Oracle (upsert)

        Args:
            logs: List of raw log JSON dicts.

        Returns:
            IngestionResult with processed / stored / failed counts.
        """
        processed = 0
        stored = 0
        failed = 0
        start = time.perf_counter()

        for i, log in enumerate(logs):
            processed += 1
            try:
                # Step 1 — semantic text
                semantic_text = self._builder.build_from_log(log)

                # Step 2 — embedding
                vector = self._embedding.generate_vector(semantic_text)

                # Step 3 — build LogRecord
                record = self._build_record(log, semantic_text, vector)

                # Step 4 — upsert into Oracle
                self._repo.merge_content(record)
                stored += 1

                logger.debug("Ingested log %d/%d | log_id=%s", i + 1, len(logs), record.log_id)

            except ValueError as e:
                # Semantic text build failure — skip gracefully
                failed += 1
                logger.warning("Skipped log %d — semantic build failed: %s", i, e)

            except Exception as e:
                failed += 1
                logger.error("Failed to ingest log %d: %s", i, e)

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "ingest_logs complete | processed=%d stored=%d failed=%d duration_ms=%.1f",
            processed, stored, failed, duration_ms,
        )

        return IngestionResult(
            processed=processed,
            stored=stored,
            failed=failed,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------ #
    # Match
    # ------------------------------------------------------------------ #

    def match_error(
        self,
        error_text: str | None = None,
        log: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> MatchDecision:
        """
        Find semantically similar past errors for a new error.

        Accepts either:
          - error_text: raw semantic string (direct input)
          - log: raw log dict (semantic text will be extracted)

        Similarity decision logic (from spec §7):
          > 0.90  → known   (same incident)
          > 0.75  → related (similar issue)
          <= 0.75 → new     (unseen issue)

        Args:
            error_text: Raw error text string (Option A).
            log:        Raw log dict (Option B).
            top_k:      Max number of candidates to retrieve.

        Returns:
            MatchDecision with status, top match, and alternatives.
        """
        if not error_text and not log:
            raise ValueError("Provide either error_text or log dict.")

        start = time.perf_counter()

        # Step 1 — build semantic text
        if error_text:
            semantic_text = self._builder.build_from_raw_text(error_text)
        else:
            semantic_text = self._builder.build_from_log(log)

        # Step 2 — embed
        vector = self._embedding.generate_vector(semantic_text)

        # Step 3 — search
        results = self._repo.semantic_search(
            query_vector=vector,
            top_k=top_k,
            min_similarity=0.0,
        )

        duration_ms = (time.perf_counter() - start) * 1000

        # Step 4 — decision
        if not results:
            return MatchDecision(
                status="empty",
                similarity=0.0,
                top_match=None,
                alternatives=[],
                semantic_text=semantic_text,
                duration_ms=duration_ms,
            )

        top = results[0]
        alternatives = results[1:]
        status = self._decide_status(top.similarity)

        logger.info(
            "match_error | status=%s | similarity=%.4f | top_match=%s | duration_ms=%.1f",
            status, top.similarity, top.log_id, duration_ms,
        )

        return MatchDecision(
            status=status,
            similarity=top.similarity,
            top_match=top,
            alternatives=alternatives,
            semantic_text=semantic_text,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _decide_status(self, similarity: float) -> str:
        """Apply similarity threshold policy from spec §7."""
        if similarity > self._threshold_known:
            return "known"
        elif similarity > self._threshold_related:
            return "related"
        else:
            return "new"

    def _build_record(
        self,
        log: dict[str, Any],
        semantic_text: str,
        vector: list[float],
    ) -> LogRecord:
        """
        Build a LogRecord from a raw log dict.
        LOG_ID is deterministic — SHA256 of semantic text (first 32 chars).
        This ensures identical errors get the same ID (natural deduplication).
        """
        # Deterministic ID from semantic content
        log_id = log.get("log_id") or log.get("event_id") or log.get("eventId")
        if not log_id:
            log_id = "LOG-" + hashlib.sha256(
                semantic_text.encode()
            ).hexdigest()[:16].upper()

        # Parse event time
        event_time = None
        raw_time = log.get("event_time") or log.get("timestamp") or log.get("created_at")
        if raw_time and isinstance(raw_time, str):
            try:
                event_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            except ValueError:
                event_time = datetime.now()
        elif isinstance(raw_time, datetime):
            event_time = raw_time
        else:
            event_time = datetime.now()

        # Extract structured fields
        ctx = self._builder.extract_context(log)

        # Everything else goes into attributes bag
        known_keys = {
            "log_id", "event_id", "eventId",
            "event_time", "timestamp", "created_at",
            "flow_code", "flow", "integration_name", "pipeline_name",
            "action_name", "action", "step", "step_name",
            "error_message", "error", "message", "fault_message",
            "endpoint_name", "endpoint",
            "error_level", "level", "severity",
            "error_code", "code",
            "business_key", "business_id", "order_id",
            "customer_id", "transaction_id", "request_id",
        }
        attributes = {k: v for k, v in log.items() if k not in known_keys}

        return LogRecord(
            log_id        = str(log_id),
            event_time    = event_time,
            flow_code     = ctx.flow_code,
            action_name   = ctx.action_name,
            endpoint_name = log.get("endpoint_name") or log.get("endpoint"),
            error_level   = log.get("error_level") or log.get("level") or log.get("severity"),
            error_code    = log.get("error_code") or log.get("code"),
            semantic_text = semantic_text,
            raw_json      = json.dumps(log),
            attributes    = attributes,
            vector        = vector,
        )