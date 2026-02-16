# =============================================================
# AIOps Platform — Oracle Semantic Repository
#
# Handles all DB operations against SS_ERROR_LOGS:
#   - merge_content()    → upsert a log + its vector
#   - semantic_search()  → ANN cosine similarity search
#   - get_store_stats()  → row count + index info
# =============================================================

from __future__ import annotations

import json
import logging
import time
import array
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import oracledb

from db.connection import OracleConnectionPool

logger = logging.getLogger(__name__)

# Store name for this domain
STORE_NAME = "SS_ERROR_LOGS"


# ------------------------------------------------------------------ #
# Data Models
# ------------------------------------------------------------------ #

@dataclass
class LogRecord:
    """
    Everything needed to persist one error log into Oracle.
    Caller populates this; repository writes it.
    """
    log_id: str
    event_time: datetime | None
    flow_code: str | None
    action_name: str | None
    endpoint_name: str | None
    error_level: str | None
    error_code: str | None
    semantic_text: str           # curated text (built by SemanticTextBuilder)
    raw_json: str                # original log as JSON string
    attributes: dict[str, Any]  # flexible metadata bag
    vector: list[float]          # 3072-dim embedding


@dataclass
class SearchResult:
    """One result from a semantic similarity search."""
    log_id: str
    similarity: float            # 0.0 → 1.0 (cosine similarity)
    flow_code: str | None
    action_name: str | None
    error_level: str | None
    error_code: str | None
    semantic_text: str
    event_time: datetime | None


@dataclass
class StoreStats:
    store_name: str
    total_records: int
    oldest_event: datetime | None
    newest_event: datetime | None


# ------------------------------------------------------------------ #
# Repository
# ------------------------------------------------------------------ #

