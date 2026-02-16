# =============================================================
# AIOps Platform — Semantic Text Builder
#
# Converts a raw log JSON dict into a curated semantic string
# used ONLY for embedding. No IDs, timestamps, or OCIDs.
#
# Design rule (from spec):
#   ✅ Include: error message, step, business key, flow name
#   ❌ Exclude: eventId, timestamps, OCIDs, payload size,
#               instance IDs, connection IDs
# =============================================================

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class SemanticContext:
    """
    Structured representation of what gets embedded.
    Separate from raw log — only meaningful semantic fields.
    """
    flow_code: str | None
    action_name: str | None
    error_message: str | None
    business_key: str | None


class SemanticTextBuilder:
    """
    Builds the canonical semantic text string from a log dict.

    The output format is fixed (per spec):
        flow: <FLOW_CODE>
        step: <ACTION_NAME>
        error: <ERROR_MESSAGE>
        business_key: <IMPORTANT_IDENTIFIER>

    Unknown / missing fields are omitted — never embedded as "None".
    """

    # Fields that should NEVER be embedded (spec §4.1)
    _EXCLUDED_KEYS = frozenset({
        "eventId", "event_id",
        "timestamp", "event_time", "created_at", "updated_at",
        "ocid", "instance_id", "connection_id",
        "payload_size", "request_size", "response_size",
    })

    # Common log field name aliases → semantic slot mapping
    _FLOW_ALIASES = ("flow_code", "flow", "integration_name", "pipeline_name")
    _ACTION_ALIASES = ("action_name", "action", "step", "step_name", "operation")
    _ERROR_ALIASES = ("error_message", "error", "message", "fault_message", "exception")
    _BUSINESS_KEY_ALIASES = (
        "business_key", "business_id",
        "order_id", "customer_id", "transaction_id",
        "request_id", "correlation_id", "entity_id",
    )

    # ------------------------------------------------------------------ #

    def extract_context(self, log: dict[str, Any]) -> SemanticContext:
        """
        Extract the semantic context from a raw log dict.
        Resolves field aliases automatically.
        """
        return SemanticContext(
            flow_code=self._resolve(log, self._FLOW_ALIASES),
            action_name=self._resolve(log, self._ACTION_ALIASES),
            error_message=self._resolve(log, self._ERROR_ALIASES),
            business_key=self._resolve(log, self._BUSINESS_KEY_ALIASES),
        )

    def build_from_log(self, log: dict[str, Any]) -> str:
        """
        Main entry point.
        Accepts a raw log dict, returns the curated semantic string.
        Raises ValueError if no meaningful fields could be extracted.
        """
        ctx = self.extract_context(log)
        return self.build_from_context(ctx)

    def build_from_context(self, ctx: SemanticContext) -> str:
        """
        Build semantic text from an already-extracted SemanticContext.
        """
        parts: list[str] = []

        if ctx.flow_code:
            parts.append(f"flow: {ctx.flow_code.strip()}")
        if ctx.action_name:
            parts.append(f"step: {ctx.action_name.strip()}")
        if ctx.error_message:
            parts.append(f"error: {ctx.error_message.strip()}")
        if ctx.business_key:
            parts.append(f"business_key: {ctx.business_key.strip()}")

        if not parts:
            raise ValueError(
                "Cannot build semantic text — no meaningful fields found in log. "
                "Expected at least one of: flow_code, action_name, error_message, business_key."
            )

        return "\n".join(parts)

    def build_from_raw_text(self, raw_text: str) -> str:
        """
        Pass-through for callers who already have semantic text
        (e.g. direct API input via error_text field).
        Strips and validates it's non-empty.
        """
        cleaned = raw_text.strip()
        if not cleaned:
            raise ValueError("Provided error_text is empty.")
        return cleaned

    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve(log: dict[str, Any], aliases: tuple[str, ...]) -> str | None:
        """
        Try each alias key in order, return the first non-empty string found.
        """
        for key in aliases:
            value = log.get(key)
            if value and isinstance(value, str) and value.strip():
                return value.strip()
        return None
