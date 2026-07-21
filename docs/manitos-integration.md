# ManitOS telemetry ingestion

The `manitOS-observer` branch exposes a versioned, retry-safe ingestion contract for
ManitOS runtimes. It is additive: existing `/v1/traces` clients remain supported.

## Endpoint

`POST /v1/ingest/manitos/traces`

When `OBSERVATORY_API_KEY` is configured, send it as
`Authorization: Bearer <key>` just like the existing API.

```json
{
  "schema_version": "manitos.telemetry.v1",
  "idempotency_key": "session_20260720:turn_4:completed",
  "project_id": "manitos",
  "environment": "development",
  "service_instance_id": "desktop-01",
  "session_id": "session_20260720_abc123",
  "turn_id": "turn_000004",
  "actor_id_hash": "hmac-sha256:...",
  "trace": {
    "id": "e74ffdfa-d9e9-49fe-9a7e-3ec20eeeff26",
    "name": "manitos.turn",
    "start_time": 1750000000.0,
    "end_time": 1750000002.0,
    "status": "ok",
    "metadata": {"privacy_mode": "metadata_only"}
  },
  "spans": [
    {
      "id": "46e94fc2-70df-48a6-a3a6-d7ce5c23edb4",
      "parent_id": null,
      "name": "llm.generate",
      "span_type": "llm",
      "start_time": 1750000000.2,
      "end_time": 1750000001.4,
      "status": "ok",
      "tokens_input": 120,
      "tokens_output": 48,
      "attributes": {"model": "local-model", "language": "en"}
    }
  ]
}
```

## Idempotency

The unique retry identity is `(project_id, idempotency_key)`.

- Replaying an identical request returns `status: duplicate` and writes no rows.
- Reusing a key with different content returns HTTP `409`.
- A new key may update an existing trace or span by UUID.
- A span UUID cannot be moved to another trace.
- A trace UUID cannot be reused by another project.

Successful responses report accepted, updated, duplicate, and rejected span counts.
Validation errors reject the entire envelope; partial writes are never committed.

## Limits

- One trace per request.
- Between 1 and 500 spans.
- Maximum serialized envelope size: 2 MiB.
- Maximum individual JSON field size: 64 KiB.
- Maximum JSON nesting depth: 8.
- Trace and span IDs must be UUIDs.
- ManitOS `session_id` values are opaque strings up to 255 characters.
- Unknown fields and unknown schema versions are rejected.

## Privacy baseline

The contract supports input and output JSON, but ManitOS exporters should default to
metadata-only telemetry. Prompts, responses, tool arguments, credentials, and artifacts
must not be sent unless the user explicitly enables content capture and the payload has
passed local redaction. `actor_id_hash` is intended for a locally generated keyed hash,
not a raw user identifier.

## ManitOS exporter (phases 2-3)

ManitOS now includes an opt-in background exporter for this contract. Enable it in
the ManitOS process with:

```bash
MANITOS_OBSERVER_ENABLED=1
MANITOS_OBSERVER_URL=http://127.0.0.1:8000
MANITOS_OBSERVER_API_KEY=
MANITOS_OBSERVER_PROJECT_ID=manitos
MANITOS_OBSERVER_ENVIRONMENT=development
MANITOS_OBSERVER_INSTANCE_ID=desktop-01
MANITOS_OBSERVER_ACTOR_HASH_KEY=<local-secret>
```

The exporter is disabled by default. It emits one trace per completed or failed turn,
uses a bounded in-memory queue, retries only transient HTTP/network failures, and
flushes during adapter shutdown. Queue saturation or Observer unavailability never
blocks or fails the conversation path.

The current producer is intentionally metadata-only. It records safe routing,
language, continuation, latency, and status attributes, but does not serialize prompts,
responses, tool arguments, credentials, artifacts, or raw actor identifiers. When
`MANITOS_OBSERVER_ACTOR_HASH_KEY` is configured, the actor identifier is represented as
a local HMAC-SHA256 digest; otherwise `actor_id_hash` is omitted.

## Database migration

From `backend/`:

```bash
alembic upgrade head
```

Alembic reads `DATABASE_URL` at runtime. The migration is reversible on both SQLite and
PostgreSQL and creates correlation columns plus `ingestion_receipts`.
