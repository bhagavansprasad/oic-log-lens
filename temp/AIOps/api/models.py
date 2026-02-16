# =============================================================
# AIOps Platform — API Request / Response Models
# Pydantic models for all FastAPI endpoints
# =============================================================

from __future__ import annotations
from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# Ingestion — POST /logs/ingest
# ------------------------------------------------------------------ #

class IngestResponse(BaseModel):
    processed: int = Field(description="Total logs received")
    stored:    int = Field(description="Successfully stored in Oracle")
    failed:    int = Field(description="Failed to process")
    duration_ms: float = Field(description="Total processing time in ms")


# ------------------------------------------------------------------ #
# Match — POST /logs/match
# ------------------------------------------------------------------ #

class MatchRequest(BaseModel):
    """
    Option A: raw error text
    Option B: full log dict
    (File upload is handled separately via multipart)
    """
    error_text: str | None = Field(
        default=None,
        description="Raw semantic error text to match against"
    )
    log: dict[str, Any] | None = Field(
        default=None,
        description="Full log JSON object to extract semantic text from"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max number of candidates to retrieve"
    )


class TopMatch(BaseModel):
    log_id:     str
    similarity: float
    flow_code:  str | None
    action_name: str | None
    error_level: str | None
    error_code:  str | None
    semantic_text: str
    first_seen:  datetime | None = Field(alias="event_time")

    model_config = {"populate_by_name": True}


class MatchResponse(BaseModel):
    known:      bool  = Field(description="True if similarity > threshold_known")
    status:     str   = Field(description="known | related | new | empty")
    similarity: float = Field(description="Top match cosine similarity (0-1)")
    semantic_text: str = Field(description="Text that was embedded for matching")
    top_match:  TopMatch | None
    alternatives: list[TopMatch]
    duration_ms: float
