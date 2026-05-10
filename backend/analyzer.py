from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from .models import AnalysisResult, IncidentFamily, IncidentType, RiskLevel, Severity

load_dotenv()

SYSTEM_PROMPT = """
Eres un sistema de analisis de seguridad para camaras municipales.
Analiza el frame y responde con una clasificacion estructurada, conservadora y explicable.
No inventes hechos no visibles.
Usa el esquema para:
- incident_family: categoria amplia del evento
- scenario_label: etiqueta corta y flexible definida por ti, por ejemplo DOG_OFF_LEASH, CROWD_GROWING, SUSPECTED_ROBBERY, PERSON_COLLAPSED
- risk_level: GREEN, YELLOW o RED segun el riesgo para las personas visibles y para la comunidad
- dispatch_target: area municipal sugerida, por ejemplo POLICIA_MUNICIPAL, TRANSITO, PROTECCION_CIVIL, CONTROL_ANIMAL, SERVICIOS_MEDICOS, MONITOREO

Guia de riesgo:
- GREEN: observacion preventiva, bajo riesgo o sin daño inminente
- YELLOW: riesgo moderado o situacion que requiere revision/intervencion preventiva
- RED: riesgo alto, violencia, posible lesion, peligro inminente o amenaza seria a la comunidad
"""


class StructuredBbox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class StructuredAnalysisPayload(BaseModel):
    has_incident: bool
    incident_family: Literal["PUBLIC_SAFETY", "MEDICAL", "SECURITY", "TRAFFIC", "ANIMAL", "CROWD", "NORMAL", "OTHER"]
    scenario_label: str = Field(min_length=2, max_length=60)
    risk_level: Literal["GREEN", "YELLOW", "RED"]
    confidence: float
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    description: str
    recommended_action: str
    dispatch_target: str
    people_risk_summary: str = ""
    community_risk_summary: str = ""
    subjects_count: int
    bbox: StructuredBbox | None = None
    observed_signals: list[str] = Field(default_factory=list)
    trigger_reason: str
    narrator_caption: str


@dataclass
class AnalyzerConfig:
    enabled: bool
    model: str
    api_key_present: bool


def get_analyzer_config() -> AnalyzerConfig:
    enabled = os.getenv("ENABLE_REAL_AI", "").lower() == "true"
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    api_key_present = bool(os.getenv("GEMINI_API_KEY"))
    return AnalyzerConfig(enabled=enabled, model=model, api_key_present=api_key_present)


def can_use_real_ai() -> bool:
    config = get_analyzer_config()
    return config.enabled and config.api_key_present


def analyze_frame_b64(frame_b64: str) -> AnalysisResult:
    config = get_analyzer_config()
    if not (config.enabled and config.api_key_present):
        raise RuntimeError("Real AI is not enabled or GEMINI_API_KEY is missing")

    image_bytes, mime_type = decode_data_url(frame_b64)
    client = genai.Client()
    response = client.models.generate_content(
        model=config.model,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            SYSTEM_PROMPT,
        ],
        config={
            "response_mime_type": "application/json",
            "response_json_schema": StructuredAnalysisPayload.model_json_schema(),
        },
    )
    text = (response.text or "").strip()
    payload = parse_json_payload(text)
    usage = getattr(response, "usage_metadata", None)
    input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
    output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
    total_tokens = int(getattr(usage, "total_token_count", 0) or 0)
    return normalize_result(payload, input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=total_tokens)


def decode_data_url(data_url: str) -> tuple[bytes, str]:
    header, encoded = data_url.split(",", 1)
    mime_type = header.split(";")[0].split(":")[1]
    return base64.b64decode(encoded), mime_type


