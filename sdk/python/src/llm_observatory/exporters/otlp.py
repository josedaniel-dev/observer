"""OTLP HTTP exporter for sending traces to observatory backend."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from llm_observatory.exporters import BaseExporter


class OTLPExporter(BaseExporter):
    """Exports traces to an OTLP-compatible backend via HTTP."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 10.0,
    ) -> None:
        """Initialize the exporter.

        Args:
            endpoint: Backend endpoint URL.
            api_key: Optional API key for authentication.
            timeout: Request timeout in seconds.
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def export(self, spans: list[dict[str, Any]]) -> None:
        """Export spans to the backend.

        Args:
            spans: List of span dictionaries to export.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = self._client.post(
                f"{self.endpoint}/v1/traces",
                json={"spans": spans},
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            # Silently fail for now - in production, add retry logic
            pass

    def flush(self) -> None:
        """Flush any buffered spans."""
        self._client.close()

    def __del__(self) -> None:
        """Clean up the client."""
        try:
            self._client.close()
        except Exception:
            pass
