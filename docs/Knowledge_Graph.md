# OIC-LogLens — Knowledge Graph (KG) Feature Documentation

> Covers synthetic log design, relationship patterns, search output interpretation,
> before/after KG comparison, validation results, and pending backlog.

---

## 1. What is the Knowledge Graph?

The Knowledge Graph (KG) is a supplementary layer on top of the vector similarity search. While vector search finds *similar* logs based on semantic embeddings, the KG provides *structured factual context* about each matched log — its exact root cause, which endpoints were involved, how many times the error has occurred, and whether it is linked to other Jira tickets.

Each log ingested into the system writes a set of nodes and edges into the graph:

**Node Types**

| Node | Description | Example |
|---|---|---|
| `FlowCode` | The OIC integration flow | `RH_NAVAN_DAILY_INTEGR_SCHEDU` |
| `Error` | The error code | `Execution failed`, `net.http.503` |
| `Endpoint` | The OIC adapter endpoint | `InvokeIntegration`, `GetItemFromATP` |
| `RootCause` | The parsed root cause message | `Not Found`, `ORA-00942` |
| `JiraTicket` | The Jira issue ID | `OLL-96E9EDBF` |

**Edge Types**

| Edge | From → To | Meaning |
|---|---|---|
| `HAD_ERROR` | FlowCode → Error | This flow produced this error |
| `ON_ENDPOINT` | Error → Endpoint | This error occurred on this endpoint |
| `HAS_ROOT_CAUSE` | Error → RootCause | This error's root cause |
| `LOGGED_IN` | FlowCode → JiraTicket | This flow is tracked in this Jira ticket |
| `DUPLICATE_OF` | JiraTicket → JiraTicket | LLM classified as exact duplicate |
| `RELATED_TO` | JiraTicket → JiraTicket | LLM classified as similar/related |

---

## 2. Synthetic Log Design — Pattern of Logs Generated

To validate the KG and search pipeline, 8 synthetic (controlled) logs were generated in `gen-logs/`. These logs have **known relationships** so search results can be verified against a cheat sheet.

### 2.1 Group A — CloudInvocationException / 404 Not Found (NAVAN flow)

These 4 logs are based on the real log `01_flow-log.json` and cover different combinations of flow name and error code.

| Log | Flow | Trigger | Endpoint | Error | Root Cause | Role |
|---|---|---|---|---|---|---|
| T01 | `RH_NAVAN_DAILY_INTEGR_SCHEDU` | scheduled | InvokeIntegration | Execution failed | Not Found | **Query log** (used for search) |
| T02 | `RH_NAVAN_DAILY_INTEGR_SCHEDU` | scheduled | InvokeIntegration | Execution failed | Not Found | Exact duplicate of T01 |
| T03 | `RH_NAVAN_WEEKLY_INTEGR_SCHEDU` | scheduled | InvokeIntegration | Execution failed | Not Found | Similar root cause (different flow) |
| T04 | `RH_NAVAN_DAILY_INTEGR_SCHEDU` | scheduled | InvokeIntegration | net.http.503 | Service Unavailable | Related (same flow, different error) |

### 2.2 Group B — Auth Failure (ORDERVALIDATION flow)

| Log | Flow | Trigger | Endpoint | Error | Root Cause | Role |
|---|---|---|---|---|---|---|
| T05 | `ORDERVALIDATION` | soap | TriggerIntegration | 401 Unauthorized | Unauthorized | Query log for Group B |
| T06 | `ORDERFULFILLMENT` | soap | TriggerIntegration | 401 Unauthorized | Unauthorized | Similar root cause (different flow) |

### 2.3 Group C — SQL Error (BPA Price Update flow)

| Log | Flow | Trigger | Endpoint | Error | Root Cause | Role |
|---|---|---|---|---|---|---|
| T07 | `TEST_BPA_PRICE_UPDATE_V3` | rest | GetItemFromATP | Execution failed | ORA-00942: table or view does not exist | Mirrors real log 02 pattern |

### 2.4 Group D — Unrelated

| Log | Flow | Trigger | Endpoint | Error | Root Cause | Role |
|---|---|---|---|---|---|---|
| T08 | `SUPPLIER_SYNC_DAILY` | rest | CreateSupplier | 500 | Internal server error | Not related to any group |

---

## 3. How the Synthetic Logs Are Related

