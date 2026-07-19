"""OTLP HTTP exporter for sending traces to observatory backend."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from llm_observatory.exporters import BaseExporter

logger = logging.getLogger(__name__)


class OTLPExporter(BaseExporter):
    """Exports traces to an OTLP-compatible backend via HTTP."""

    def __init__(
        self,
        endpoint: str = "http://localhost:8000",
        api_key: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the exporter.

        Args:
            endpoint: Backend endpoint URL.
            api_key: Optional API key for authentication.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries on failure.
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.Client(timeout=timeout)

    def export(self, spans: list[dict[str, Any]]) -> None:
        """Export spans to the backend.

        Args:
            spans: List of span dictionaries to export.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(self.max_retries):
            try:
                response = self._client.post(
                    f"{self.endpoint}/v1/traces/batch",
                    json={"spans": spans},
                    headers=headers,
                )
                response.raise_for_status()
                logger.debug(f"Exported {len(spans)} spans successfully")
                return
            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Export failed (attempt {attempt + 1}/{self.max_retries}): "
                    f"HTTP {e.response.status_code} - {e.response.text}"
                )
                if attempt == self.max_retries - 1:
                    msg = (
                        f"Export failed after {self.max_retries} attempts, "
                        f"dropping {len(spans)} spans"
                    )
                    logger.error(msg)
            except httpx.HTTPError as e:
                logger.warning(
                    f"Export failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt == self.max_retries - 1:
                    msg = (
                        f"Export failed after {self.max_retries} attempts, "
                        f"dropping {len(spans)} spans"
                    )
                    logger.error(msg)

    def flush(self) -> None:
        """Flush any buffered spans."""
        self._client.close()

    def __del__(self) -> None:
        """Clean up the client."""
        try:
            self._client.close()
        except Exception:
            pass
