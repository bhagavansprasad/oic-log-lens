-- ============================================================
-- OIC-LogLens — Knowledge Graph Schema
-- File     : kg_schema.sql
-- Tables   : OIC_KB_GRAPH_NODES, OIC_KB_GRAPH_EDGES
-- Graph    : OIC_KB_GRAPH
-- User     : EA_APP | DB: FREEPDB1
-- Version  : 1.2
-- ============================================================
-- NOTE: Run this AFTER oic_kb_schema.sql
--       Safe to re-run — drops in correct order before recreating.
--
-- DROP ORDER (critical — FK constraint safe):
--   1. Property Graph first
--   2. Edges table second  (references Nodes via FK)
--   3. Nodes table last
-- ============================================================


-- ── Step 1: Drop Property Graph ──────────────────────────────

BEGIN
    EXECUTE IMMEDIATE 'DROP PROPERTY GRAPH OIC_KB_GRAPH';
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/

-- ── Step 2: Drop Edges (FK references Nodes) ─────────────────

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE OIC_KB_GRAPH_EDGES';
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/

-- ── Step 3: Drop Nodes ────────────────────────────────────────

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE OIC_KB_GRAPH_NODES';
EXCEPTION
    WHEN OTHERS THEN NULL;
END;
/

-- ── Step 4: Create Nodes Table ───────────────────────────────

CREATE TABLE OIC_KB_GRAPH_NODES (
    NODE_ID      VARCHAR2(200)  PRIMARY KEY,
    NODE_TYPE    VARCHAR2(50)   NOT NULL,
    NODE_VALUE   VARCHAR2(500)  NOT NULL,
    PROPERTIES   CLOB,
    CREATED_AT   TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE OIC_KB_GRAPH_NODES IS
    'OIC Knowledge Base: Stores unique graph entities (FlowCode, Error, Endpoint, RootCause, JiraTicket, Resolution).';

COMMENT ON COLUMN OIC_KB_GRAPH_NODES.NODE_ID IS
    'Composite key in format NodeType:NodeValue. e.g. FlowCode:RH_NAVAN_DAILY.';

COMMENT ON COLUMN OIC_KB_GRAPH_NODES.NODE_TYPE IS
    'Entity type. Values: FlowCode | Error | Endpoint | RootCause | JiraTicket | Resolution.';

COMMENT ON COLUMN OIC_KB_GRAPH_NODES.NODE_VALUE IS
    'The actual entity value. e.g. RH_NAVAN_DAILY_INTEGR, CloudInvocationException.';

COMMENT ON COLUMN OIC_KB_GRAPH_NODES.PROPERTIES IS
    'Optional JSON blob. e.g. {"trigger_type": "scheduled"} for FlowCode nodes.';

-- ── Step 5: Create Edges Table ───────────────────────────────
-- FK constraints added via ALTER TABLE (SQLPlus compatible)

CREATE TABLE OIC_KB_GRAPH_EDGES (
    EDGE_ID      VARCHAR2(100)  PRIMARY KEY,
    FROM_NODE    VARCHAR2(200)  NOT NULL,
    TO_NODE      VARCHAR2(200)  NOT NULL,
    EDGE_TYPE    VARCHAR2(100)  NOT NULL,
    PROPERTIES   CLOB,
    CREATED_AT   TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE OIC_KB_GRAPH_EDGES
    ADD CONSTRAINT OIC_KB_EDGES_FROM_FK
    FOREIGN KEY (FROM_NODE) REFERENCES OIC_KB_GRAPH_NODES(NODE_ID);

ALTER TABLE OIC_KB_GRAPH_EDGES
    ADD CONSTRAINT OIC_KB_EDGES_TO_FK
    FOREIGN KEY (TO_NODE) REFERENCES OIC_KB_GRAPH_NODES(NODE_ID);

COMMENT ON TABLE OIC_KB_GRAPH_EDGES IS
    'OIC Knowledge Base: Stores directional relationships between graph entities.';

COMMENT ON COLUMN OIC_KB_GRAPH_EDGES.EDGE_ID IS
    'UUID. Primary key for the edge.';

COMMENT ON COLUMN OIC_KB_GRAPH_EDGES.EDGE_TYPE IS
    'Relationship type. Values: HAD_ERROR | ON_ENDPOINT | HAS_ROOT_CAUSE | LOGGED_IN | DUPLICATE_OF | RELATED_TO | FIXED_BY.';

COMMENT ON COLUMN OIC_KB_GRAPH_EDGES.PROPERTIES IS
    'Optional JSON blob. e.g. {"confidence": 95, "classified_by": "llm"} for DUPLICATE_OF edges.';

-- ── Step 6: Create Indexes ────────────────────────────────────

CREATE INDEX OIC_KB_NODES_TYPE_IDX  ON OIC_KB_GRAPH_NODES(NODE_TYPE);
CREATE INDEX OIC_KB_NODES_VALUE_IDX ON OIC_KB_GRAPH_NODES(NODE_VALUE);
CREATE INDEX OIC_KB_EDGES_FROM_IDX  ON OIC_KB_GRAPH_EDGES(FROM_NODE);
CREATE INDEX OIC_KB_EDGES_TO_IDX    ON OIC_KB_GRAPH_EDGES(TO_NODE);
CREATE INDEX OIC_KB_EDGES_TYPE_IDX  ON OIC_KB_GRAPH_EDGES(EDGE_TYPE);

-- ── Step 7: Create Property Graph ────────────────────────────

CREATE PROPERTY GRAPH OIC_KB_GRAPH
    VERTEX TABLES (
        OIC_KB_GRAPH_NODES
            KEY (NODE_ID)
            LABEL node
            PROPERTIES (NODE_TYPE, NODE_VALUE, PROPERTIES, CREATED_AT)
    )
    EDGE TABLES (
        OIC_KB_GRAPH_EDGES
            KEY (EDGE_ID)
            SOURCE KEY      (FROM_NODE) REFERENCES OIC_KB_GRAPH_NODES (NODE_ID)
            DESTINATION KEY (TO_NODE)   REFERENCES OIC_KB_GRAPH_NODES (NODE_ID)
            LABEL edge
            PROPERTIES (EDGE_TYPE, PROPERTIES, CREATED_AT)
    );

-- ── Step 8: Verify ────────────────────────────────────────────

SELECT TABLE_NAME FROM USER_TABLES
WHERE TABLE_NAME IN ('OIC_KB_GRAPH_NODES', 'OIC_KB_GRAPH_EDGES')
ORDER BY TABLE_NAME;

SELECT GRAPH_NAME FROM USER_PROPERTY_GRAPHS
WHERE GRAPH_NAME = 'OIC_KB_GRAPH';

SELECT INDEX_NAME FROM USER_INDEXES
WHERE TABLE_NAME IN ('OIC_KB_GRAPH_NODES', 'OIC_KB_GRAPH_EDGES')
ORDER BY TABLE_NAME, INDEX_NAME;
