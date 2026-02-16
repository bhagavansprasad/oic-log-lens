# =============================================================
# AIOps Platform — Embedding Service
# Uses google.genai (new SDK) with gemini-embedding-001 (3072-dim)
# API key is picked up automatically from GEMINI_API_KEY /
# GOOGLE_API_KEY environment variables (set in ~/.bashrc)
# =============================================================

from __future__ import annotations
import logging
import time

from google import genai

from config.settings import GeminiConfig

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generates 3072-dim float32 embeddings via Gemini API.

    Usage:
        svc = EmbeddingService(config.gemini)
        svc.init()
        vector = svc.generate_vector("flow: X\nstep: Y\nerror: Z")
    """

    def __init__(self, config: GeminiConfig):
        self._config = config
        self._client: genai.Client | None = None
        self._ready = False

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        """
        Initialise Gemini client.
        API key is read automatically from GOOGLE_API_KEY / GEMINI_API_KEY
        environment variables — do NOT pass it explicitly or it routes
        to Vertex AI instead of AI Studio and fails with 401.
        """
        self._client = genai.Client()   # key from env automatically
        self._ready = True
        logger.info(
            "EmbeddingService ready | model=%s | dim=%d",
            self._config.model,
            self._config.embedding_dim,
        )

    # ------------------------------------------------------------------ #
    # Core API
    # ------------------------------------------------------------------ #

    def generate_vector(self, text: str) -> list[float]:
        """
        Embed a single semantic text string.

        Args:
            text: Curated semantic text from SemanticTextBuilder.

        Returns:
            List of 3072 floats (the embedding vector).
        """
        self._check_ready()

        if not text or not text.strip():
            raise ValueError("Cannot embed empty text.")

        logger.debug("Generating embedding | text_len=%d", len(text))
        start = time.perf_counter()

        result = self._client.models.embed_content(
            model=self._config.model,
            contents=text,
        )

        vector: list[float] = result.embeddings[0].values
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.debug(
            "Embedding generated | dim=%d | latency_ms=%.1f",
            len(vector),
            elapsed_ms,
        )

        # Sanity check — should always be 3072
        if len(vector) != self._config.embedding_dim:
            raise ValueError(
                f"Unexpected embedding dimension: got {len(vector)}, "
                f"expected {self._config.embedding_dim}."
            )

        return vector

    def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple texts sequentially.
        Failed embeddings raise immediately.
        """
        self._check_ready()

        vectors = []
        for i, text in enumerate(texts):
            try:
                vectors.append(self.generate_vector(text))
            except Exception as e:
                logger.error("Embedding failed for text[%d]: %s", i, e)
                raise
        return vectors

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _check_ready(self) -> None:
        if not self._ready:
            raise RuntimeError(
                "EmbeddingService not initialised. Call init() first."
            )