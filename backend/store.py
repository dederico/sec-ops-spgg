from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from .models import AnalysisResult, Incident, IncidentType, SessionStartRequest, Severity


@dataclass
class SessionState:
    session_id: UUID
    request: SessionStartRequest
    started_at: datetime
    status: str = "ACTIVE"
    frames_analyzed: int = 0
    incidents_detected: int = 0
    incident_ids: list[UUID] = field(default_factory=list)
    analysis_history: list[dict] = field(default_factory=list)
    last_analysis: AnalysisResult | None = None
    last_frame_hash: str | None = None
    gemini_calls: int = 0
    saved_calls: int = 0
    next_inference_at: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    device_location: object | None = None
    task: asyncio.Task | None = None


class InMemoryStore:
    def __init__(self) -> None:
        self.sessions: dict[UUID, SessionState] = {}
        self.incidents: list[Incident] = []
        self.live_frames: dict[str, str] = {}
        self.global_next_inference_at: datetime | None = None
        self._lock = asyncio.Lock()

    async def create_session(self, request: SessionStartRequest) -> SessionState:
        session = SessionState(
            session_id=uuid4(),
            request=request,
            started_at=datetime.now(UTC),
            device_location=request.device_location,
        )
        async with self._lock:
            self.global_next_inference_at = None
            for existing in self.sessions.values():
                if existing.status == "ACTIVE" and existing.request.camera_label == request.camera_label:
                    existing.status = "STOPPED"
                    if existing.task and not existing.task.done():
                        existing.task.cancel()
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

    async def get_analysis_history(self, session_id: UUID) -> list[dict]:
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return []
            return list(session.analysis_history)

    async def get_incident(self, incident_id: UUID) -> Incident | None:
        async with self._lock:
            for incident in self.incidents:
                if incident.id == incident_id:
                    return incident
        return None

    async def update_live_frame(self, camera_label: str, frame_b64: str, device_location: object | None = None) -> None:
        async with self._lock:
            self.live_frames[camera_label] = frame_b64
            if device_location is not None:
                for session in self.sessions.values():
                    if session.request.camera_label == camera_label:
                        session.device_location = device_location
                        session.request.device_location = device_location

    async def get_live_frame(self, camera_label: str) -> str | None:
        async with self._lock:
            return self.live_frames.get(camera_label)

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
                incident_family=analysis.incident_family,
                scenario_label=analysis.scenario_label,
                dispatch_target=analysis.dispatch_target,
                severity=analysis.severity,
                confidence=analysis.confidence,
                description=analysis.description,
                recommended_action=analysis.recommended_action,
                frame_hash=frame_hash,
                chain_hash=chain_hash,
                session_id=session_id,
                source_type=session.request.source,
                source_path=session.request.source_path,
                detected_at_second=round(session.frames_analyzed / session.request.frame_sample_rate, 2),
                observed_signals=analysis.observed_signals,
                trigger_reason=analysis.trigger_reason,
                scene_summary=self._build_scene_summary(session),
                risk_level=analysis.risk_level,
                device_location=session.device_location,
                frame_b64=self.live_frames.get(session.request.camera_label)
                or build_mock_frame(
                    session.request,
                    session.frames_analyzed,
                    analysis.incident_type.value,
                    analysis.description,
                    analysis.severity.value,
                ),
            )
            self.incidents.append(incident)
            session.incidents_detected += 1
            session.incident_ids.append(incident.id)
            return incident

    async def append_analysis_event(
        self,
        session_id: UUID,
        frame_number: int,
        analysis: AnalysisResult,
        ai_mode: str,
        detection_basis: str,
    ) -> None:
        async with self._lock:
            session = self.sessions[session_id]
            session.analysis_history.append(
                {
                    "frame_number": frame_number,
                    "frame_second": round(frame_number / session.request.frame_sample_rate, 2),
                    "description": analysis.description,
                    "signals": analysis.observed_signals,
                    "incident_type": analysis.incident_type.value,
                    "incident_family": analysis.incident_family.value,
                    "scenario_label": analysis.scenario_label,
                    "dispatch_target": analysis.dispatch_target,
                    "has_incident": analysis.has_incident,
                    "risk_level": analysis.risk_level,
                    "recommended_action": analysis.recommended_action,
                    "ai_mode": ai_mode,
                    "detection_basis": detection_basis,
                }
            )
            session.analysis_history = session.analysis_history[-20:]
            session.last_analysis = analysis

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

    def _build_scene_summary(self, session: SessionState) -> str:
        if not session.analysis_history:
            return "Sin historial previo de analisis."
        recent = session.analysis_history[-4:]
        parts = [f"t={item['frame_second']}s: {item['description']}" for item in recent]
        return " | ".join(parts)

    async def get_rate_control_state(self, session_id: UUID) -> dict | None:
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            return {
                "gemini_calls": session.gemini_calls,
                "saved_calls": session.saved_calls,
                "next_inference_at": session.next_inference_at.isoformat() if session.next_inference_at else None,
                "global_next_inference_at": self.global_next_inference_at.isoformat() if self.global_next_inference_at else None,
                "input_tokens": session.input_tokens,
                "output_tokens": session.output_tokens,
                "total_tokens": session.total_tokens,
                "last_analysis": session.last_analysis.model_dump(mode="json") if session.last_analysis else None,
            }

    async def should_analyze_frame(
        self,
        session_id: UUID,
        frame_b64: str,
        now: datetime,
        baseline_interval_seconds: float,
        alert_interval_seconds: float,
        soft_throttle_enabled: bool,
    ) -> tuple[bool, str]:
        async with self._lock:
            session = self.sessions[session_id]
            frame_hash = self._hash_text(frame_b64[:4096])
            if session.last_frame_hash == frame_hash:
                session.saved_calls += 1
                return False, "duplicate_frame"

            if session.next_inference_at and now < session.next_inference_at:
                session.saved_calls += 1
                return False, "backoff_window"

            if self.global_next_inference_at and now < self.global_next_inference_at:
                session.saved_calls += 1
                return False, "project_backoff_window"

            if not soft_throttle_enabled:
                session.last_frame_hash = frame_hash
                return True, "ready"

            target_interval = baseline_interval_seconds
            if session.last_analysis and (
                session.last_analysis.has_incident
                or session.last_analysis.severity in {Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL}
            ):
                target_interval = alert_interval_seconds

            if session.analysis_history:
                last_second = session.analysis_history[-1]["frame_second"]
                current_second = round(session.frames_analyzed / session.request.frame_sample_rate, 2)
                if current_second - last_second < target_interval:
                    session.saved_calls += 1
                    return False, "throttled_interval"

            session.last_frame_hash = frame_hash
            return True, "ready"

    async def register_gemini_call(
        self,
        session_id: UUID,
        next_inference_at: datetime | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
    ) -> None:
        async with self._lock:
            session = self.sessions[session_id]
            session.gemini_calls += 1
            session.next_inference_at = next_inference_at
            session.input_tokens += max(input_tokens, 0)
            session.output_tokens += max(output_tokens, 0)
            session.total_tokens += max(total_tokens, 0)

    async def register_backoff(self, session_id: UUID, next_inference_at: datetime) -> None:
        async with self._lock:
            session = self.sessions[session_id]
            session.next_inference_at = next_inference_at
            self.global_next_inference_at = next_inference_at


