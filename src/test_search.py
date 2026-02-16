"""
test_search.py
--------------
Tests the search / deduplication pipeline for OIC-LogLens.
Takes a query log, normalizes it, generates an embedding,
and searches OLL_LOGS for the Top-5 most similar records.
"""

import sys
from normalizer import normalize_log_from_file
from embedder import generate_embedding
from db import search_similar_logs

# ── QUERY LOG ──────────────────────────────────────────────────────────────────
# Change this to test with different query logs.
# Using a log already in the DB tests for self-match (expect score ~0.0).
# Using a new/unseen log tests real deduplication.

QUERY_LOG = "flow-logs/01_flow-log.json"
TOP_N     = 5


# ── FUNCTIONS ──────────────────────────────────────────────────────────────────

def run_normalization(file_path: str) -> dict | None:
    """
    Normalizes the query log file.

    Args:
        file_path: Path to the query log file.

    Returns:
        Normalized log dict if successful, None otherwise.
    """
    print(f"\n{'='*60}")
    print(f"QUERY LOG : {file_path}")
    print(f"{'='*60}")
    try:
        normalized = normalize_log_from_file(file_path)
        print(f"Flow Code  : {normalized.get('flow', {}).get('code')}")
        print(f"Log Type   : {normalized.get('log_type')}")
        print(f"Error Code : {normalized.get('error', {}).get('code')}")
        return normalized
    except Exception as e:
        print(f"[NORMALIZATION ERROR] {e}")
        return None


def run_embedding(normalized_log: dict) -> list | None:
    """
    Generates embedding for the normalized query log.

    Args:
        normalized_log: Normalized log dict.

    Returns:
        Embedding vector if successful, None otherwise.
    """
    print(f"\n--- Generating Query Embedding ---")
    try:
        embedding = generate_embedding(normalized_log)
        print(f"Dimensions : {len(embedding)}")
        return embedding
    except Exception as e:
        print(f"[EMBEDDING ERROR] {e}")
        return None


def run_search(query_embedding: list, top_n: int) -> list | None:
    """
    Searches OLL_LOGS for the most similar logs.

    Args:
        query_embedding: Vector embedding of the query log.
        top_n:           Number of top results to return.

    Returns:
        List of result dicts if successful, None otherwise.
    """
    print(f"\n--- Vector Similarity Search (Top-{top_n}) ---")
    try:
        results = search_similar_logs(query_embedding, top_n)
        return results
    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        return None


def print_results(results: list) -> None:
    """
    Prints the search results in a readable format.

    Args:
        results: List of result dicts from search_similar_logs.
    """
    print(f"\n{'='*60}")
    print(f"SEARCH RESULTS")
    print(f"{'='*60}")

    if not results:
        print("No results found.")
        return

    for i, r in enumerate(results, start=1):
        # Cosine distance: 0.0 = identical, 1.0 = completely different
        # Convert to similarity percentage: 1 - distance
        distance   = float(r.get("similarity_score") or 1.0)
        similarity = round((1 - distance) * 100, 2)

        # Truncate error_summary for display
        summary = r.get("error_summary")
        summary = summary.read() if hasattr(summary, "read") else (summary or "")

        glimpse = summary[:100].replace("\n", " ") + ("..." if len(summary) > 100 else "")

        print(f"\nRank {i}")
        print(f"  Jira ID    : {r.get('jira_id')}")
        print(f"  Similarity : {similarity}%")
        print(f"  Flow Code  : {r.get('flow_code')}")
        print(f"  Trigger    : {r.get('trigger_type')}")
        print(f"  Error Code : {r.get('error_code')}")
        print(f"  Glimpse    : {glimpse}")


if __name__ == "__main__":
    # Step 1 — Normalize query log
    normalized = run_normalization(QUERY_LOG)
    if normalized is None:
        sys.exit(1)

    # Step 2 — Generate embedding
    embedding = run_embedding(normalized)
    if embedding is None:
        sys.exit(1)

    # Step 3 — Search
    results = run_search(embedding, TOP_N)
    if results is None:
        sys.exit(1)

    # Step 4 — Print results
    print_results(results)