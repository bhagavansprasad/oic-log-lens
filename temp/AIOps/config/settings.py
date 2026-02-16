# =============================================================
# AIOps Platform — Configuration
# All secrets loaded from environment / .env file
# =============================================================

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class OracleConfig:
    user: str
    password: str
    dsn: str           # host:port/service_name
    pool_min: int
    pool_max: int
    pool_increment: int


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str
    model: str
    embedding_dim: int


@dataclass(frozen=True)
class AppConfig:
    oracle: OracleConfig
    gemini: GeminiConfig

    # Similarity thresholds (from design doc)
    threshold_known: float       # > this → known incident
    threshold_related: float     # > this → related issue, else new


def load_config() -> AppConfig:
    return AppConfig(
        oracle=OracleConfig(
            user=os.environ["ORACLE_USER"],
            password=os.environ["ORACLE_PASSWORD"],
            dsn=os.environ["ORACLE_DSN"],          # e.g. localhost:1521/FREEPDB1
            pool_min=int(os.getenv("ORACLE_POOL_MIN", "2")),
            pool_max=int(os.getenv("ORACLE_POOL_MAX", "10")),
            pool_increment=int(os.getenv("ORACLE_POOL_INCREMENT", "1")),
        ),
        gemini=GeminiConfig(
            api_key=os.environ["GEMINI_API_KEY"],
            model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"),
            embedding_dim=int(os.getenv("GEMINI_EMBEDDING_DIM", "3072")),
        ),
        threshold_known=float(os.getenv("THRESHOLD_KNOWN", "0.90")),
        threshold_related=float(os.getenv("THRESHOLD_RELATED", "0.75")),
    )
