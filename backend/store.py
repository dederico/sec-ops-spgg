from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .models import AnalysisResult, Incident, IncidentType, SessionStartRequest, Severity


PLACEHOLDER_FRAME = (
    "data:image/svg+xml;base64,"
    + base64.b64encode(
        (
            "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360'>"
            "<rect width='100%' height='100%' fill='#0f172a'/>"
            "<text x='50%' y='48%' text-anchor='middle' fill='#f8fafc' "
            "font-size='28' font-family='Arial'>CertiVision</text>"
            "<text x='50%' y='58%' text-anchor='middle' fill='#94a3b8' "
            "font-size='16' font-family='Arial'>Mock frame para hackathon MVP</text>"
            "</svg>"
        ).encode("utf-8")
    ).decode("ascii")
)


@dataclass
class SessionState:
    session_id: UUID
    request: SessionStartRequest
    started_at: datetime
    status: str = "ACTIVE"
    frames_analyzed: int = 0
    incidents_detected: int = 0
    incident_ids: list[UUID] = field(default_factory=list)
    task: asyncio.Task | None = None


class InMemoryStore:
    def __init__(self) -> None:
        self.sessions: dict[UUID, SessionState] = {}
        self.incidents: list[Incident] = []
        self._lock = asyncio.Lock()

    async def create_session(self, request: SessionStartRequest) -> SessionState:
        session = SessionState(
            session_id=uuid4(),
            request=request,
            started_at=datetime.now(UTC),
        )
        async with self._lock:
            self.sessions[session.session_id] = session
        return session

    async def stop_session(self, session_id: UUID) -> SessionState | None:
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            session.status = "STOPPED"
            if session.task and not session.task.done():
                session.task.cancel()
        return session

    async def list_sessions(self) -> list[SessionState]:
        async with self._lock:
            return list(self.sessions.values())

    async def get_session(self, session_id: UUID) -> SessionState | None:
        async with self._lock:
            return self.sessions.get(session_id)

    async def get_incident(self, incident_id: UUID) -> Incident | None:
        async with self._lock:
            for incident in self.incidents:
                if incident.id == incident_id:
                    return incident
        return None

    async def add_incident(self, session_id: UUID, analysis: AnalysisResult) -> Incident:
        async with self._lock:
            session = self.sessions[session_id]
            frame_hash = self._hash_text(f"{session_id}:{session.frames_analyzed}:{analysis.model_dump_json()}")
            previous_hash = self.incidents[-1].chain_hash if self.incidents else "GENESIS"
            chain_hash = self._hash_text(f"{previous_hash}:{frame_hash}:{session.request.camera_label}")
            incident = Incident(
                id=uuid4(),
                timestamp=datetime.now(UTC),
                source_id=session.request.camera_label,
                incident_type=analysis.incident_type,
                severity=analysis.severity,
                confidence=analysis.confidence,
                description=analysis.description,
                recommended_action=analysis.recommended_action,
                frame_hash=frame_hash,
                chain_hash=chain_hash,
                session_id=session_id,
                frame_b64=PLACEHOLDER_FRAME,
            )
            self.incidents.append(incident)
            session.incidents_detected += 1
            session.incident_ids.append(incident.id)
            return incident

    async def register_frame(self, session_id: UUID) -> SessionState:
        async with self._lock:
            session = self.sessions[session_id]
            session.frames_analyzed += 1
            return session

    async def verify_integrity(self) -> tuple[bool, str | None, str | None]:
        async with self._lock:
            previous_hash = "GENESIS"
            first_hash = self.incidents[0].chain_hash if self.incidents else None
            last_hash = self.incidents[-1].chain_hash if self.incidents else None
            for incident in self.incidents:
                expected = self._hash_text(f"{previous_hash}:{incident.frame_hash}:{incident.source_id}")
                if incident.chain_hash != expected:
                    return False, first_hash, last_hash
                previous_hash = incident.chain_hash
            return True, first_hash, last_hash

    def _hash_text(self, value: str) -> str:
        return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def demo_analysis_for_session(request: SessionStartRequest, frame_number: int) -> AnalysisResult | None:
    descriptor = (request.source_path or request.camera_label).lower()
    if frame_number < 3:
        return None

    if "person_down" in descriptor:
        return AnalysisResult(
            has_incident=True,
            incident_type=IncidentType.PERSON_DOWN,
            confidence=0.92,
            severity=Severity.HIGH,
            description="Se observa una persona tendida en el suelo sin incorporarse.",
            recommended_action="Despachar apoyo y verificar condición médica de inmediato.",
            subjects_count=1,
        )
    if "fight" in descriptor:
        return AnalysisResult(
            has_incident=True,
            incident_type=IncidentType.FIGHT,
            confidence=0.95,
            severity=Severity.CRITICAL,
            description="Se detecta contacto físico agresivo entre múltiples personas.",
            recommended_action="Enviar unidad de seguridad y aislar el perímetro.",
            subjects_count=3,
        )
    if "vehicle" in descriptor:
        return AnalysisResult(
            has_incident=True,
            incident_type=IncidentType.VEHICLE_RESTRICTED,
            confidence=0.9,
            severity=Severity.HIGH,
            description="Un vehículo ingresa a una zona restringida de tránsito peatonal.",
            recommended_action="Bloquear acceso y despachar vigilancia al punto.",
            subjects_count=1,
        )
    if request.source.value == "webcam":
        return AnalysisResult(
            has_incident=True,
            incident_type=IncidentType.ROBBERY,
            confidence=0.94,
            severity=Severity.CRITICAL,
            description="Se detecta una interacción compatible con asalto en escena en vivo.",
            recommended_action="Despachar unidad de seguridad inmediatamente al punto de cámara.",
            subjects_count=2,
        )
    return AnalysisResult(
        has_incident=True,
        incident_type=IncidentType.CROWD,
        confidence=0.82,
        severity=Severity.MEDIUM,
        description="Se observa una aglomeración inusual que amerita seguimiento.",
        recommended_action="Continuar monitoreo y validar si se requiere apoyo preventivo.",
        subjects_count=18,
    )