def demo_analysis_for_session(request: SessionStartRequest, frame_number: int) -> AnalysisResult | None:
    descriptor = (request.source_path or request.camera_label).lower()
    threshold = 5 if request.source.value in {"webcam", "mobile"} else 3
    if frame_number < threshold:
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
    if request.source.value in {"webcam", "mobile"}:
        return AnalysisResult(
            has_incident=True,
            incident_type=IncidentType.ROBBERY,
            confidence=0.94,
            severity=Severity.CRITICAL,
            description="Se detecta una interacción compatible con asalto en escena en vivo: una persona entra al cuadro, la víctima eleva las manos y ocurre despojo.",
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


def normal_analysis_for_session(request: SessionStartRequest, frame_number: int) -> AnalysisResult:
    descriptor = (request.source_path or request.camera_label).lower()

    if request.source.value in {"webcam", "mobile"}:
        live_descriptions = {
            1: "Live feed estable. El sistema está calibrando la escena, postura corporal y número de sujetos.",
            2: "Se mantiene vigilancia en vivo; todavía no hay interacción de riesgo confirmada.",
            3: "Aparece movimiento adicional en el encuadre. El modelo incrementa atención sobre proximidad entre sujetos.",
            4: "La distancia entre sujetos se reduce y la postura cambia. La escena queda marcada como de alta observación.",
        }
        description = live_descriptions.get(
            frame_number,
            "La escena en vivo se observa estable; el sistema sigue monitoreando interacciones y postura corporal.",
        )
    elif "fight" in descriptor:
        description = "Se observan múltiples personas en cuadro; el modelo sigue evaluando si la interacción escala a agresión."
    elif "person_down" in descriptor:
        description = "Se detecta tránsito peatonal y una zona de observación; todavía no hay incidente confirmado."
    elif "vehicle" in descriptor:
        description = "El sistema verifica si el vehículo permanece dentro de una zona restringida antes de elevar la alerta."
    else:
        description = "Escena normal en observación; se valida movimiento, densidad y contexto."

    return AnalysisResult(
        has_incident=False,
        incident_type=IncidentType.NORMAL,
        confidence=min(0.55 + frame_number * 0.08, 0.74),
        severity=Severity.LOW,
        description=description,
        recommended_action="Continuar monitoreo automático.",
        subjects_count=1 if request.source.value in {"webcam", "mobile"} else 4,
    )


def build_mock_frame(
    request: SessionStartRequest,
    frame_number: int,
    title: str,
    subtitle: str,
    severity: str,
) -> str:
    descriptor = request.source_path or request.camera_label
    accent = {
        "LOW": "#38bdf8",
        "MEDIUM": "#facc15",
        "HIGH": "#fb923c",
        "CRITICAL": "#fb7185",
    }.get(severity, "#38bdf8")
    source_label = "WEBCAM EN VIVO" if request.source.value == "webcam" else "ARCHIVO DE VIDEO"
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360' viewBox='0 0 640 360'>"
        "<defs>"
        "<linearGradient id='bg' x1='0' x2='1' y1='0' y2='1'>"
        "<stop offset='0%' stop-color='#07111f'/>"
        "<stop offset='100%' stop-color='#172554'/>"
        "</linearGradient>"
        "</defs>"
        "<rect width='640' height='360' fill='url(#bg)'/>"
        f"<rect x='24' y='24' width='592' height='312' rx='28' fill='rgba(15,23,42,0.72)' stroke='{accent}' stroke-width='3'/>"
        f"<circle cx='{160 + frame_number * 36}' cy='{180 - frame_number * 6}' r='34' fill='{accent}' opacity='0.32'/>"
        f"<rect x='{360 - frame_number * 18}' y='{108 + frame_number * 8}' width='128' height='92' rx='18' fill='{accent}' opacity='0.18'/>"
        f"<text x='48' y='62' fill='#cbd5e1' font-size='15' font-family='Arial'>{source_label}</text>"
        f"<text x='48' y='92' fill='#f8fafc' font-size='28' font-family='Arial' font-weight='700'>{escape_xml(title)}</text>"
        f"<text x='48' y='128' fill='#94a3b8' font-size='15' font-family='Arial'>Frame {frame_number} · {escape_xml(request.camera_label)}</text>"
        f"<text x='48' y='154' fill='#94a3b8' font-size='14' font-family='Arial'>{escape_xml(descriptor[-48:])}</text>"
        f"<text x='48' y='286' fill='#e2e8f0' font-size='16' font-family='Arial'>{escape_xml(subtitle[:78])}</text>"
        "<text x='48' y='310' fill='#64748b' font-size='13' font-family='Arial'>Visual sintético para demo del hackathon</text>"
        "</svg>"
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
