#!/usr/bin/env python3
"""
test_search_api.py
------------------
Test the /search endpoint with a real log file.
Displays search results including Knowledge Graph insights.
"""

import json
import requests

# Read log file
with open('flow-logs/01_flow-log.json', 'r') as f:
    log_content = f.read()

# Call search endpoint
print("=== Searching for similar logs ===")
response = requests.post(
    'http://localhost:8000/search',
    json={'log_content': log_content}
)

# Print results
print(f"\nStatus Code: {response.status_code}\n")

if response.status_code == 200:
    data = response.json()
    print(f"Status : {data['status']}")
    print(f"Message: {data['message']}\n")

    for i, match in enumerate(data['matches'], 1):
        print(f"{'='*60}")
        print(f"Rank {i}:")
        print(f"  Jira ID        : {match['jira_id']}")
        print(f"  Similarity     : {match['similarity_score']}%")
        print(f"  Flow Code      : {match['flow_code']}")
        print(f"  Trigger        : {match['trigger_type']}")
        print(f"  Error Code     : {match['error_code']}")
        print(f"  Classification : {match.get('classification')} ({match.get('confidence')}%)")
        print(f"  Reasoning      : {match.get('reasoning')}")
        print(f"  Summary        : {match['error_summary'][:100]}")

        # ── KG Insights ───────────────────────────────────────────
        kg = match.get('kg_insights')
        if kg:
            print(f"  --- KG Insights ---")
            print(f"  Root Cause     : {kg.get('root_cause') or 'N/A'}")
            print(f"  Endpoints      : {', '.join(kg.get('endpoints', [])) or 'N/A'}")
            print(f"  Recurrence     : {kg.get('recurrence_count', 0)} time(s)")
            related = kg.get('related_tickets', [])
            print(f"  Related Tickets: {', '.join(related) if related else 'None'}")
        else:
            print(f"  --- KG Insights : Not available ---")

        print()

else:
    print(f"Error: {response.json()}")
