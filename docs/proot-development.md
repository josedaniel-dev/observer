# PRoot Development Guide

Development guide for building LLM Observatory within Termux/PRoot constraints.

## Environment Profile

| Resource | Status | Notes |
|----------|--------|-------|
| CPU | 8 cores ARM64 | Sufficient for compilation and testing |
| RAM | 7.4 GB | Enough for FastAPI + Node dev servers |
| Storage | 122 GB free | Ample for all components |
| OS | Debian 13 (trixie) via PRoot | No kernel-level features |
| Python | 3.13 | Full CPython, pip works |
| Node.js | 24 | Full npm ecosystem |
| SQLite | Available | Primary database |
| Container runtime | **None** | Podman/Docker impossible |
| systemd/init | **None** | No service management |
| PostgreSQL | **Not installed** | Use SQLite instead |

## Hard Constraints

| Feature | Available | Workaround |
|---------|-----------|------------|
| User namespaces | No | N/A - containers impossible |
| cgroups | No | N/A - containers impossible |
| systemd | No | Run processes directly |
| Root access | No | User-level only |
| Kernel modules | No | PRoot limitation |
| `/proc/sys` writes | No | Read-only |

## What Works Here

- Python/Node.js compilation and execution
- SQLite databases (file-based, no server)
- FastAPI with uvicorn (direct process)
- React/Vite development server
- Git operations
- npm/pip package management
- Unit testing (pytest, vitest)

## What Doesn't Work

- Podman/Docker container builds
- PostgreSQL server
- Redis server
- systemd services
- Kernel-dependent features

## Development Architecture

```
PRoot Environment (Development)
┌─────────────────────────────────────────────────────┐
│  Python SDK (tracer, instrumentors)                 │
│  TypeScript SDK (tracer, instrumentors)             │
│  FastAPI Backend (SQLite backend, no PostgreSQL)    │
│  CLI Tool (local operations)                        │
│  React Dashboard (Vite dev server)                  │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
            SQLite database file
                    │
                    ▼
Standard Server (Production)
┌─────────────────────────────────────────────────────┐
│  Podman containers                                  │
│  PostgreSQL                                         │
│  Full stack deployment                              │
└─────────────────────────────────────────────────────┘
```

## Quick Start (PRoot)

### 1. Install SQLite backend dependencies

```bash
cd backend
pip install --break-system-packages aiosqlite
```

### 2. Run backend with SQLite

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./observatory.db uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Run dashboard

```bash
cd dashboard
npm run dev
```

### 4. Run tests

```bash
cd sdk/python && pytest tests/ -v
cd backend && pytest tests/ -v
```

## Development Workflow

### Phase 1: Local Development (PRoot)

Focus on components that work without containers:

1. **SDK Development** - Full testing, no dependencies
2. **API Development** - FastAPI + SQLite
3. **Dashboard Development** - React/Vite hot reload
4. **CLI Development** - Local commands only

### Phase 2: Migration to Laptop

When moving to a standard Linux environment:

1. Switch database: `DATABASE_URL=postgresql+asyncpg://...`
2. Build containers: `podman-compose up -d`
3. Run migrations: `alembic upgrade head`
4. Deploy full stack

## Testing Strategy

### Unit Tests (PRoot)

```bash
# Python SDK - works fully
cd sdk/python
pytest tests/ -v

# Backend API - works with SQLite
cd backend
DATABASE_URL=sqlite+aiosqlite:///./test.db pytest tests/ -v

# Dashboard - builds successfully
cd dashboard
npm run build
```

### Integration Tests (Laptop)

Full integration tests require PostgreSQL and are deferred to laptop environment.

## Environment Variables

```bash
# PRoot development
export DATABASE_URL="sqlite+aiosqlite:///./observatory.db"
export APP_ENV="development"
export CORS_ORIGINS="http://localhost:5173"

# Production (laptop/server)
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/observatory"
export APP_ENV="production"
export PODMAN_COMPOSE="true"
```

## Limitations and Workarounds

| Limitation | Workaround |
|------------|------------|
| No containers | Run processes directly |
| No PostgreSQL | Use SQLite (aiosqlite) |
| No systemd | Start with `uvicorn` directly |
| No root | All user-level operations |
| Memory pressure | Use `--workers 1` for uvicorn |

## Migration Checklist

When moving to laptop:

- [ ] Install PostgreSQL
- [ ] Install Podman
- [ ] Switch DATABASE_URL to PostgreSQL
- [ ] Run `podman-compose up -d`
- [ ] Run `alembic upgrade head`
- [ ] Verify full stack with `podman-compose logs`
- [ ] Run integration tests
