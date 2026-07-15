"""Tests for the backend API."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models import Base
from app.db import get_session


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create a test database session."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_engine):
    """Create a test client with overridden database."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.anyio
async def test_root(client):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "LLM Observatory"
    assert data["version"] == "0.1.0"


@pytest.mark.anyio
async def test_create_trace(client):
    """Test creating a trace."""
    response = await client.post("/v1/traces/", json={
        "name": "test-trace",
        "start_time": 1700000000.0,
        "status": "ok",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-trace"
    assert data["status"] == "ok"
    assert "id" in data


@pytest.mark.anyio
async def test_create_trace_with_spans(client):
    """Test creating a trace with spans."""
    response = await client.post("/v1/traces/", json={
        "name": "test-trace",
        "start_time": 1700000000.0,
        "status": "ok",
        "spans": [
            {
                "name": "llm-call",
                "span_type": "llm",
                "start_time": 1700000000.0,
                "end_time": 1700000001.0,
                "status": "ok",
                "tokens_input": 100,
                "tokens_output": 50,
                "cost_usd": 0.001,
            }
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-trace"


@pytest.mark.anyio
async def test_list_traces(client):
    """Test listing traces."""
    # Create a trace first
    await client.post("/v1/traces/", json={
        "name": "test-trace",
        "start_time": 1700000000.0,
        "status": "ok",
    })

    response = await client.get("/v1/traces/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "test-trace"


@pytest.mark.anyio
async def test_list_traces_with_status_filter(client):
    """Test listing traces with status filter."""
    # Create traces with different statuses
    await client.post("/v1/traces/", json={
        "name": "ok-trace",
        "start_time": 1700000000.0,
        "status": "ok",
    })
    await client.post("/v1/traces/", json={
        "name": "error-trace",
        "start_time": 1700000001.0,
        "status": "error",
    })

    response = await client.get("/v1/traces/?status=ok")
    assert response.status_code == 200
    data = response.json()
    assert all(t["status"] == "ok" for t in data)


@pytest.mark.anyio
async def test_get_trace(client):
    """Test getting a single trace."""
    create_response = await client.post("/v1/traces/", json={
        "name": "test-trace",
        "start_time": 1700000000.0,
        "status": "ok",
    })
    trace_id = create_response.json()["id"]

    response = await client.get(f"/v1/traces/{trace_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-trace"


@pytest.mark.anyio
async def test_get_trace_not_found(client):
    """Test getting a non-existent trace."""
    response = await client.get("/v1/traces/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_trace_invalid_id(client):
    """Test getting a trace with invalid ID format."""
    response = await client.get("/v1/traces/not-a-uuid")
    assert response.status_code == 400


@pytest.mark.anyio
async def test_get_trace_spans(client):
    """Test getting spans for a trace."""
    create_response = await client.post("/v1/traces/", json={
        "name": "test-trace",
        "start_time": 1700000000.0,
        "status": "ok",
        "spans": [
            {
                "name": "span-1",
                "span_type": "llm",
                "start_time": 1700000000.0,
                "end_time": 1700000001.0,
                "status": "ok",
            }
        ],
    })
    trace_id = create_response.json()["id"]

    response = await client.get(f"/v1/traces/{trace_id}/spans")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "span-1"


@pytest.mark.anyio
async def test_batch_create_spans(client):
    """Test batch creating spans."""
    response = await client.post("/v1/traces/batch", json={
        "spans": [
            {
                "trace_id": "00000000-0000-0000-0000-000000000001",
                "name": "span-1",
                "span_type": "llm",
                "start_time": 1700000000.0,
                "end_time": 1700000001.0,
                "status": "ok",
            },
            {
                "trace_id": "00000000-0000-0000-0000-000000000001",
                "name": "span-2",
                "span_type": "llm",
                "start_time": 1700000001.0,
                "end_time": 1700000002.0,
                "status": "ok",
            },
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1  # Both spans belong to same trace


@pytest.mark.anyio
async def test_create_evaluation(client):
    """Test creating an evaluation."""
    # Create a trace first
    create_response = await client.post("/v1/traces/", json={
        "name": "test-trace",
        "start_time": 1700000000.0,
        "status": "ok",
    })
    trace_id = create_response.json()["id"]

    response = await client.post("/v1/evaluations/", json={
        "trace_id": trace_id,
        "evaluator_type": "rule_based",
        "score": 0.95,
        "criteria": {"max_latency": 1.0},
    })
    assert response.status_code == 200
    data = response.json()
    assert float(data["score"]) == 0.95


@pytest.mark.anyio
async def test_list_evaluations(client):
    """Test listing evaluations."""
    # Create a trace and evaluation
    create_response = await client.post("/v1/traces/", json={
        "name": "test-trace",
        "start_time": 1700000000.0,
        "status": "ok",
    })
    trace_id = create_response.json()["id"]

    await client.post("/v1/evaluations/", json={
        "trace_id": trace_id,
        "evaluator_type": "rule_based",
        "score": 0.95,
    })

    response = await client.get("/v1/evaluations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.anyio
async def test_run_rule_based_evaluation(client):
    """Test running a rule-based evaluation."""
    # Create a trace with spans
    create_response = await client.post("/v1/traces/", json={
        "name": "test-trace",
        "start_time": 1700000000.0,
        "status": "ok",
        "spans": [
            {
                "name": "span-1",
                "span_type": "llm",
                "start_time": 1700000000.0,
                "end_time": 1700000001.0,
                "status": "ok",
                "cost_usd": 0.001,
            }
        ],
    })
    trace_id = create_response.json()["id"]

    response = await client.post("/v1/evaluations/run", json={
        "trace_id": trace_id,
        "evaluator_type": "rule_based",
        "criteria": [
            {"name": "max_latency", "description": "Max latency", "threshold": 5000},
            {"name": "max_cost", "description": "Max cost", "threshold": 0.1},
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "result" in data
    assert "passed" in data["result"]


@pytest.mark.anyio
async def test_analytics_summary(client):
    """Test analytics summary endpoint."""
    # Create some traces
    for i in range(3):
        await client.post("/v1/traces/", json={
            "name": f"trace-{i}",
            "start_time": 1700000000.0 + i,
            "status": "ok" if i < 2 else "error",
        })

    response = await client.get("/v1/analytics/summary?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert data["total_traces"] == 3
    assert data["error_count"] == 1


@pytest.mark.anyio
async def test_analytics_cost_by_model(client):
    """Test cost-by-model endpoint."""
    await client.post("/v1/traces/", json={
        "name": "trace-with-cost",
        "start_time": 1700000000.0,
        "status": "ok",
        "spans": [
            {
                "name": "openai-call",
                "span_type": "llm",
                "start_time": 1700000000.0,
                "end_time": 1700000001.0,
                "status": "ok",
                "cost_usd": 0.005,
                "attributes": {"model": "gpt-4o"},
            }
        ],
    })

    response = await client.get("/v1/analytics/cost-by-model?hours=24")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["model"] == "gpt-4o"
    assert float(data[0]["cost_usd"]) > 0


@pytest.mark.anyio
async def test_analytics_timeline(client):
    """Test timeline endpoint."""
    for i in range(3):
        await client.post("/v1/traces/", json={
            "name": f"trace-{i}",
            "start_time": 1700000000.0 + i,
            "status": "ok",
        })

    response = await client.get("/v1/analytics/timeline?hours=24&interval_minutes=60")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.anyio
async def test_delete_trace(client):
    """Test deleting a trace."""
    create_response = await client.post("/v1/traces/", json={
        "name": "trace-to-delete",
        "start_time": 1700000000.0,
        "status": "ok",
    })
    trace_id = create_response.json()["id"]

    response = await client.delete(f"/v1/traces/{trace_id}")
    assert response.status_code == 200

    # Verify it's gone
    response = await client.get(f"/v1/traces/{trace_id}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_trace_not_found(client):
    """Test deleting a non-existent trace."""
    response = await client.delete("/v1/traces/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_delete_evaluation(client):
    """Test deleting an evaluation."""
    # Create trace + eval
    create_response = await client.post("/v1/traces/", json={
        "name": "trace-for-eval-delete",
        "start_time": 1700000000.0,
        "status": "ok",
    })
    trace_id = create_response.json()["id"]

    eval_response = await client.post("/v1/evaluations/", json={
        "trace_id": trace_id,
        "evaluator_type": "rule_based",
        "score": 0.8,
    })
    eval_id = eval_response.json()["id"]

    response = await client.delete(f"/v1/evaluations/{eval_id}")
    assert response.status_code == 200

    # Verify it's gone
    response = await client.get(f"/v1/evaluations/{eval_id}")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_sdk_batch_export_contract(client):
    """Integration test: verify SDK OTLPExporter batch format is accepted by backend."""
    # This simulates what the Python SDK's OTLPExporter sends to /v1/traces/batch
    trace_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    spans = [
        {
            "id": "span-001",
            "trace_id": trace_id,
            "parent_id": None,
            "name": "openai.chat.completions.create",
            "span_type": "llm",
            "start_time": 1700000000.0,
            "end_time": 1700000001.5,
            "status": "ok",
            "input": {"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]},
            "output": {"content": "Hi there!", "role": "assistant"},
            "tokens_input": 10,
            "tokens_output": 5,
            "cost_usd": 0.0001,
            "metadata": {},
            "attributes": {"model": "gpt-4o", "gen_ai.system": "openai"},
        }
    ]

    response = await client.post("/v1/traces/batch", json={"spans": spans})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "openai.chat.completions.create"

    # Verify spans are queryable
    trace_id_resp = data[0]["id"]
    spans_response = await client.get(f"/v1/traces/{trace_id_resp}/spans")
    assert spans_response.status_code == 200
    spans_data = spans_response.json()
    assert len(spans_data) == 1
    assert spans_data[0]["tokens_input"] == 10
    assert spans_data[0]["tokens_output"] == 5
    assert float(spans_data[0]["cost_usd"]) == 0.0001
