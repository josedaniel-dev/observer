"""FastAPI application for LLM Observatory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import traces, evaluations
from app.db.postgres import engine
from app.websocket import manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="LLM Observatory",
    description="Open-source observability and telemetry platform for LLMs",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(traces.router, prefix="/v1/traces", tags=["traces"])
app.include_router(evaluations.router, prefix="/v1/evaluations", tags=["evaluations"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": "LLM Observatory",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time trace streaming."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back or handle specific commands
            await manager.send_personal(websocket, {"type": "pong", "data": data})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
