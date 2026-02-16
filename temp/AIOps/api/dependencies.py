# =============================================================
# AIOps Platform — FastAPI Dependencies
# Provides AIOpsService instance to all route handlers
# =============================================================

from services.aiops_service import AIOpsService

# Singleton service instance — set once at startup via lifespan
_service: AIOpsService | None = None


def set_service(service: AIOpsService) -> None:
    """Called once at startup to register the service instance."""
    global _service
    _service = service


def get_service() -> AIOpsService:
    """FastAPI dependency — inject into route handlers."""
    if _service is None:
        raise RuntimeError("AIOpsService not initialised.")
    return _service
