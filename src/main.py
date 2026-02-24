"""
main.py
-------
FastAPI REST API for OIC-LogLens.
Provides endpoints for log ingestion and deduplication search.
"""

import time
import uuid
from typing import Dict

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from models import (IngestFileRequest, IngestURLRequest, IngestRawRequest,
                     IngestDatabaseRequest, IngestResponse, BatchIngestResponse,
                     BatchJobAccepted, BatchJobStatus,
                     SearchRequest, SearchResponse)
from ingestion_service import (load_from_file, load_from_url, load_from_raw_text, 
                                     load_from_database, ingest_log)
from search_service import search_log
from config import logger

# ── FastAPI App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OIC-LogLens API",
    description="AI-Powered Error Resolution Engine for Oracle Integration Cloud",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── In-Memory Job Store ───────────────────────────────────────────────────────
# Stores background job state keyed by job_id.
# In production this should be replaced with a persistent store (Redis, DB).

_jobs: Dict[str, dict] = {}


# ── CORS Middleware ────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "OIC-LogLens"}


# ── Ingest Endpoints ───────────────────────────────────────────────────────────

@app.post(
    "/ingest/file",
    response_model=IngestResponse,
    tags=["Ingestion"],
    summary="Ingest log from file path"
)
def ingest_file(request: IngestFileRequest):
    """
    Ingest an OIC log from a file path on the server.
    
    The pipeline:
    1. Read file from provided path
    2. Normalize log using Gemini LLM
    3. Generate embedding vector
    4. Store in Oracle 26ai Vector Database
    
    Returns the LOG_ID of the ingested record.
    """
    # Load raw log from file
    raw_log = load_from_file(request.file_path)
    
    # Run ingestion pipeline
    log_id, jira_id = ingest_log(raw_log)
    
    return IngestResponse(
        log_id=log_id,
        jira_id=jira_id,
        status="success",
        message="Log ingested successfully"
    )



@app.post(
    "/ingest/url",
    response_model=IngestResponse,
    tags=["Ingestion"],
    summary="Ingest log from URL"
)
def ingest_url(request: IngestURLRequest):
    """
    Ingest an OIC log from a URL.
    
    Fetches the log file from the provided HTTP/HTTPS URL,
    then runs the standard ingestion pipeline.
    """
    # Load raw log from URL
    raw_log = load_from_url(request.url)
    
    # Run ingestion pipeline
    log_id, jira_id = ingest_log(raw_log)
    
    return IngestResponse(
        log_id=log_id,
        jira_id=jira_id,
        status="success",
        message="Log ingested successfully"
    )


@app.post(
    "/ingest/raw",
    response_model=IngestResponse,
    tags=["Ingestion"],
    summary="Ingest log from raw text"
)
def ingest_raw(request: IngestRawRequest):
    """
    Ingest an OIC log from raw JSON text.
    
    Accepts the log content as a JSON string,
    then runs the standard ingestion pipeline.
    """
    # Load raw log from text
    raw_log = load_from_raw_text(request.log_content)
    
    # Run ingestion pipeline
    log_id, jira_id = ingest_log(raw_log)
    
    return IngestResponse(
        log_id=log_id,
        jira_id=jira_id,
        status="success",
        message="Log ingested successfully"
    )


@app.post(
    "/ingest/database",
    response_model=BatchJobAccepted,
    tags=["Ingestion"],
    summary="Ingest logs from database (background batch)"
)
def ingest_database(request: IngestDatabaseRequest, background_tasks: BackgroundTasks):
    """
    Ingest OIC logs from a database query — runs in the background.

    Returns immediately with a job_id.
    Poll GET /ingest/status/{job_id} to track progress.

    Pipeline per log:
    1. Normalize using Gemini LLM
    2. Generate embedding vector
    3. Store in Oracle 26ai Vector Database
    4. Write to Knowledge Graph
    """
    from fastapi import HTTPException

    # Load raw logs from database upfront (fast — no LLM calls)
    raw_logs = load_from_database(request.connection_string, request.query)
    total = len(raw_logs)

    # Create job entry
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status":      "pending",
        "total_logs":  total,
        "processed":   0,
        "successful":  0,
        "duplicates":  0,
        "failed":      0,
        "current_log": None,
        "results":     [],
        "error":       None
    }

    logger.info(f"Job {job_id} created | {total} logs queued")

    # Queue background processing
    background_tasks.add_task(_process_batch, job_id, raw_logs)

    return BatchJobAccepted(
        job_id=job_id,
        status="accepted",
        message=f"{total} logs queued for background processing",
        total_logs=total
    )


