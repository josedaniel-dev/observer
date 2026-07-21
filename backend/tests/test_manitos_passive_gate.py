from __future__ import annotations

import httpx
import pytest

from app.ops.manitos_passive_gate import (
    PassiveGateConfig,
    PassiveGateThresholds,
    collect_sample,
    evaluate_samples,
    run_passive_gate,
)


def _sample(
    *,
    turns: int,
    errors: int = 0,
    tts_errors: int = 0,
    dropped: int = 0,
    circuit: str = "closed",
) -> dict:
    return {
        "observer": {"ok": True},
        "quality": {
            "total_turns": turns,
            "error_count": errors,
            "degraded_count": 0,
            "truncated_count": 0,
            "tool_error_count": 0,
            "fallback_count": 0,
            "tts_error_count": tts_errors,
            "avg_duration_ms": 1200,
            "avg_ttft_ms": 120,
        },
        "manitos": {
            "ok": True,
            "exporter": {
                "enabled": True,
                "privacy_mode": "metadata_only",
                "durable_delivery": True,
                "circuit_state": circuit,
                "persisted_pending": 0,
                "spool_error": None,
                "stats": {"dropped": dropped, "spool_evicted": 0},
            },
        },
    }


def test_evaluate_samples_passes_on_healthy_deltas():
    thresholds = PassiveGateThresholds(minimum_turns=2)

    result = evaluate_samples([_sample(turns=10), _sample(turns=12)], thresholds)

    assert result["passed"] is True
    assert result["observed_turns"] == 2
    assert result["quality_rates"]["error_rate"] == 0.0


def test_evaluate_samples_fails_on_quality_and_delivery_regressions():
    thresholds = PassiveGateThresholds(minimum_turns=2, maximum_error_rate=0.2)

    result = evaluate_samples(
        [_sample(turns=10), _sample(turns=12, errors=1, dropped=1, circuit="open")],
        thresholds,
    )

    assert result["passed"] is False
    assert "error_rate_above_threshold" in result["failures"]
    assert "observer_envelopes_dropped" in result["failures"]
    assert "observer_circuit_open_during_window" in result["failures"]


def test_evaluate_samples_fails_closed_without_real_turns():
    result = evaluate_samples([_sample(turns=10), _sample(turns=10)], PassiveGateThresholds())

    assert result["passed"] is False
    assert "insufficient_observed_turns" in result["failures"]


@pytest.mark.asyncio
async def test_collect_sample_keeps_only_bounded_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "healthy", "db": "ok"})
        if request.url.path == "/v1/analytics/manitos-quality":
            return httpx.Response(
                200,
                json={
                    "project_id": "manitos",
                    "environment": "test",
                    "hours": 24,
                    "total_turns": 3,
                    "error_count": 0,
                    "models": [{"key": "phi4-mini", "count": 3, "secret": "drop-me"}],
                    "prompt": "must-not-survive",
                },
            )
        if request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "features": {
                        "observer_exporter": {
                            "enabled": True,
                            "privacy_mode": "metadata_only",
                            "durable_delivery": True,
                            "circuit_state": "closed",
                            "stats": {"accepted": 3},
                            "api_key": "must-not-survive",
                        }
                    },
                },
            )
        return httpx.Response(404)

    config = PassiveGateConfig(
        observer_url="http://observer",
        manitos_ready_url="http://manitos/readyz",
        duration_seconds=0,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        sample = await collect_sample(client, config)

    assert sample["observer"]["ok"] is True
    assert sample["quality"]["models"] == [{"key": "phi4-mini", "count": 3}]
    assert "prompt" not in sample["quality"]
    assert "api_key" not in sample["manitos"]["exporter"]


@pytest.mark.asyncio
async def test_report_never_persists_api_key_or_url_credentials(tmp_path, monkeypatch):
    async def fake_collect(_client, _config):
        return _sample(turns=0)

    monkeypatch.setattr("app.ops.manitos_passive_gate.collect_sample", fake_collect)
    output = tmp_path / "gate.json"
    config = PassiveGateConfig(
        observer_url="http://user:password@observer.local:8000?token=url-secret",
        manitos_ready_url="http://manitos.local:8765/readyz?token=ready-secret",
        api_key="header-secret",
        duration_seconds=0,
        output_path=str(output),
        thresholds=PassiveGateThresholds(minimum_turns=0),
    )

    await run_passive_gate(config)

    persisted = output.read_text(encoding="utf-8")
    assert "password" not in persisted
    assert "url-secret" not in persisted
    assert "ready-secret" not in persisted
    assert "header-secret" not in persisted
