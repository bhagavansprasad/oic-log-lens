"""
graph_service.py
----------------
Knowledge Graph service for OIC-LogLens.
Reads and writes the OIC_KB_GRAPH (Oracle Property Graph).

Two primary responsibilities:
  1. add_log_to_graph()      — called during ingestion, writes nodes + edges
  2. enrich_search_results() — called during search, adds KG insights to matches

Node Types : FlowCode | Error | Endpoint | RootCause | JiraTicket
Edge Types : HAD_ERROR | ON_ENDPOINT | HAS_ROOT_CAUSE | LOGGED_IN
             DUPLICATE_OF | RELATED_TO | FIXED_BY
"""

import json
import uuid
import oracledb
from config import logger

# ── CONNECTION CONFIG ──────────────────────────────────────────────────────────

DB_USER     = "EA_APP"
DB_PASSWORD = "jnjnuh"
DB_DSN      = "localhost/FREEPDB1"


# ── CONNECTION ─────────────────────────────────────────────────────────────────

def get_connection() -> oracledb.Connection:
    conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
    return conn


# ── SQL ────────────────────────────────────────────────────────────────────────

UPSERT_NODE_SQL = """
MERGE INTO OIC_KB_GRAPH_NODES tgt
USING (SELECT :node_id AS NODE_ID FROM DUAL) src
ON (tgt.NODE_ID = src.NODE_ID)
WHEN NOT MATCHED THEN
    INSERT (NODE_ID, NODE_TYPE, NODE_VALUE, PROPERTIES, CREATED_AT)
    VALUES (:node_id, :node_type, :node_value, :properties, CURRENT_TIMESTAMP)
"""

INSERT_EDGE_SQL = """
INSERT INTO OIC_KB_GRAPH_EDGES (EDGE_ID, FROM_NODE, TO_NODE, EDGE_TYPE, PROPERTIES, CREATED_AT)
VALUES (:edge_id, :from_node, :to_node, :edge_type, :properties, CURRENT_TIMESTAMP)
"""

CHECK_EDGE_SQL = """
SELECT COUNT(*) FROM OIC_KB_GRAPH_EDGES
WHERE FROM_NODE = :from_node
  AND TO_NODE   = :to_node
  AND EDGE_TYPE = :edge_type
"""

# ── FIX: Scoped KG insights query ─────────────────────────────────────────────
# Traverse: JiraTicket --[LOGGED_IN (reverse)]--> FlowCode --[HAD_ERROR]--> Error
#           Error --[ON_ENDPOINT]--> Endpoint
#           Error --[HAS_ROOT_CAUSE]--> RootCause
# Scoped to this specific JiraTicket so we don't bleed data across logs.

GET_KG_INSIGHTS_SQL = """
SELECT
    n2.NODE_TYPE,
    n2.NODE_VALUE,
    e1.EDGE_TYPE
FROM OIC_KB_GRAPH_EDGES e1
JOIN OIC_KB_GRAPH_NODES n2 ON e1.TO_NODE = n2.NODE_ID
WHERE e1.FROM_NODE  = :jira_node
  AND e1.EDGE_TYPE IN ('ON_ENDPOINT', 'HAS_ROOT_CAUSE')
"""

GET_RECURRENCE_SQL = """
SELECT COUNT(*)
FROM OIC_KB_GRAPH_EDGES e1
JOIN OIC_KB_GRAPH_EDGES e2 ON e1.TO_NODE   = e2.FROM_NODE
                           AND e2.EDGE_TYPE = 'HAD_ERROR'
                           AND e2.TO_NODE   = :error_node
WHERE e1.FROM_NODE = :flow_node
  AND e1.EDGE_TYPE = 'LOGGED_IN'
  AND e1.TO_NODE   LIKE 'JiraTicket:%'
"""