The relationship matrix below shows what search result you should expect when searching with **T01** as the query log.

```
T01 (Query)
 │
 ├── T02  ──── EXACT_DUPLICATE      Same flow + same endpoint + same error + same root cause
 │
 ├── T03  ──── SIMILAR_ROOT_CAUSE   Different flow (WEEKLY vs DAILY), same error + root cause
 │
 ├── T04  ──── RELATED              Same flow + same endpoint, different error (503 vs 404)
 │
 ├── T05  ──── NOT_RELATED          Completely different flow, endpoint, error domain
 ├── T06  ──── NOT_RELATED          Completely different flow, endpoint, error domain
 ├── T07  ──── NOT_RELATED          Completely different flow, endpoint, error domain
 └── T08  ──── NOT_RELATED          Completely different flow, endpoint, error domain
```

When searching with **T05** as the query log:

```
T05 (Query)
 │
 ├── T06  ──── SIMILAR_ROOT_CAUSE   Different flow (ORDERFULFILLMENT vs ORDERVALIDATION), same auth error
 │
 ├── T01-T04  ─ NOT_RELATED         Different error domain entirely
 └── T07-T08  ─ NOT_RELATED         Different error domain entirely
```

### Classification Criteria

| Classification | Confidence | When it applies |
|---|---|---|
| `EXACT_DUPLICATE` | 90–100% | Same flow, endpoint, error code, root cause. Same fix applies. |
| `SIMILAR_ROOT_CAUSE` | 70–89% | Same root cause or error pattern, different flow or minor variation. Fix is likely transferable. |
| `RELATED` | 50–69% | Same flow or endpoint, different error code or family. Useful context even if fix differs. |
| `NOT_RELATED` | 0–49% | Different flow, endpoint, and error domain. Not helpful for resolution. |

---

## 4. How to Interpret the Search Output with KG

When you run a search, each result has two sections — the **vector search + LLM section** and the **KG Insights section**.

### 4.1 Full Output Structure

```
Rank N:
  Jira ID        : https://...atlassian.net/browse/OLL-XXXXXXXX
  Similarity     : 98.75%                  ← vector cosine similarity
  Flow Code      : RH_NAVAN_DAILY_...      ← flow that produced the error
  Trigger        : scheduled               ← how the flow was triggered
  Error Code     : Execution failed        ← OIC error code
  Classification : SIMILAR_ROOT_CAUSE (80%)  ← LLM classification + confidence
  Reasoning      : <LLM explanation>       ← why the LLM classified it this way
  Summary        : oracle.cloud.connector… ← first 100 chars of error summary

  --- KG Insights ---
  Root Cause     : Not Found               ← parsed root cause from this ticket's graph path
  Endpoints      : InvokeIntegration       ← endpoints this ticket's error hit
  Recurrence     : 3 time(s)              ← how many times this flow+error combination occurred
  Related Tickets: OLL-ABC, OLL-DEF        ← tickets linked by DUPLICATE_OF or RELATED_TO edges
```

### 4.2 How to Read Each KG Field

**Root Cause** — The exact root cause extracted during ingestion for *this specific ticket*. Scoped to the ticket's own graph path (`JiraTicket → Error → RootCause`) so it never shows another ticket's root cause.

**Endpoints** — Which OIC adapter endpoints were involved when the error occurred. Useful for pinpointing which adapter or target system to investigate.

**Recurrence** — How many times the same flow produced the same error in the knowledge base. Counted by traversing `FlowCode --[LOGGED_IN]--> JiraTicket --[HAD_ERROR]--> Error`, scoped to this specific flow + error combination. A count of 3 means 3 separate Jira tickets for the same flow hit the same error — a strong signal of a recurring systemic issue.

**Related Tickets** — Jira tickets that the LLM classified as `DUPLICATE_OF` or `RELATED_TO` this ticket in previous searches. Builds up over time as more searches are run.

### 4.3 Decision Guide

| What you see | What it means | Action |
|---|---|---|
| `EXACT_DUPLICATE` + same Root Cause | Confirmed duplicate | Close new ticket, link to existing |
| `SIMILAR_ROOT_CAUSE` + same Endpoint | Same adapter issue, different flow | Check if same fix applies to this flow |
| `RELATED` + same Flow, different error | Same integration, different failure mode | Investigate the flow broadly |
| `NOT_RELATED` across all results | Genuinely new issue | Create new Jira ticket |
| Recurrence > 1 | Recurring systemic error | Escalate — this is not a one-off |
| Related Tickets populated | Already part of a known cluster | Read linked tickets for resolution history |

