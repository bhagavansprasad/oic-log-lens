#!/usr/bin/env python3
"""
load_logs_to_db.py
------------------
Load all log files from flow-logs/ and gen-logs/ into TEST_LOGS table.
Used to test the /ingest/database endpoint.
"""

import oracledb
from pathlib import Path

# Database connection
DB_USER     = "EA_APP"
DB_PASSWORD = "jnjnuh"
DB_DSN      = "localhost/FREEPDB1"

# Log files to load — both real and controlled test logs
LOG_FILES = [
    ("flow-logs", "01_flow-log.json"),
    ("flow-logs", "02_flow-log.json"),
    ("flow-logs", "03_flow-log.json"),
    ("flow-logs", "04_flow-log.json"),
    ("flow-logs", "05_flow-log.json"),
    ("flow-logs", "06_flow-log.json"),
    ("flow-logs", "07_flow-log.json"),
    ("flow-logs", "08_flow-log.json"),
    ("gen-logs",  "T01_flow-log.json"),
    ("gen-logs",  "T02_flow-log.json"),
    ("gen-logs",  "T03_flow-log.json"),
    ("gen-logs",  "T04_flow-log.json"),
    ("gen-logs",  "T05_flow-log.json"),
    ("gen-logs",  "T06_flow-log.json"),
    ("gen-logs",  "T07_flow-log.json"),
    ("gen-logs",  "T08_flow-log.json"),
]


def create_table(conn):
    """Drop and recreate TEST_LOGS table."""
    cursor = conn.cursor()
    try:
        cursor.execute("DROP TABLE TEST_LOGS")
        print("Dropped existing TEST_LOGS table")
    except Exception:
        pass  # Table didn't exist yet

    cursor.execute("""
        CREATE TABLE TEST_LOGS (
            LOG_ID   NUMBER        PRIMARY KEY,
            LOG_NAME VARCHAR2(100),
            LOG_DIR  VARCHAR2(50),
            LOG_JSON CLOB
        )
    """)
    print("Created TEST_LOGS table")
    cursor.close()


def insert_logs(conn):
    """Insert all log files into TEST_LOGS."""
    cursor = conn.cursor()

    for i, (folder, filename) in enumerate(LOG_FILES, start=1):
        file_path = Path(folder) / filename

        if not file_path.exists():
            print(f"  [{i:02d}] SKIP  {folder}/{filename} — file not found")
            continue

        with open(file_path, 'r') as f:
            log_content = f.read()

        cursor.execute(
            "INSERT INTO TEST_LOGS (LOG_ID, LOG_NAME, LOG_DIR, LOG_JSON) VALUES (:1, :2, :3, :4)",
            (i, filename, folder, log_content)
        )
        print(f"  [{i:02d}] OK    {folder}/{filename}")

    conn.commit()
    cursor.close()


def verify_data(conn):
    """Print summary of inserted data."""
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM TEST_LOGS")
    total = cursor.fetchone()[0]
    print(f"\nTotal rows in TEST_LOGS: {total}")

    cursor.execute("SELECT LOG_ID, LOG_DIR, LOG_NAME FROM TEST_LOGS ORDER BY LOG_ID")
    print("\nRows:")
    for row in cursor.fetchall():
        print(f"  {row[0]:02d}  {row[1]}/{row[2]}")

    cursor.close()


if __name__ == "__main__":
    print("=== Loading logs into TEST_LOGS ===\n")

    conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
    print(f"Connected to {DB_DSN}\n")

    try:
        create_table(conn)
        print()
        insert_logs(conn)
        verify_data(conn)

        print("\nDone! Ingest all logs via database endpoint:")
        print("")
        print('  curl -X POST http://localhost:8000/ingest/database \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d \'{"connection_string": "EA_APP/jnjnuh@localhost/FREEPDB1",')
        print('          "query": "SELECT LOG_JSON FROM TEST_LOGS ORDER BY LOG_ID"}\'')

    finally:
        conn.close()
