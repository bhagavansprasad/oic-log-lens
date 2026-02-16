# =============================================================
# AIOps Platform — Oracle DB Connection Pool
# python-oracledb thin mode (no Oracle Client install needed)
# =============================================================

import oracledb
import logging
from contextlib import contextmanager
from config.settings import OracleConfig

logger = logging.getLogger(__name__)


class OracleConnectionPool:
    """
    Manages a single shared connection pool for the application.
    Use as a singleton — create once, share everywhere.
    """

    def __init__(self, config: OracleConfig):
        self._config = config
        self._pool: oracledb.ConnectionPool | None = None

    def init(self) -> None:
        """
        Initialize the pool. Call once at application startup.
        """
        logger.info(
            "Initialising Oracle connection pool | DSN=%s | min=%d max=%d",
            self._config.dsn,
            self._config.pool_min,
            self._config.pool_max,
        )

        # Thin mode — no Oracle Instant Client required

        self._pool = oracledb.create_pool(
            user=self._config.user,
            password=self._config.password,
            dsn=self._config.dsn,
            min=self._config.pool_min,
            max=self._config.pool_max,
            increment=self._config.pool_increment,
        )
        logger.info("Oracle connection pool ready.")

    def close(self) -> None:
        """Gracefully close the pool. Call at application shutdown."""
        if self._pool:
            self._pool.close()
            logger.info("Oracle connection pool closed.")

    @contextmanager
    def acquire(self):
        """
        Context manager that yields a connection from the pool.

        Usage:
            with pool.acquire() as conn:
                with conn.cursor() as cur:
                    cur.execute(...)
        """
        if self._pool is None:
            raise RuntimeError("Pool not initialised. Call init() first.")

        conn = self._pool.acquire()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.release(conn)
