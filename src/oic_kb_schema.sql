-- ============================================================
-- OIC-LogLens — Vector Table Schema
-- File     : oll_schema.sql
-- Table    : OIC_KB_ISSUE  (renamed from OLL_LOGS)
-- User     : EA_APP | DB: FREEPDB1
-- Version  : 1.1
-- ============================================================
-- NAMING CONVENTION (consistent across entire project):
--   OIC_KB_             → prefix for all OIC Knowledge Base objects
--   OIC_KB_ISSUE        → this file — vector table for ingested logs
--   OIC_KB_GRAPH_NODES  → knowledge graph nodes  (see kg_schema.sql)
--   OIC_KB_GRAPH_EDGES  → knowledge graph edges  (see kg_schema.sql)
--   OIC_KB_GRAPH        → property graph view    (see kg_schema.sql)
--
-- RUN ORDER:
--   1. oll_schema.sql   ← this file
--   2. kg_schema.sql    ← knowledge graph
-- ============================================================


-- ── Drop existing objects safely ─────────────────────────────

BEGIN
    EXECUTE IMMEDIATE 'DROP INDEX OIC_KB_ISSUE_VIDX';
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE OIC_KB_ISSUE';
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/


-- ── Main Table ───────────────────────────────────────────────

CREATE TABLE OIC_KB_ISSUE (
    LOG_ID            VARCHAR2(100)    PRIMARY KEY,
    LOG_HASH          VARCHAR2(64)     NOT NULL,
    JIRA_ID           VARCHAR2(100),
    LOG_TYPE          VARCHAR2(20),
    EVENT_TIME        TIMESTAMP,
    FLOW_CODE         VARCHAR2(200),
    TRIGGER_TYPE      VARCHAR2(50),
    ENDPOINT_NAME     VARCHAR2(200),
    ERROR_CODE        VARCHAR2(100),
    ERROR_SUMMARY     CLOB,
    SEMANTIC_TEXT     CLOB,
    RAW_JSON          CLOB,
    NORMALIZED_JSON   CLOB,
    VECTOR            VECTOR(3072, FLOAT32)
);

ALTER TABLE OIC_KB_ISSUE ADD CONSTRAINT OIC_KB_ISSUE_HASH_UQ UNIQUE (LOG_HASH);


-- ── Column Comments ───────────────────────────────────────────

COMMENT ON TABLE OIC_KB_ISSUE IS
    'OIC Knowledge Base: Stores ingested OIC flow logs with normalized metadata, raw content, and vector embeddings for semantic deduplication.';

COMMENT ON COLUMN OIC_KB_ISSUE.LOG_ID IS
    'Primary key. UUID generated at insert time. Uniquely identifies each ingested log record.';

COMMENT ON COLUMN OIC_KB_ISSUE.LOG_HASH IS
    'SHA256 hash of the raw log JSON. Used to prevent duplicate log ingestion. Same raw log will always produce the same hash.';

COMMENT ON COLUMN OIC_KB_ISSUE.JIRA_ID IS
    'Associated Jira issue ID for this log. Used as the deduplication reference returned during similarity search.';

COMMENT ON COLUMN OIC_KB_ISSUE.LOG_TYPE IS
    'Classification of the log. Values: error | informational. Populated from normalized_json.log_type.';

COMMENT ON COLUMN OIC_KB_ISSUE.EVENT_TIME IS
    'Timestamp of the flow execution event. Populated from normalized_json.flow.timestamp (converted from epoch ms).';

COMMENT ON COLUMN OIC_KB_ISSUE.FLOW_CODE IS
    'OIC integration flow code that generated this log. Populated from normalized_json.flow.code.';

COMMENT ON COLUMN OIC_KB_ISSUE.TRIGGER_TYPE IS
    'How the flow was triggered. Values: rest | soap | scheduled. Populated from normalized_json.flow.trigger_type.';

COMMENT ON COLUMN OIC_KB_ISSUE.ENDPOINT_NAME IS
    'Name of the endpoint where the error occurred. Populated from normalized_json.error.endpoint_name.';

COMMENT ON COLUMN OIC_KB_ISSUE.ERROR_CODE IS
    'Short error code from the log. Examples: Execution failed, 401, 404, 503. Populated from normalized_json.error.code.';

COMMENT ON COLUMN OIC_KB_ISSUE.ERROR_SUMMARY IS
    'One-line human readable error summary. Populated from normalized_json.error.summary.';

COMMENT ON COLUMN OIC_KB_ISSUE.SEMANTIC_TEXT IS
    'Concatenated text string built from key normalized fields. This is the input used to generate the vector embedding.';

COMMENT ON COLUMN OIC_KB_ISSUE.RAW_JSON IS
    'Original raw OIC log file content as-is. Stored for traceability and reprocessing.';

COMMENT ON COLUMN OIC_KB_ISSUE.NORMALIZED_JSON IS
    'Full normalized log JSON produced by the LLM normalization pipeline. Stored for audit and future use.';

COMMENT ON COLUMN OIC_KB_ISSUE.VECTOR IS
    'Vector embedding (3072 dimensions, FLOAT32) generated from SEMANTIC_TEXT using Gemini gemini-embedding-001. Used for cosine similarity search.';


-- ── Vector Index (HNSW Cosine) ───────────────────────────────

CREATE VECTOR INDEX OIC_KB_ISSUE_VIDX
ON OIC_KB_ISSUE(VECTOR)
ORGANIZATION INMEMORY GRAPH
DISTANCE COSINE
WITH TARGET ACCURACY 95;


-- ── Metadata Indexes ─────────────────────────────────────────

CREATE INDEX OIC_KB_ISSUE_FLOW_IDX  ON OIC_KB_ISSUE(FLOW_CODE);
CREATE INDEX OIC_KB_ISSUE_JIRA_IDX  ON OIC_KB_ISSUE(JIRA_ID);
CREATE INDEX OIC_KB_ISSUE_TIME_IDX  ON OIC_KB_ISSUE(EVENT_TIME);
CREATE INDEX OIC_KB_ISSUE_TYPE_IDX  ON OIC_KB_ISSUE(LOG_TYPE);


-- ── Verify ───────────────────────────────────────────────────

SELECT 'TABLE CREATED OK' AS STATUS
FROM USER_TABLES
WHERE TABLE_NAME = 'OIC_KB_ISSUE';

SELECT INDEX_NAME, INDEX_TYPE
FROM USER_INDEXES
WHERE TABLE_NAME = 'OIC_KB_ISSUE';

SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH
FROM USER_TAB_COLUMNS
WHERE TABLE_NAME = 'OIC_KB_ISSUE'
ORDER BY COLUMN_ID;
