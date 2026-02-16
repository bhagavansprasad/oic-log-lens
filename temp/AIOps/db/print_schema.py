# =============================================================
# AIOps Platform — Readable Schema Printer
# Run from project root: python3 db/print_schema.py
# =============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import load_config
from db.connection import OracleConnectionPool

TARGET_TABLES = [
    "SS_ERROR_LOGS",
]

cfg  = load_config()
pool = OracleConnectionPool(cfg.oracle)
pool.init()

with pool.acquire() as conn:
    with conn.cursor() as cur:

        for table in TARGET_TABLES:

            # Check table exists
            cur.execute(
                "SELECT COUNT(*) FROM USER_TABLES WHERE TABLE_NAME = :t",
                {"t": table}
            )
            if cur.fetchone()[0] == 0:
                continue

            # Row count
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cur.fetchone()[0]

            # Columns — no VECTOR_DIM/VECTOR_FORMAT (not in USER_TAB_COLUMNS)
            cur.execute("""
                SELECT
                    COLUMN_ID,
                    COLUMN_NAME,
                    CASE
                        WHEN DATA_TYPE = 'VARCHAR2'
                            THEN 'VARCHAR2(' || DATA_LENGTH || ')'
                        WHEN DATA_TYPE = 'NUMBER' AND DATA_PRECISION IS NOT NULL
                            THEN 'NUMBER(' || DATA_PRECISION || ',' || DATA_SCALE || ')'
                        ELSE DATA_TYPE
                    END AS DATA_TYPE,
                    CASE NULLABLE WHEN 'N' THEN 'NOT NULL' ELSE 'NULL' END AS NULLABLE
                FROM USER_TAB_COLUMNS
                WHERE TABLE_NAME = :t
                ORDER BY COLUMN_ID
            """, {"t": table})
            columns = cur.fetchall()

            # Indexes
            cur.execute("""
                SELECT INDEX_NAME, INDEX_TYPE, UNIQUENESS
                FROM USER_INDEXES
                WHERE TABLE_NAME = :t
                AND INDEX_NAME NOT LIKE 'SYS_%'
                ORDER BY INDEX_NAME
            """, {"t": table})
            indexes = cur.fetchall()

            # Print
            print()
            print("=" * 65)
            print(f"  TABLE : {table}")
            print(f"  ROWS  : {row_count}")
            print("=" * 65)
            print(f"  {'#':<4} {'COLUMN':<25} {'TYPE':<22} {'NULLABLE'}")
            print(f"  {'-'*4} {'-'*25} {'-'*22} {'-'*10}")
            for col_id, col_name, data_type, nullable in columns:
                print(f"  {col_id:<4} {col_name:<25} {data_type:<22} {nullable}")

            if indexes:
                print()
                print(f"  {'INDEX':<40} {'TYPE':<20} {'UNIQUE'}")
                print(f"  {'-'*40} {'-'*20} {'-'*6}")
                for idx_name, idx_type, uniqueness in indexes:
                    print(f"  {idx_name:<40} {idx_type:<20} {uniqueness}")

            print()

pool.close()