"""Contract tests for versioned ManitOS telemetry ingestion."""

from __future__ import annotations

import copy
import uuid

import pytest


def _payload(*, key: str = "turn-1-attempt-1") -> dict:
    trace_id = str(uuid.uuid4())
    root_span_id = str(uuid.uuid4())
    return {
        "schema_version": "manitos.telemetry.v1",
        "idempotency_key": key,
        "project_id": "manitos",
        "environment": "test",
        "service_instance_id": "desktop-test-01",
        "session_id": "session_20260720_abc123",
        "turn_id": "turn_000001",
        "actor_id_hash": "hmac-sha256:anonymous-test",
        "trace": {
            "id": trace_id,
            "name": "manitos.turn",
            "start_time": 1_750_000_000.0,
            "end_time": 1_750_000_002.0,
            "status": "ok",
            "metadata": {"privacy_mode": "metadata_only"},
        },
        "spans": [
            {
                "id": root_span_id,
                "name": "llm.generate",
                "span_type": "llm",
                "start_time": 1_750_000_000.2,
                "end_time": 1_750_000_001.4,
                "status": "ok",
                "tokens_input": 120,
                "tokens_output": 48,
                "attributes": {"model": "test-model", "language": "en"},
            },
            {
                "id": str(uuid.uuid4()),
                "parent_id": root_span_id,
                "name": "quality.guard",
                "span_type": "guard",
                "start_time": 1_750_000_001.4,
                "end_time": 1_750_000_001.5,
                "status": "ok",
                "attributes": {"guard": "language"},
            },
        ],
    }


@pytest.mark.anyio
async def test_ingest_accepts_manitos_identifiers_and_parent_spans(client):
    payload = _payload()

    response = await client.post("/v1/ingest/manitos/traces", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "manitos.telemetry.v1",
        "idempotency_key": payload["idempotency_key"],
        "trace_id": payload["trace"]["id"],
        "status": "accepted",
        "accepted_spans": 2,
        "updated_spans": 0,
        "duplicate_spans": 0,
        "rejected_spans": 0,
    }

    traces = await client.get(f"/v1/traces/?session_id={payload['session_id']}")
    assert traces.status_code == 200
    assert traces.json()["total"] == 1
    assert traces.json()["traces"][0]["session_id"] == payload["session_id"]
    assert traces.json()["traces"][0]["turn_id"] == payload["turn_id"]
    assert traces.json()["traces"][0]["project_id"] == payload["project_id"]
    assert traces.json()["traces"][0]["schema_version"] == payload["schema_version"]

    spans = await client.get(f"/v1/traces/{payload['trace']['id']}/spans")
    assert spans.status_code == 200
    assert len(spans.json()) == 2
    child = next(item for item in spans.json() if item["name"] == "quality.guard")
    assert child["parent_id"] == payload["spans"][0]["id"]


