from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .models import AnalysisResult, IncidentType, Severity

load_dotenv()

SYSTEM_PROMPT = """
Eres un sistema de analisis de seguridad para camaras municipales.
Analiza el frame y responde unicamente con un objeto JSON valido.
No incluyas markdown ni texto extra.

Estructura:
{
  "has_incident": boolean,
  "incident_type": "ASSAULT" | "ROBBERY" | "PERSON_DOWN" | "FIGHT" | "VEHICLE_RESTRICTED" | "CROWD" | "NORMAL",
  "confidence": float,
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "description": "descripcion breve en espanol",
  "recommended_action": "accion recomendada",
  "subjects_count": int,
  "bbox": {"x": int, "y": int, "w": int, "h": int} | null,
  "observed_signals": ["lista breve de elementos visuales relevantes"],
  "trigger_reason": "explica por que este frame si o no justifica alerta",
  "narrator_caption": "subtitulo corto de lo que esta viendo el modelo"
}

Criterios:
- ROBBERY: despojo, amenaza, victima con manos arriba o sometida
- ASSAULT: agresion fisica directa
- PERSON_DOWN: persona tirada en piso o incapacitada
- FIGHT: dos o mas personas en confrontacion fisica
- VEHICLE_RESTRICTED: vehiculo en zona peatonal o prohibida
- CROWD: concentracion inusual de personas
- NORMAL: sin evento relevante
"""


@dataclass
class AnalyzerConfig:
    enabled: bool
    model: str
    api_key_present: bool


def get_analyzer_config() -> AnalyzerConfig:
    enabled = os.getenv("ENABLE_REAL_AI", "").lower() == "true"
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
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
    incident_type = payload.get("incident_type", "NORMAL")
    if incident_type not in IncidentType.__members__:
        incident_type = "NORMAL"

    severity = payload.get("severity", "LOW")
    if severity not in Severity.__members__:
        severity = "LOW"

    confidence = float(payload.get("confidence", 0.0) or 0.0)
    confidence = max(0.0, min(confidence, 1.0))

    has_incident = bool(payload.get("has_incident")) and incident_type != "NORMAL"
    if not has_incident:
        incident_type = "NORMAL"

    return AnalysisResult(
        has_incident=has_incident,
        incident_type=IncidentType[incident_type],
        confidence=confidence,
        severity=Severity[severity],
        description=str(payload.get("description", "Sin descripcion disponible.")),
        recommended_action=str(payload.get("recommended_action", "Continuar monitoreo.")),
        subjects_count=max(int(payload.get("subjects_count", 0) or 0), 0),
        bbox=payload.get("bbox"),
        observed_signals=[str(item) for item in payload.get("observed_signals", [])][:6],
        trigger_reason=str(payload.get("trigger_reason", "")),
        narrator_caption=str(payload.get("narrator_caption", payload.get("description", ""))),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )
