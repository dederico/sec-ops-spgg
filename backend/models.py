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
    NORMAL = "NORMAL"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourceType(str, Enum):
    WEBCAM = "webcam"
    FILE = "file"
    RTSP = "rtsp"


class AnalysisResult(BaseModel):
    has_incident: bool
    incident_type: IncidentType
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity
    description: str
    recommended_action: str
    subjects_count: int = Field(ge=0)
    bbox: dict[str, int] | None = None


class Incident(BaseModel):
    id: UUID
    timestamp: datetime
    source_id: str
    incident_type: IncidentType
    severity: Severity
    confidence: float
    description: str
    recommended_action: str
    frame_hash: str
    chain_hash: str
    session_id: UUID
    frame_b64: str | None = None


class SessionStartRequest(BaseModel):
    source: SourceType
    source_path: str | None = None
    webcam_index: int | None = None
    camera_label: str
    frame_sample_rate: float = Field(default=1.0, gt=0.0)


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
    status: Literal["ACTIVE", "STOPPED"]
    started_at: datetime
    frames_analyzed: int
    incidents_detected: int


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