class OracleSemanticRepository:
    """
    Handles read/write operations on SS_ERROR_LOGS (Oracle AI DB 26ai).
    Requires an initialised OracleConnectionPool.
    """

    def __init__(self, pool: OracleConnectionPool):
        self._pool = pool

    # ------------------------------------------------------------------ #
    # Write — MERGE upsert
    # ------------------------------------------------------------------ #

    def merge_content(self, record: LogRecord) -> None:
        """
        Upsert a log record into SS_ERROR_LOGS.
        If LOG_ID already exists → update all fields (including vector).
        If new → insert.

        This is idempotent — safe to call multiple times for same log_id.
        """
        sql = """
            MERGE INTO SS_ERROR_LOGS tgt
            USING (
                SELECT
                    :log_id          AS log_id,
                    :event_time      AS event_time,
                    :flow_code       AS flow_code,
                    :action_name     AS action_name,
                    :endpoint_name   AS endpoint_name,
                    :error_level     AS error_level,
                    :error_code      AS error_code,
                    :semantic_text   AS semantic_text,
                    :raw_json        AS raw_json,
                    :attributes      AS attributes,
                    :vector          AS vector
                FROM DUAL
            ) src
            ON (tgt.LOG_ID = src.log_id)
            WHEN MATCHED THEN UPDATE SET
                tgt.EVENT_TIME      = src.event_time,
                tgt.FLOW_CODE       = src.flow_code,
                tgt.ACTION_NAME     = src.action_name,
                tgt.ENDPOINT_NAME   = src.endpoint_name,
                tgt.ERROR_LEVEL     = src.error_level,
                tgt.ERROR_CODE      = src.error_code,
                tgt.SEMANTIC_TEXT   = src.semantic_text,
                tgt.RAW_JSON        = src.raw_json,
                tgt.ATTRIBUTES      = src.attributes,
                tgt.VECTOR          = src.vector
            WHEN NOT MATCHED THEN INSERT (
                LOG_ID, EVENT_TIME, FLOW_CODE, ACTION_NAME,
                ENDPOINT_NAME, ERROR_LEVEL, ERROR_CODE,
                SEMANTIC_TEXT, RAW_JSON, ATTRIBUTES, VECTOR
            ) VALUES (
                src.log_id, src.event_time, src.flow_code, src.action_name,
                src.endpoint_name, src.error_level, src.error_code,
                src.semantic_text, src.raw_json, src.attributes, src.vector
            )
        """

        # Oracle expects VECTOR as a float array in oracledb
        vector_data = array.array("f", record.vector)

        params = {
            "log_id":        record.log_id,
            "event_time":    record.event_time,
            "flow_code":     record.flow_code,
            "action_name":   record.action_name,
            "endpoint_name": record.endpoint_name,
            "error_level":   record.error_level,
            "error_code":    record.error_code,
            "semantic_text": record.semantic_text,
            "raw_json":      record.raw_json,
            "attributes":    json.dumps(record.attributes),
            "vector":        vector_data,
        }

        start = time.perf_counter()

        with self._pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            "merge_content complete | log_id=%s | latency_ms=%.1f",
            record.log_id, elapsed_ms,
        )

    def merge_batch(self, records: list[LogRecord]) -> tuple[int, int]:
        """
        Upsert multiple records. Each is merged individually within
        a single connection (one transaction per batch).

        Returns:
            (stored_count, failed_count)
        """
        stored = 0
        failed = 0

        for record in records:
            try:
                self.merge_content(record)
                stored += 1
            except Exception as e:
                logger.error(
                    "merge_content failed | log_id=%s | error=%s",
                    record.log_id, e,
                )
                failed += 1

        return stored, failed

    # ------------------------------------------------------------------ #
    # Read — Semantic Similarity Search
    # ------------------------------------------------------------------ #

    def semantic_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> list[SearchResult]:
        """
        Perform ANN cosine similarity search against SS_ERROR_LOGS.

        Args:
            query_vector:   3072-dim embedding of the query text.
            top_k:          Max results to return (Oracle FETCH FIRST N).
            min_similarity: Filter out results below this threshold.

        Returns:
            List of SearchResult sorted by similarity descending.
        """
        # Oracle AI DB: VECTOR_DISTANCE() with COSINE returns a distance (0=same).
        # We convert to similarity = 1 - distance for intuitive scoring.
        sql = """
            SELECT
                LOG_ID,
                FLOW_CODE,
                ACTION_NAME,
                ERROR_LEVEL,
                ERROR_CODE,
                SEMANTIC_TEXT,
                EVENT_TIME,
                1 - VECTOR_DISTANCE(VECTOR, :query_vec, COSINE) AS SIMILARITY
            FROM SS_ERROR_LOGS
            ORDER BY VECTOR_DISTANCE(VECTOR, :query_vec, COSINE)
            FETCH FIRST :top_k ROWS ONLY
        """

        query_array = array.array("f", query_vector)

        start = time.perf_counter()

        with self._pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {
                    "query_vec": query_array,
                    "top_k":     top_k,
                })
                rows = cur.fetchall()

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            "semantic_search complete | rows=%d | latency_ms=%.1f",
            len(rows), elapsed_ms,
        )

        def _read(val) -> str:
            """Oracle CLOB columns come back as LOB objects — read to string."""
            if val is None:
                return ""
            if hasattr(val, "read"):
                return val.read()
            return str(val)

        results = []
        for row in rows:
            log_id, flow_code, action_name, error_level, \
                error_code, semantic_text, event_time, similarity = row

            sim_float = float(similarity) if similarity is not None else 0.0

            if sim_float < min_similarity:
                continue

            results.append(SearchResult(
                log_id=log_id,
                similarity=sim_float,
                flow_code=flow_code,
                action_name=action_name,
                error_level=error_level,
                error_code=error_code,
                semantic_text=_read(semantic_text),
                event_time=event_time,
            ))

        return results

    # ------------------------------------------------------------------ #
    # Utility
    # ------------------------------------------------------------------ #

    def get_store_stats(self) -> StoreStats:
        """Return basic statistics about the SS_ERROR_LOGS store."""
        sql = """
            SELECT
                COUNT(*)        AS total,
                MIN(EVENT_TIME) AS oldest,
                MAX(EVENT_TIME) AS newest
            FROM SS_ERROR_LOGS
        """
        with self._pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                total, oldest, newest = cur.fetchone()

        return StoreStats(
            store_name=STORE_NAME,
            total_records=int(total),
            oldest_event=oldest,
            newest_event=newest,
        )