GET_RELATED_TICKETS_SQL = """
SELECT n2.NODE_VALUE AS related_jira
FROM OIC_KB_GRAPH_EDGES e
JOIN OIC_KB_GRAPH_NODES n2 ON e.TO_NODE = n2.NODE_ID
WHERE e.FROM_NODE = :jira_node
  AND e.EDGE_TYPE IN ('DUPLICATE_OF', 'RELATED_TO')
"""


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _make_node_id(node_type: str, node_value: str) -> str:
    return f"{node_type}:{node_value}"[:200]


def _upsert_node(cursor, node_type: str, node_value: str, properties: dict = None) -> str:
    node_id = _make_node_id(node_type, node_value)
    props   = json.dumps(properties) if properties else None

    cursor.execute(UPSERT_NODE_SQL, {
        "node_id":    node_id,
        "node_type":  node_type,
        "node_value": node_value[:500],
        "properties": props
    })

    return node_id


def _insert_edge(cursor, from_node: str, to_node: str, edge_type: str, properties: dict = None):
    cursor.execute(CHECK_EDGE_SQL, {
        "from_node": from_node,
        "to_node":   to_node,
        "edge_type": edge_type
    })
    count = cursor.fetchone()[0]

    if count > 0:
        logger.info(f"Edge already exists: {from_node} --[{edge_type}]--> {to_node}")
        return

    props = json.dumps(properties) if properties else None

    cursor.execute(INSERT_EDGE_SQL, {
        "edge_id":    str(uuid.uuid4()),
        "from_node":  from_node,
        "to_node":    to_node,
        "edge_type":  edge_type,
        "properties": props
    })

    logger.info(f"Edge created: {from_node} --[{edge_type}]--> {to_node}")


# ── WRITE: ADD LOG TO GRAPH ────────────────────────────────────────────────────

def add_log_to_graph(normalized_log: dict, jira_id: str) -> bool:
    try:
        flow  = normalized_log.get("flow")  or {}
        error = normalized_log.get("error") or {}
        msg   = error.get("message_parsed") or {}

        flow_code   = flow.get("code")
        trigger     = flow.get("trigger_type")
        error_code  = error.get("code")
        endpoint    = error.get("endpoint_name")
        root_cause  = msg.get("root_cause")

        if not flow_code and not error_code:
            logger.warning("graph_service: skipping — no flow_code or error_code found")
            return False

        conn   = get_connection()
        cursor = conn.cursor()

        try:
            flow_node  = None
            error_node = None
            ep_node    = None
            rc_node    = None
            jira_node  = None

            if flow_code:
                flow_node = _upsert_node(
                    cursor, "FlowCode", flow_code,
                    properties={"trigger_type": trigger} if trigger else None
                )

            if error_code:
                error_node = _upsert_node(cursor, "Error", error_code)

            if endpoint:
                ep_node = _upsert_node(cursor, "Endpoint", endpoint)

            if root_cause:
                rc_node = _upsert_node(cursor, "RootCause", root_cause)

            if jira_id:
                ticket_id = jira_id.split("/")[-1] if "/" in jira_id else jira_id
                jira_node = _upsert_node(
                    cursor, "JiraTicket", ticket_id,
                    properties={"full_url": jira_id}
                )

            if flow_node and error_node:
                _insert_edge(cursor, flow_node, error_node, "HAD_ERROR")

            if error_node and ep_node:
                _insert_edge(cursor, error_node, ep_node, "ON_ENDPOINT")

            if error_node and rc_node:
                _insert_edge(cursor, error_node, rc_node, "HAS_ROOT_CAUSE")

            if flow_node and jira_node:
                _insert_edge(cursor, flow_node, jira_node, "LOGGED_IN")

            # ── Direct JiraTicket edges for scoped KG insights ─────────────────
            # Allows GET_KG_INSIGHTS_SQL to find the exact Error/Endpoint/RootCause
            # for THIS ticket without bleeding across shared FlowCode nodes.
            if jira_node and error_node:
                _insert_edge(cursor, jira_node, error_node, "HAD_ERROR")

            if jira_node and ep_node:
                _insert_edge(cursor, jira_node, ep_node, "ON_ENDPOINT")

            if jira_node and rc_node:
                _insert_edge(cursor, jira_node, rc_node, "HAS_ROOT_CAUSE")

            conn.commit()
            logger.info(f"graph_service: log added to graph | flow={flow_code} | jira={jira_id}")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"graph_service: graph write failed: {e}")
            raise

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"graph_service: add_log_to_graph failed: {e}")
        return False