def _process_batch(job_id: str, raw_logs: list):
    """
    Background task — processes each log sequentially with sleep between calls.
    Updates _jobs[job_id] in place so the status endpoint can poll it.
    """
    from fastapi import HTTPException

    BATCH_SLEEP_SECONDS = 15  # gap between logs to avoid LLM rate limits

    job = _jobs[job_id]
    job["status"] = "in_progress"
    total = len(raw_logs)

    for i, raw_log in enumerate(raw_logs, 1):
        job["current_log"] = i
        logger.info(f"Job {job_id} | Processing log {i}/{total}")

        try:
            log_id, jira_id = ingest_log(raw_log)

            job["results"].append({
                "log_index": i,
                "log_id":    log_id,
                "jira_id":   jira_id,
                "status":    "success",
                "message":   f"Log {i} ingested successfully"
            })
            job["successful"] += 1

        except HTTPException as e:
            if e.status_code == 409:
                job["duplicates"] += 1
                job["results"].append({
                    "log_index": i,
                    "log_id":    "",
                    "jira_id":   "",
                    "status":    "duplicate",
                    "message":   f"Log {i}: Duplicate detected"
                })
            else:
                job["failed"] += 1
                job["results"].append({
                    "log_index": i,
                    "log_id":    "",
                    "jira_id":   "",
                    "status":    "error",
                    "message":   f"Log {i}: {e.detail}"
                })

        except Exception as e:
            job["failed"] += 1
            job["results"].append({
                "log_index": i,
                "log_id":    "",
                "jira_id":   "",
                "status":    "error",
                "message":   f"Log {i}: {str(e)}"
            })

        job["processed"] = i

        # Sleep between logs — skip after last
        if i < total:
            logger.info(f"Job {job_id} | Sleeping {BATCH_SLEEP_SECONDS}s (rate limit buffer)...")
            time.sleep(BATCH_SLEEP_SECONDS)

    # Mark job complete
    if job["failed"] == 0 and job["duplicates"] == 0:
        job["status"] = "completed"
    elif job["successful"] > 0:
        job["status"] = "completed"
    else:
        job["status"] = "failed"

    job["current_log"] = None
    logger.info(f"Job {job_id} | Done | success={job['successful']} duplicates={job['duplicates']} failed={job['failed']}")


# ── Job Status Endpoint ────────────────────────────────────────────────────────

@app.get(
    "/ingest/status/{job_id}",
    response_model=BatchJobStatus,
    tags=["Ingestion"],
    summary="Poll background ingest job status"
)
def get_ingest_status(job_id: str):
    """
    Poll the status of a background database ingest job.

    Status values:
    - pending     : job accepted, not started yet
    - in_progress : actively processing logs
    - completed   : all logs processed (check successful/failed counts)
    - failed      : job failed entirely before processing any logs
    """
    from fastapi import HTTPException, status as http_status

    if job_id not in _jobs:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    job = _jobs[job_id]

    return BatchJobStatus(
        job_id=job_id,
        status=job["status"],
        total_logs=job["total_logs"],
        processed=job["processed"],
        successful=job["successful"],
        duplicates=job["duplicates"],
        failed=job["failed"],
        current_log=job["current_log"],
        results=job["results"],
        error=job["error"]
    )


# ── Search Endpoint ────────────────────────────────────────────────────────────

@app.post(
    "/search",
    response_model=SearchResponse,
    tags=["Search"],
    summary="Search for duplicate/similar logs"
)
def search_duplicate(request: SearchRequest):
    """
    Search for duplicate or similar logs using semantic similarity.
    
    The pipeline:
    1. Normalize query log using Gemini LLM
    2. Generate embedding vector
    3. Vector similarity search in Oracle 26ai
    4. Return Top-5 most similar logs
    
    Returns matches with Jira IDs, similarity scores, and metadata.
    """
    # Load raw log from text
    raw_log = load_from_raw_text(request.log_content)
    
    # Run search pipeline
    matches = search_log(raw_log, top_n=5)
    
    return SearchResponse(
        status="success",
        message=f"Found {len(matches)} similar logs",
        matches=matches
    )

# ── Run Server ─────────────────────────────────────────────────────────────────


@app.get(
    "/stats/cache",
    tags=["System"],
    summary="Get cache statistics"
)
def get_cache_statistics():
    """
    Get performance cache statistics.
    
    Shows hit rates, sizes, and efficiency metrics
    for normalized logs, embeddings, and search results.
    """
    from cache import get_cache_stats
    return get_cache_stats()


@app.post(
    "/admin/clear-cache",
    tags=["System"],
    summary="Clear all caches"
)
def clear_caches():
    """
    Clear all performance caches.
    
    Use this if you need to force fresh results
    or after updating the normalization/embedding logic.
    """
    from cache import clear_all_caches
    clear_all_caches()
    return {"status": "success", "message": "All caches cleared"}


# ── SHUTDOWN HANDLER ───────────────────────────────────────────────────────────

@app.on_event("shutdown")
def shutdown_event():
    """Clean up resources on shutdown"""
    from db import close_connection_pool
    close_connection_pool()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