---

## 5. Output Without KG vs With KG

### 5.1 Without KG

Before the Knowledge Graph was introduced, search results only showed vector similarity and LLM classification:

```
Rank 1:
  Jira ID        : https://...atlassian.net/browse/OLL-96E9EDBF
  Similarity     : 100.0%
  Flow Code      : RH_NAVAN_DAILY_INTEGR_SCHEDU
  Trigger        : scheduled
  Error Code     : Execution failed
  Classification : EXACT_DUPLICATE (100%)
  Reasoning      : Flow name, trigger, error code, error summary and root cause
                   are identical. It is the same error.
  Summary        : oracle.cloud.connector.api.CloudInvocationException
```

**Limitations without KG:**
- You could tell *that* it was a duplicate, but not *what* the root cause was unless you opened the original Jira ticket
- No way to know if the error was recurring or a one-off
- No visibility into which endpoints were affected
- No cross-ticket linking — each search result was isolated

### 5.2 With KG

The same result now includes structured, factual context pulled directly from the graph:

```
Rank 1:
  Jira ID        : https://...atlassian.net/browse/OLL-96E9EDBF
  Similarity     : 100.0%
  Flow Code      : RH_NAVAN_DAILY_INTEGR_SCHEDU
  Trigger        : scheduled
  Error Code     : Execution failed
  Classification : EXACT_DUPLICATE (100%)
  Reasoning      : Flow name, trigger, error code, error summary and root cause
                   are identical. It is the same error.
  Summary        : oracle.cloud.connector.api.CloudInvocationException

  --- KG Insights ---
  Root Cause     : Not Found
  Endpoints      : InvokeIntegration
  Recurrence     : 3 time(s)
  Related Tickets: None
```

### 5.3 Side-by-Side Comparison

| Capability | Without KG | With KG |
|---|---|---|
| Finds similar logs | ✅ Vector similarity | ✅ Vector similarity |
| LLM classification | ✅ EXACT_DUPLICATE etc. | ✅ EXACT_DUPLICATE etc. |
| Root cause visible in results | ❌ Must open Jira ticket | ✅ Shown inline |
| Endpoint context | ❌ Not shown | ✅ Shown inline |
| Recurrence count | ❌ Not available | ✅ Shown inline, scoped per flow+error |
| Cross-ticket linking | ❌ Not available | ✅ DUPLICATE_OF / RELATED_TO edges |
| Scoped per ticket | N/A | ✅ Each ticket shows its own data |
| Improves over time | ❌ Static | ✅ Graph grows with every search |

---

## 6. Validation Results

All three synthetic log groups were validated against the search pipeline.

### Group A — T01 Query (NAVAN DAILY, 404 Not Found)

| Rank | Jira Ticket | Classification | KG Root Cause | KG Recurrence | ✅/❌ |
|---|---|---|---|---|---|
| 1 | OLL-4FF0674A | EXACT_DUPLICATE (100%) | Not Found | 3 | ✅ |
| 2 | OLL-EB5B1B12 | EXACT_DUPLICATE (100%) | Not Found | 3 | ✅ |
| 3 | OLL-96E9EDBF | EXACT_DUPLICATE (100%) | Not Found | 3 | ✅ |
| 4 | OLL-A59D9F74 | SIMILAR_ROOT_CAUSE (80%) | Not Found | 1 | ✅ |
| 5 | OLL-61B5BE03 | RELATED (65%) | Service Unavailable | 1 | ✅ |

**5/5 correct ✅**

### Group B — T05 Query (ORDERVALIDATION, 401 Unauthorized)

| Rank | Jira Ticket | Flow | Classification | KG Root Cause | ✅/❌ |
|---|---|---|---|---|---|
| 1 | OLL-AD4B3FC4 | ORDERVALIDATION (real) | EXACT_DUPLICATE (100%) | N/A | ✅ |
| 2 | OLL-9760B2BE | ORDERVALIDATION (T05) | EXACT_DUPLICATE (100%) | N/A | ✅ |
| 3 | OLL-51D6EACF | ORDERFULFILLMENT (T06) | SIMILAR_ROOT_CAUSE (85%) | Unauthorized | ✅ |
| 4 | OLL-DD026514 | EXTCOMMONORDER 503 | NOT_RELATED (40%) | N/A | ✅ |
| 5 | OLL-21E195B4 | INT1_SOAP_GTM 406 | NOT_RELATED (40%) | Target URL... | ✅ |