# ── WRITE: ADD JIRA RELATIONSHIP ───────────────────────────────────────────────

def add_jira_relationship(
    from_jira_id: str,
    to_jira_id: str,
    edge_type: str,
    confidence: int = None
) -> bool:
    try:
        from_ticket = from_jira_id.split("/")[-1] if "/" in from_jira_id else from_jira_id
        to_ticket   = to_jira_id.split("/")[-1]   if "/" in to_jira_id   else to_jira_id

        from_node = _make_node_id("JiraTicket", from_ticket)
        to_node   = _make_node_id("JiraTicket", to_ticket)

        props = {"confidence": confidence} if confidence else None

        conn   = get_connection()
        cursor = conn.cursor()

        try:
            _insert_edge(cursor, from_node, to_node, edge_type, properties=props)
            conn.commit()
            logger.info(f"graph_service: {from_ticket} --[{edge_type}]--> {to_ticket}")
            return True

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"graph_service: add_jira_relationship failed: {e}")
        return False


# ── READ: ENRICH SEARCH RESULTS ────────────────────────────────────────────────

def enrich_search_results(matches: list[dict]) -> list[dict]:
    try:
        conn   = get_connection()
        cursor = conn.cursor()

        try:
            for match in matches:
                jira_id    = match.get("jira_id", "")
                flow_code  = match.get("flow_code", "")
                error_code = match.get("error_code", "")

                ticket_id  = jira_id.split("/")[-1] if "/" in jira_id else jira_id
                jira_node  = _make_node_id("JiraTicket", ticket_id)
                flow_node  = _make_node_id("FlowCode", flow_code)  if flow_code  else None
                error_node = _make_node_id("Error",    error_code) if error_code else None

                insights = {
                    "root_cause":       None,
                    "endpoints":        [],
                    "recurrence_count": 0,
                    "related_tickets":  []
                }

                # ── Scoped insights: traverse via JiraTicket → FlowCode → Error ──
                cursor.execute(GET_KG_INSIGHTS_SQL, {"jira_node": jira_node})
                rows = cursor.fetchall()
                for node_type, node_value, edge_type in rows:
                    if edge_type == "HAS_ROOT_CAUSE":
                        insights["root_cause"] = node_value
                    elif edge_type == "ON_ENDPOINT":
                        if node_value not in insights["endpoints"]:
                            insights["endpoints"].append(node_value)

                # ── Recurrence count ───────────────────────────────────────────
                # Counts JiraTickets for this specific FlowCode that also had
                # this same Error — i.e. how many times THIS flow hit THIS error.
                if flow_node and error_node:
                    cursor.execute(GET_RECURRENCE_SQL, {
                        "flow_node":  flow_node,
                        "error_node": error_node
                    })
                    insights["recurrence_count"] = cursor.fetchone()[0]

                # ── Related Jira tickets ───────────────────────────────────────
                if jira_node:
                    cursor.execute(GET_RELATED_TICKETS_SQL, {"jira_node": jira_node})
                    insights["related_tickets"] = [row[0] for row in cursor.fetchall()]

                match["kg_insights"] = insights
                logger.info(f"graph_service: enriched {ticket_id} | root_cause={insights['root_cause']} | recurrence={insights['recurrence_count']}")

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"graph_service: enrich_search_results failed: {e}")

    return matches