def parse_json_payload(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Gemini response did not contain JSON: {text}")
    return json.loads(cleaned[start : end + 1])


def normalize_result(payload: dict, input_tokens: int = 0, output_tokens: int = 0, total_tokens: int = 0) -> AnalysisResult:
    validated = StructuredAnalysisPayload.model_validate(payload)

    severity = validated.severity if validated.severity in Severity.__members__ else "LOW"

    confidence = float(validated.confidence or 0.0)
    confidence = max(0.0, min(confidence, 1.0))

    has_incident = bool(validated.has_incident) and validated.incident_family != "NORMAL"
    if not has_incident:
        incident_family = IncidentFamily.NORMAL
        incident_type = IncidentType.NORMAL
        scenario_label = "NORMAL"
        dispatch_target = "MONITOREO"
        risk_level = RiskLevel.GREEN
    else:
        incident_family = IncidentFamily[validated.incident_family]
        incident_type = infer_incident_type(incident_family, validated.scenario_label)
        scenario_label = validated.scenario_label.upper().replace(" ", "_")
        dispatch_target = normalize_dispatch_target(validated.dispatch_target, incident_family)
        risk_level = RiskLevel[validated.risk_level]

    normalized_severity = Severity[severity]
    recommended_action = normalize_recommended_action(
        incident_family,
        dispatch_target,
        validated.recommended_action,
    )

    return AnalysisResult(
        has_incident=has_incident,
        incident_type=incident_type,
        incident_family=incident_family,
        scenario_label=scenario_label,
        dispatch_target=dispatch_target,
        confidence=confidence,
        severity=normalized_severity,
        description=validated.description,
        recommended_action=recommended_action,
        subjects_count=max(int(validated.subjects_count or 0), 0),
        bbox=validated.bbox.model_dump() if validated.bbox else None,
        observed_signals=[str(item) for item in validated.observed_signals][:6],
        trigger_reason=merge_risk_context(validated.trigger_reason, validated.people_risk_summary, validated.community_risk_summary),
        narrator_caption=validated.narrator_caption or validated.description,
        risk_level=risk_level,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def infer_incident_type(incident_family: IncidentFamily, scenario_label: str) -> IncidentType:
    scenario = scenario_label.upper()
    if "ROBB" in scenario:
        return IncidentType.ROBBERY
    if "ASSAULT" in scenario or "AGGRE" in scenario:
        return IncidentType.ASSAULT
    if "DOWN" in scenario or "COLLAP" in scenario:
        return IncidentType.PERSON_DOWN
    if "FIGHT" in scenario:
        return IncidentType.FIGHT
    if "VEHICLE" in scenario or incident_family == IncidentFamily.TRAFFIC:
        return IncidentType.VEHICLE_RESTRICTED
    if "DOG" in scenario or "ANIMAL" in scenario or incident_family == IncidentFamily.ANIMAL:
        return IncidentType.ANIMAL_RISK
    if "CROWD" in scenario or incident_family == IncidentFamily.CROWD:
        return IncidentType.CROWD
    if incident_family in {IncidentFamily.SECURITY, IncidentFamily.PUBLIC_SAFETY}:
        return IncidentType.ASSAULT
    if incident_family == IncidentFamily.MEDICAL:
        return IncidentType.PERSON_DOWN
    return IncidentType.NORMAL


def normalize_dispatch_target(dispatch_target: str, incident_family: IncidentFamily) -> str:
    normalized = dispatch_target.strip().upper().replace(" ", "_")
    if normalized:
        return normalized
    if incident_family in {IncidentFamily.PUBLIC_SAFETY, IncidentFamily.SECURITY}:
        return "POLICIA_MUNICIPAL"
    if incident_family == IncidentFamily.MEDICAL:
        return "SERVICIOS_MEDICOS"
    if incident_family == IncidentFamily.TRAFFIC:
        return "TRANSITO"
    if incident_family == IncidentFamily.ANIMAL:
        return "CONTROL_ANIMAL"
    if incident_family == IncidentFamily.CROWD:
        return "PROTECCION_CIVIL"
    return "MONITOREO"


def normalize_recommended_action(incident_family: IncidentFamily, dispatch_target: str, current_action: str) -> str:
    if incident_family in {IncidentFamily.PUBLIC_SAFETY, IncidentFamily.SECURITY} and "ROBB" in dispatch_target:
        return "Despachar policia municipal y mantener seguimiento en vivo del evento."
    if incident_family == IncidentFamily.PUBLIC_SAFETY:
        return "Despachar policia municipal y mantener seguimiento en vivo del evento."
    if incident_family == IncidentFamily.SECURITY:
        return "Enviar patrulla de proximidad y documentar la agresion para intervencion inmediata."
    if incident_family == IncidentFamily.MEDICAL:
        return "Enviar apoyo medico y unidad de proximidad para verificar el estado de la persona."
    if incident_family == IncidentFamily.TRAFFIC:
        return "Avisar a transito o inspeccion municipal para retiro o contencion del vehiculo."
    if incident_family == IncidentFamily.CROWD:
        return "Activar monitoreo preventivo y valorar apoyo de proteccion civil segun densidad y comportamiento."
    if incident_family == IncidentFamily.ANIMAL:
        return "Avisar a control animal o a la perrera municipal para retiro seguro del animal."
    return current_action or f"Canalizar el evento hacia {dispatch_target} y continuar monitoreo."


def merge_risk_context(trigger_reason: str, people_risk_summary: str, community_risk_summary: str) -> str:
    parts = [trigger_reason.strip()]
    if people_risk_summary.strip():
        parts.append(f"Riesgo personas: {people_risk_summary.strip()}")
    if community_risk_summary.strip():
        parts.append(f"Riesgo comunidad: {community_risk_summary.strip()}")
    return " | ".join(part for part in parts if part)
