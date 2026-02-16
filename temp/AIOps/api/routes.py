# =============================================================
# AIOps Platform — API Routes
#
# POST /logs/ingest  — bulk log ingestion
# POST /logs/match   — semantic error matching
#   Option A: JSON body { "error_text": "..." }
#   Option B: JSON body { "log": {...} }
#   Option C: multipart file upload
# =============================================================

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from api.dependencies import get_service
from api.models import IngestResponse, MatchRequest, MatchResponse, TopMatch
from services.aiops_service import AIOpsService, MatchDecision

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])


# ------------------------------------------------------------------ #
# Helper — convert MatchDecision → MatchResponse
# ------------------------------------------------------------------ #

def _to_match_response(decision: MatchDecision) -> MatchResponse:
    def _to_top_match(r) -> TopMatch:
        return TopMatch(
            log_id        = r.log_id,
            similarity    = round(r.similarity, 4),
            flow_code     = r.flow_code,
            action_name   = r.action_name,
            error_level   = r.error_level,
            error_code    = r.error_code,
            semantic_text = r.semantic_text,
            event_time    = r.event_time,
        )

    return MatchResponse(
        known         = decision.status == "known",
        status        = decision.status,
        similarity    = round(decision.similarity, 4),
        semantic_text = decision.semantic_text,
        top_match     = _to_top_match(decision.top_match) if decision.top_match else None,
        alternatives  = [_to_top_match(r) for r in decision.alternatives],
        duration_ms   = round(decision.duration_ms, 1),
    )


# ------------------------------------------------------------------ #
# POST /logs/ingest
# ------------------------------------------------------------------ #

@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk ingest error logs",
    description="Accepts a JSON array of log objects, embeds each and stores in Oracle.",
)
async def ingest_logs(
    logs: list[dict[str, Any]],
    service: AIOpsService = Depends(get_service),
) -> IngestResponse:
    """
    Bulk ingest a list of raw log JSON objects.

    Each log is processed:
    1. Semantic text extracted (excluded fields stripped)
    2. Gemini embedding generated
    3. Upserted into Oracle via MERGE
    """
    if not logs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body must be a non-empty JSON array of log objects.",
        )

    logger.info("POST /logs/ingest | count=%d", len(logs))

    result = service.ingest_logs(logs)

    logger.info(
        "Ingestion complete | processed=%d stored=%d failed=%d",
        result.processed, result.stored, result.failed,
    )

    return IngestResponse(
        processed    = result.processed,
        stored       = result.stored,
        failed       = result.failed,
        duration_ms  = round(result.duration_ms, 1),
    )


# ------------------------------------------------------------------ #
# POST /logs/match — Option A & B (JSON body)
# ------------------------------------------------------------------ #

@router.post(
    "/match",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic error match",
    description="Match a new error against historical logs using vector similarity.",
)
async def match_error(
    request: MatchRequest,
    service: AIOpsService = Depends(get_service),
) -> MatchResponse:
    """
    Match a new error semantically against stored logs.

    Option A — raw text:
        { "error_text": "flow: X\\nstep: Y\\nerror: Z" }

    Option B — log dict:
        { "log": { "flow_code": "...", "error_message": "..." } }
    """
    if not request.error_text and not request.log:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either 'error_text' or 'log' in request body.",
        )

    logger.info(
        "POST /logs/match | input=%s",
        "error_text" if request.error_text else "log_dict",
    )

    try:
        decision = service.match_error(
            error_text = request.error_text,
            log        = request.log,
            top_k      = request.top_k,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return _to_match_response(decision)


# ------------------------------------------------------------------ #
# POST /logs/match/file — Option C (file upload)
# ------------------------------------------------------------------ #

@router.post(
    "/match/file",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic error match via file upload",
    description="Upload a JSON log file (.json) to match against historical logs.",
)
async def match_error_file(
    file: UploadFile = File(..., description="JSON log file"),
    top_k: int = 5,
    service: AIOpsService = Depends(get_service),
) -> MatchResponse:
    """
    Match via uploaded JSON file (multipart/form-data).

    The file must contain either:
    - A single log object: { "flow_code": "...", ... }
    - A JSON array with one log: [{ ... }]
    """
    # Validate file type
    if not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only .json files are supported.",
        )

    # Read and parse
    try:
        content = await file.read()
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid JSON in uploaded file: {e}",
        )

    # Accept single object or array with one item
    if isinstance(data, list):
        if len(data) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Uploaded JSON array is empty.",
            )
        log = data[0]
    elif isinstance(data, dict):
        log = data
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must contain a JSON object or array.",
        )

    logger.info("POST /logs/match/file | filename=%s", file.filename)

    try:
        decision = service.match_error(log=log, top_k=top_k)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return _to_match_response(decision)
