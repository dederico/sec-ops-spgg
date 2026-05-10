from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    AuditVerifyResponse,
    Incident,
    IncidentsListResponse,
    SessionResponse,
    SessionsListResponse,
    SessionStartRequest,
    SessionStopResponse,
    SessionSummary,
)
from .store import InMemoryStore, demo_analysis_for_session

app = FastAPI(title="CertiVision SPGG", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = InMemoryStore()
connections: set[WebSocket] = set()
boot_time = datetime.now(UTC)


async def broadcast(payload: dict) -> None:
    stale: list[WebSocket] = []
    for ws in connections:
        try:
            await ws.send_json(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        connections.discard(ws)


async def run_mock_pipeline(session_id: UUID) -> None:
    for frame_number in range(1, 6):
        session = await store.get_session(session_id)
        if not session or session.status != "ACTIVE":
            return
        await asyncio.sleep(1.2)
        session = await store.register_frame(session_id)
        await broadcast(
            {
                "type": "HEARTBEAT",
                "timestamp": datetime.now(UTC).isoformat(),
                "cameras_active": sum(1 for item in await store.list_sessions() if item.status == "ACTIVE"),
                "frames_analyzed": sum(item.frames_analyzed for item in await store.list_sessions()),
                "incidents_today": len(store.incidents),
            }
        )
        analysis = demo_analysis_for_session(session.request, frame_number)
        if not analysis:
            continue
        incident = await store.add_incident(session_id, analysis)
        await broadcast({"type": "INCIDENT_ALERT", "incident": incident.model_dump(mode="json")})
        return


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": app.version,
        "database": "mocked",
        "gemini_api": "mocked",
        "uptime_seconds": int((datetime.now(UTC) - boot_time).total_seconds()),
    }


@app.post("/sessions/start", response_model=SessionResponse)
async def start_session(request: SessionStartRequest) -> SessionResponse:
    session = await store.create_session(request)
    session.task = asyncio.create_task(run_mock_pipeline(session.session_id))
    await broadcast(
        {
            "type": "CAMERA_STATUS",
            "source_id": request.camera_label,
            "status": "ACTIVE",
        }
    )
    return SessionResponse(
        session_id=session.session_id,
        status="STARTED",
        camera_label=request.camera_label,
        started_at=session.started_at,
    )


@app.post("/sessions/{session_id}/stop", response_model=SessionStopResponse)
async def stop_session(session_id: UUID) -> SessionStopResponse:
    session = await store.stop_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await broadcast(
        {
            "type": "CAMERA_STATUS",
            "source_id": session.request.camera_label,
            "status": "STOPPED",
        }
    )
    return SessionStopResponse(
        session_id=session_id,
        status="STOPPED",
        frames_analyzed=session.frames_analyzed,
        incidents_detected=session.incidents_detected,
        duration_seconds=int((datetime.now(UTC) - session.started_at).total_seconds()),
    )


@app.get("/sessions", response_model=SessionsListResponse)
async def list_sessions() -> SessionsListResponse:
    sessions = await store.list_sessions()
    return SessionsListResponse(
        sessions=[
            SessionSummary(
                session_id=session.session_id,
                camera_label=session.request.camera_label,
                status=session.status,
                started_at=session.started_at,
                frames_analyzed=session.frames_analyzed,
                incidents_detected=session.incidents_detected,
            )
            for session in sessions
        ]
    )


@app.get("/incidents", response_model=IncidentsListResponse)
async def list_incidents(limit: int = 50, offset: int = 0) -> IncidentsListResponse:
    incidents = store.incidents[offset : offset + min(limit, 200)]
    return IncidentsListResponse(total=len(store.incidents), incidents=incidents)


@app.get("/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: UUID) -> Incident:
    incident = await store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/audit/verify", response_model=AuditVerifyResponse)
async def audit_verify() -> AuditVerifyResponse:
    integrity_valid, first_hash, last_hash = await store.verify_integrity()
    return AuditVerifyResponse(
        integrity_valid=integrity_valid,
        total_records=len(store.incidents),
        verified_at=datetime.now(UTC),
        first_record_hash=first_hash,
        last_record_hash=last_hash,
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)
    except Exception:
        connections.discard(websocket)


@app.on_event("shutdown")
async def shutdown() -> None:
    sessions = await store.list_sessions()
    for session in sessions:
        if session.task and not session.task.done():
            session.task.cancel()
            with suppress(asyncio.CancelledError):
                await session.task