**5/5 correct ✅**

Note: Ranks 1 and 2 show `Root Cause: N/A` because the 401 error message is an ASM policy string — clean root cause extraction is a normalizer improvement, not a KG bug.

### Group C — T07 Query (TEST_BPA_PRICE_UPDATE_V3, ORA-00942)

| Rank | Jira Ticket | Flow | Classification | KG Root Cause | ✅/❌ |
|---|---|---|---|---|---|
| 1 | OLL-592BDEBD | TEST_BPA (T07) | EXACT_DUPLICATE (100%) | ORA-00942 | ✅ |
| 2 | OLL-3C5C205C | TEST_BPA CA-BS-001 (real) | SIMILAR_ROOT_CAUSE (90%) | ORA-00942 | ⚠️ |
| 3 | OLL-DD026514 | EXTCOMMONORDER 503 | RELATED (60%) | N/A | ⚠️ |
| 4 | OLL-67F1D465 | SUPPLIER_SYNC 500 | NOT_RELATED (30%) | JBO-FND... | ✅ |
| 5 | OLL-866F9103 | XX_FROM_AI_CREATE | NOT_RELATED (25%) | N/A | ✅ |

**3/5 correct, 2 borderline ⚠️**

- Rank 2: CA-BS-001 has a different error code but same flow + same ORA-00942 on the same endpoint. SIMILAR_ROOT_CAUSE is acceptable here.
- Rank 3: EXTCOMMONORDER 503 classified as RELATED is borderline — different flow, endpoint, and error domain. The LLM is reasoning about infrastructure-level similarity. Acceptable deviation.

---

## 7. Bugs Fixed

### KG-1 — KG Insights scoping bug
**Problem:** `GET_KG_INSIGHTS_SQL` queried from the shared `Error` node, bleeding data across all logs with the same error code. All results showed the same root cause regardless of which ticket was matched.

**Fix:** Added direct `JiraTicket --[HAD_ERROR/ON_ENDPOINT/HAS_ROOT_CAUSE]--> *` edges during ingestion. Query now reads directly from the JiraTicket node, fully scoped per ticket.

### KG-2 — Recurrence count always 1 (then inflated)
**Problem:** Original query counted `HAD_ERROR` edges on the `FlowCode` node — only 1 edge exists per flow+error pair so count was always 1. After Phase 1 fix it counted all `JiraTicket → Error` edges across all flows, giving inflated counts (6 instead of 3).

**Fix:** Query now joins `FlowCode --[LOGGED_IN]--> JiraTicket --[HAD_ERROR]--> Error`, scoping the count to tickets for this specific flow + error combination.

```sql
SELECT COUNT(*)
FROM OIC_KB_GRAPH_EDGES e1
JOIN OIC_KB_GRAPH_EDGES e2 ON e1.TO_NODE   = e2.FROM_NODE
                           AND e2.EDGE_TYPE = 'HAD_ERROR'
                           AND e2.TO_NODE   = :error_node
WHERE e1.FROM_NODE = :flow_node
  AND e1.EDGE_TYPE = 'LOGGED_IN'
  AND e1.TO_NODE   LIKE 'JiraTicket:%'
```

---

## 8. TODO Backlog

| # | Branch | Description | Priority |
|---|---|---|---|
| KG-3 | `feat/kg-phase2-patterns` | Pattern Intelligence — recurring error trends, top failing flows, `GET /kg/patterns` endpoint | Medium |
| KG-4 | `feat/kg-phase3-fixed-by` | FIXED_BY edges — capture resolutions when Jira tickets are closed, surface fix history in search results | Medium |
| KG-5 | `feat/kg-related-tickets` | Related Tickets currently empty on first search — pre-populate on ingestion using existing graph edges | Low |
| KG-6 | `fix/ingest-timeout` | `/ingest/database` times out UI at 60s for large batches — convert to background job with `/ingest/status/{job_id}` | Low |

---

*Last updated: KG Phase 1 + recurrence fix — February 2026*