@pytest.mark.anyio
async def test_identical_retry_is_deduplicated(client):
    payload = _payload()
    first = await client.post("/v1/ingest/manitos/traces", json=payload)
    second = await client.post("/v1/ingest/manitos/traces", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert second.json()["accepted_spans"] == 0
    assert second.json()["duplicate_spans"] == 2

    spans = await client.get(f"/v1/traces/{payload['trace']['id']}/spans")
    assert len(spans.json()) == 2


@pytest.mark.anyio
async def test_reused_idempotency_key_with_different_payload_conflicts(client):
    payload = _payload()
    assert (await client.post("/v1/ingest/manitos/traces", json=payload)).status_code == 200

    changed = copy.deepcopy(payload)
    changed["trace"]["status"] = "error"
    response = await client.post("/v1/ingest/manitos/traces", json=changed)

    assert response.status_code == 409
    assert "different payload" in response.json()["detail"]


@pytest.mark.anyio
async def test_new_request_key_can_update_existing_span(client):
    payload = _payload()
    assert (await client.post("/v1/ingest/manitos/traces", json=payload)).status_code == 200

    updated = copy.deepcopy(payload)
    updated["idempotency_key"] = "turn-1-completed"
    updated["spans"][0]["tokens_output"] = 64
    response = await client.post("/v1/ingest/manitos/traces", json=updated)

    assert response.status_code == 200
    assert response.json()["accepted_spans"] == 0
    assert response.json()["updated_spans"] == 1
    assert response.json()["duplicate_spans"] == 1

    spans = await client.get(f"/v1/traces/{payload['trace']['id']}/spans")
    llm_span = next(item for item in spans.json() if item["name"] == "llm.generate")
    assert llm_span["tokens_output"] == 64


@pytest.mark.anyio
async def test_trace_id_cannot_cross_project_boundary(client):
    payload = _payload()
    assert (await client.post("/v1/ingest/manitos/traces", json=payload)).status_code == 200

    conflicting = copy.deepcopy(payload)
    conflicting["project_id"] = "another-project"
    conflicting["idempotency_key"] = "another-project-attempt"
    response = await client.post("/v1/ingest/manitos/traces", json=conflicting)

    assert response.status_code == 409
    assert "another project" in response.json()["detail"]


@pytest.mark.anyio
async def test_contract_rejects_duplicate_span_ids(client):
    payload = _payload()
    payload["spans"][1]["id"] = payload["spans"][0]["id"]

    response = await client.post("/v1/ingest/manitos/traces", json=payload)

    assert response.status_code == 422
    assert "span IDs must be unique" in response.text


@pytest.mark.anyio
async def test_contract_rejects_parent_cycles(client):
    payload = _payload()
    payload["spans"][0]["parent_id"] = payload["spans"][1]["id"]

    response = await client.post("/v1/ingest/manitos/traces", json=payload)

    assert response.status_code == 422
    assert "must be acyclic" in response.text


@pytest.mark.anyio
async def test_contract_rejects_unknown_schema_and_fields(client):
    payload = _payload()
    payload["schema_version"] = "manitos.telemetry.v2"
    payload["unexpected"] = True

    response = await client.post("/v1/ingest/manitos/traces", json=payload)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_contract_rejects_oversized_or_deep_json(client):
    oversized = _payload()
    oversized["trace"]["metadata"] = {"value": "x" * (64 * 1024)}
    assert (await client.post("/v1/ingest/manitos/traces", json=oversized)).status_code == 422

    deep = _payload(key="deep-json")
    value: dict = {"leaf": True}
    for _ in range(10):
        value = {"nested": value}
    deep["spans"][0]["attributes"] = value
    assert (await client.post("/v1/ingest/manitos/traces", json=deep)).status_code == 422


@pytest.mark.anyio
async def test_contract_rejects_more_than_500_spans(client):
    payload = _payload()
    template = payload["spans"][0]
    payload["spans"] = [
        {**template, "id": str(uuid.uuid4()), "parent_id": None}
        for _ in range(501)
    ]

    response = await client.post("/v1/ingest/manitos/traces", json=payload)

    assert response.status_code == 422


@pytest.mark.anyio
async def test_manitos_endpoint_uses_existing_api_auth(client):
    import app.auth as auth_mod

    payload = _payload()
    old_key = auth_mod.API_KEY
    auth_mod.API_KEY = "test-secret-key"
    try:
        blocked = await client.post("/v1/ingest/manitos/traces", json=payload)
        accepted = await client.post(
            "/v1/ingest/manitos/traces",
            json=payload,
            headers={"Authorization": "Bearer test-secret-key"},
        )
    finally:
        auth_mod.API_KEY = old_key

    assert blocked.status_code == 401
    assert accepted.status_code == 200


@pytest.mark.anyio
async def test_analytics_filters_opaque_manitos_session_id(client):
    payload = _payload()
    assert (await client.post("/v1/ingest/manitos/traces", json=payload)).status_code == 200

    response = await client.get(
        f"/v1/analytics/summary?hours=720&session_id={payload['session_id']}"
    )

    assert response.status_code == 200
    assert response.json()["total_traces"] == 1
    assert response.json()["total_spans"] == 2
