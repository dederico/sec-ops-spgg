from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    ROBBERY = "ROBBERY"
    ASSAULT = "ASSAULT"
    PERSON_DOWN = "PERSON_DOWN"
    FIGHT = "FIGHT"
    VEHICLE_RESTRICTED = "VEHICLE_RESTRICTED"
    CROWD = "CROWD"
    ANIMAL_RISK = "ANIMAL_RISK"
    NORMAL = "NORMAL"


class IncidentFamily(str, Enum):
    PUBLIC_SAFETY = "PUBLIC_SAFETY"
    MEDICAL = "MEDICAL"
    SECURITY = "SECURITY"
    TRAFFIC = "TRAFFIC"
    ANIMAL = "ANIMAL"
    CROWD = "CROWD"
    NORMAL = "NORMAL"
    OTHER = "OTHER"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceType(str, Enum):
    WEBCAM = "webcam"
    MOBILE = "mobile"
    FILE = "file"
    RTSP = "rtsp"


class RiskLevel(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class DeviceLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: float | None = None
    shared_at: datetime | None = None
    label: str | None = None


class AnalysisResult(BaseModel):
    has_incident: bool
    incident_type: IncidentType
    incident_family: IncidentFamily = IncidentFamily.NORMAL
    scenario_label: str = "NORMAL"
    dispatch_target: str = "MONITOREO"
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity
    description: str
    recommended_action: str
    subjects_count: int = Field(ge=0)
    bbox: dict[str, int] | None = None
    observed_signals: list[str] = Field(default_factory=list)
    trigger_reason: str = ""
    narrator_caption: str = ""
    risk_level: RiskLevel = RiskLevel.GREEN
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class Incident(BaseModel):
    id: UUID
    timestamp: datetime
    source_id: str
    incident_type: IncidentType
    incident_family: IncidentFamily = IncidentFamily.NORMAL
    scenario_label: str = "NORMAL"
    dispatch_target: str = "MONITOREO"
    severity: Severity
    confidence: float
    description: str
    recommended_action: str
    frame_hash: str
    chain_hash: str
    session_id: UUID
    source_type: SourceType | None = None
    source_path: str | None = None
    detected_at_second: float | None = None
    observed_signals: list[str] = Field(default_factory=list)
    trigger_reason: str = ""
    scene_summary: str = ""
    frame_b64: str | None = None
    risk_level: RiskLevel = RiskLevel.GREEN
    device_location: DeviceLocation | None = None


class SessionStartRequest(BaseModel):
    source: SourceType
    source_path: str | None = None
    webcam_index: int | None = None
    camera_label: str
    frame_sample_rate: float = Field(default=1.0, gt=0.0)
    device_location: DeviceLocation | None = None


class LiveFrameRequest(BaseModel):
    camera_label: str
    frame_b64: str
    device_location: DeviceLocation | None = None


class SessionResponse(BaseModel):
    session_id: UUID
    status: Literal["STARTED", "STOPPED", "ACTIVE"]
    camera_label: str
    started_at: datetime


class SessionStopResponse(BaseModel):
    session_id: UUID
    status: Literal["STOPPED"]
    frames_analyzed: int
    incidents_detected: int
    duration_seconds: int


class SessionSummary(BaseModel):
    session_id: UUID
    camera_label: str
    source: SourceType
    source_path: str | None = None
    status: Literal["ACTIVE", "STOPPED"]
    started_at: datetime
    frames_analyzed: int
    incidents_detected: int
    gemini_calls: int = 0
    saved_calls: int = 0
    next_inference_at: datetime | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    device_location: DeviceLocation | None = None


class SessionsListResponse(BaseModel):
    sessions: list[SessionSummary]


class IncidentsListResponse(BaseModel):
    total: int
    incidents: list[Incident]


class AuditVerifyResponse(BaseModel):
    integrity_valid: bool
    total_records: int
    verified_at: datetime
    first_record_hash: str | None
    last_record_hash: str | None
