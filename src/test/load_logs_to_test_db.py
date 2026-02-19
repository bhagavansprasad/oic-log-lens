#!/usr/bin/env python3
"""
load_logs_to_db.py
------------------
Load all log files from flow-logs/ into TEST_LOGS table for testing.
"""

import json
import oracledb
from pathlib import Path

# Database connection
DB_USER = "EA_APP"
DB_PASSWORD = "jnjnuh"
DB_DSN = "localhost/FREEPDB1"

# Log files directory
LOG_DIR = Path("flow-logs")
LOG_FILES = [
    "01_flow-log.json",
    "02_flow-log.json",
    "03_flow-log.json",
    "04_flow-log.json",
    "05_flow-log.json",
    "06_flow-log.json",
    "07_flow-log.json",
    "08_flow-log.json",
]


def create_table(conn):
    """Create TEST_LOGS table if it doesn't exist"""
    cursor = conn.cursor()
    
    try:
        # Drop table if exists
        cursor.execute("DROP TABLE TEST_LOGS")
        print("Dropped existing TEST_LOGS table")
    except:
        pass
    
    # Create table
    cursor.execute("""
        CREATE TABLE TEST_LOGS (
            LOG_ID NUMBER PRIMARY KEY,
            LOG_NAME VARCHAR2(100),
            LOG_JSON CLOB
        )
    """)
    print("Created TEST_LOGS table")
    cursor.close()


def insert_logs(conn):
    """Insert all log files into TEST_LOGS"""
    cursor = conn.cursor()
    
    for i, log_file in enumerate(LOG_FILES, start=1):
        file_path = LOG_DIR / log_file
        
        if not file_path.exists():
            print(f"⚠️  Skipping {log_file} - file not found")
            continue
        
        # Read log file
        with open(file_path, 'r') as f:
            log_content = f.read()
        
        # Insert into database
        cursor.execute(
            "INSERT INTO TEST_LOGS (LOG_ID, LOG_NAME, LOG_JSON) VALUES (:1, :2, :3)",
            (i, log_file, log_content)
        )
        
        print(f"✅ Inserted {log_file} (LOG_ID: {i})")
    
    conn.commit()
    cursor.close()


def verify_data(conn):
    """Verify inserted data"""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM TEST_LOGS")
    count = cursor.fetchone()[0]
    print(f"\n📊 Total logs in TEST_LOGS: {count}")
    
    cursor.execute("SELECT LOG_ID, LOG_NAME FROM TEST_LOGS ORDER BY LOG_ID")
    print("\nLogs in table:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    cursor.close()


if __name__ == "__main__":
    print("=== Loading logs into TEST_LOGS table ===\n")
    
    # Connect to database
    print(f"Connecting to {DB_DSN}...")
    conn = oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
    print("Connected!\n")
    
    try:
        # Create table
        create_table(conn)
        print()
        
        # Insert logs
        insert_logs(conn)
        
        # Verify
        verify_data(conn)
        
        print("\n✅ Done! You can now test /ingest/database endpoint")
        print("\nExample test command:")
        print('curl -X POST http://localhost:8000/ingest/database \\')
        print('  -H "Content-Type: application/json" \\')
        print("  -d '{")
        print('    "connection_string": "EA_APP/jnjnuh@localhost/FREEPDB1",')
        print('    "query": "SELECT LOG_JSON FROM TEST_LOGS WHERE LOG_ID = 1"')
        print("  }'")
        
    finally:
        conn.close()
