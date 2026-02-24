"""
models.py
---------
Pydantic models for OIC-LogLens REST API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


# ── REQUEST MODELS ─────────────────────────────────────────────────────────────

class IngestFileRequest(BaseModel):
    """Request model for POST /ingest/file"""
    file_path: str = Field(..., description="Absolute path to the log file on the server")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/path/to/flow-logs/01_flow-log.json"
            }
        }


# ── RESPONSE MODELS ────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    """Response model for all ingest endpoints"""
    log_id: str = Field(..., description="UUID of the ingested log record")
    jira_id: str = Field(..., description="Jira issue ID (extracted or generated)")
    status: str = Field(..., description="success or error")
    message: str = Field(..., description="Human readable message")

    class Config:
        json_schema_extra = {
            "example": {
                "log_id": "9f9da348-963c-41fe-8c61-3ec23dbb3c13",
                "jira_id": "https://promptlyai.atlassian.net/browse/OLL-4FF0674A",
                "status": "success",
                "message": "Log ingested successfully"
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = Field(default="error", description="Always 'error'")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "File not found",
                "detail": "/path/to/log.json does not exist"
            }
        }


# ── SEARCH MODELS ──────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    """Request model for POST /search"""
    log_content: str = Field(..., description="Raw log as JSON string (array format)")

    class Config:
        json_schema_extra = {
            "example": {
                "log_content": "[{...raw log json array...}]"
            }
        }


class KGInsights(BaseModel):
    """Knowledge Graph insights for a search match"""
    root_cause: Optional[str] = Field(None, description="Root cause extracted from Knowledge Graph")
    endpoints: List[str] = Field(default_factory=list, description="Endpoints associated with this error")
    recurrence_count: int = Field(default=0, description="Number of times this flow+error combination has occurred")
    related_tickets: List[str] = Field(default_factory=list, description="Related Jira ticket IDs from Knowledge Graph")


class SearchMatch(BaseModel):
    """Single search result match"""
    jira_id: str = Field(..., description="Jira issue ID")
    similarity_score: float = Field(..., description="Similarity percentage (0-100)")
    flow_code: str = Field(..., description="OIC flow code")
    trigger_type: Optional[str] = Field(None, description="Trigger type (rest/soap/scheduled)")
    error_code: Optional[str] = Field(None, description="Error code")
    error_summary: str = Field(..., description="Error summary (first 150 chars)")
    rank: Optional[int] = Field(None, description="LLM re-ranking position")
    classification: Optional[str] = Field(None, description="EXACT_DUPLICATE | SIMILAR_ROOT_CAUSE | RELATED | NOT_RELATED")
    confidence: Optional[int] = Field(None, description="LLM confidence score (0-100)")
    reasoning: Optional[str] = Field(None, description="LLM explanation of classification")
    kg_insights: Optional[KGInsights] = Field(None, description="Knowledge Graph insights — root cause, recurrence, related tickets")


class SearchResponse(BaseModel):
    """Response model for POST /search"""
    status: str = Field(..., description="success or error")
    message: str = Field(..., description="Human readable message")
    matches: list[SearchMatch] = Field(..., description="List of similar logs (Top-N)")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Found 5 similar logs",
                "matches": [
                    {
                        "jira_id": "https://promptlyai.atlassian.net/browse/OLL-4FF0674A",
                        "similarity_score": 100.0,
                        "flow_code": "RH_NAVAN_DAILY_INTEGR_SCHEDU",
                        "trigger_type": "scheduled",
                        "error_code": "Execution failed",
                        "error_summary": "oracle.cloud.connector.api.CloudInvocationException",
                        "rank": 1,
                        "classification": "EXACT_DUPLICATE",
                        "confidence": 100,
                        "reasoning": "Same flow, same error, same root cause",
                        "kg_insights": {
                            "root_cause": "Not Found",
                            "endpoints": ["InvokeIntegration"],
                            "recurrence_count": 1,
                            "related_tickets": []
                        }
                    }
                ]
            }
        }


class IngestURLRequest(BaseModel):
    """Request model for POST /ingest/url"""
    url: str = Field(..., description="HTTP/HTTPS URL pointing to a log file")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/logs/error.json"
            }
        }


class IngestRawRequest(BaseModel):
    """Request model for POST /ingest/raw"""
    log_content: str = Field(..., description="Raw log as JSON string (array format)")

    class Config:
        json_schema_extra = {
            "example": {
                "log_content": "[{...raw log json array...}]"
            }
        }


class IngestDatabaseRequest(BaseModel):
    """Request model for POST /ingest/database"""
    connection_string: str = Field(..., description="Database connection string")
    query: str = Field(..., description="SQL query to fetch the log")

    class Config:
        json_schema_extra = {
            "example": {
                "connection_string": "oracle://user:pass@host:port/service",
                "query": "SELECT log_json FROM logs WHERE id = 123"
            }
        }


class BatchJobAccepted(BaseModel):
    """Response model for POST /ingest/database — returned immediately"""
    job_id: str = Field(..., description="Unique job ID to poll for status")
    status: str = Field(default="accepted", description="Always 'accepted'")
    message: str = Field(..., description="Human readable message")
    total_logs: int = Field(..., description="Total logs queued for processing")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "accepted",
                "message": "16 logs queued for background processing",
                "total_logs": 16
            }
        }


class BatchJobStatus(BaseModel):
    """Response model for GET /ingest/status/{job_id}"""
    job_id: str = Field(..., description="Job ID")
    status: str = Field(..., description="pending | in_progress | completed | failed")
    total_logs: int = Field(..., description="Total logs to process")
    processed: int = Field(..., description="Logs processed so far")
    successful: int = Field(..., description="Successfully ingested")
    duplicates: int = Field(..., description="Duplicates skipped")
    failed: int = Field(..., description="Failed logs")
    current_log: Optional[int] = Field(None, description="Index of log currently being processed")
    results: list = Field(default_factory=list, description="Individual results so far")
    error: Optional[str] = Field(None, description="Error message if job failed entirely")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "in_progress",
                "total_logs": 16,
                "processed": 5,
                "successful": 4,
                "duplicates": 1,
                "failed": 0,
                "current_log": 6,
                "results": []
            }
        }


class BatchIngestResponse(BaseModel):
    """Response model for batch ingestion"""
    status: str = Field(..., description="success or partial_success or error")
    message: str = Field(..., description="Human readable message")
    total_logs: int = Field(..., description="Total logs attempted")
    successful: int = Field(..., description="Successfully ingested logs")
    failed: int = Field(..., description="Failed logs")
    duplicates: int = Field(..., description="Duplicate logs")
    results: list[IngestResponse] = Field(default_factory=list, description="Individual results")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Batch ingestion completed",
                "total_logs": 5,
                "successful": 4,
                "failed": 0,
                "duplicates": 1,
                "results": []
            }
        }
