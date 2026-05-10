# API.md — CertiVision SPGG Backend

Base URL: `http://localhost:8000`

---

## WebSocket

### `WS /ws`

Conexión principal para recibir alertas en tiempo real.

**Mensajes del servidor → cliente:**

```json
// Alerta de incidente
{
  "type": "INCIDENT_ALERT",
  "incident": {
    "id": "3f7a1b2c-...",
    "timestamp": "2026-05-19T14:32:07Z",
    "source_id": "CAM-01",
    "incident_type": "ROBBERY",
    "severity": "CRITICAL",
    "confidence": 0.94,
    "description": "Se detecta una persona con las manos levantadas mientras otra le arrebata un objeto.",
    "recommended_action": "Despachar unidad de seguridad inmediatamente al punto de cámara.",
    "frame_b64": "data:image/jpeg;base64,/9j/4AAQ..."
  }
}

// Heartbeat cada 5 segundos
{
  "type": "HEARTBEAT",
  "timestamp": "2026-05-19T14:32:10Z",
  "cameras_active": 1,
  "frames_analyzed": 142,
  "incidents_today": 3
}

// Cambio de estado de cámara
{
  "type": "CAMERA_STATUS",
  "source_id": "CAM-01",
  "status": "ACTIVE" | "STOPPED" | "ERROR"
}
```

---

## REST Endpoints

### Sesiones de análisis

#### `POST /sessions/start`
Inicia una nueva sesión de análisis de video.

**Body:**
```json
{
  "source": "webcam" | "file" | "rtsp",
  "source_path": "/path/to/video.mp4",  // requerido si source=file
  "webcam_index": 0,                     // requerido si source=webcam
  "camera_label": "CAM-01",
  "frame_sample_rate": 1.0
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "status": "STARTED",
  "camera_label": "CAM-01",
  "started_at": "ISO8601"
}
```

---

#### `POST /sessions/{session_id}/stop`
Detiene una sesión activa.

**Response:**
```json
{
  "session_id": "uuid",
  "status": "STOPPED",
  "frames_analyzed": 287,
  "incidents_detected": 2,
  "duration_seconds": 287
}
```

---

#### `GET /sessions`
Lista todas las sesiones.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "camera_label": "CAM-01",
      "status": "ACTIVE" | "STOPPED",
      "started_at": "ISO8601",
      "frames_analyzed": 142,
      "incidents_detected": 1
    }
  ]
}
```

---

### Incidentes

#### `GET /incidents`
Lista incidentes con filtros.

**Query params:**
- `session_id` (opcional) — filtrar por sesión
- `severity` (opcional) — LOW, MEDIUM, HIGH, CRITICAL
- `incident_type` (opcional) — ROBBERY, ASSAULT, etc.
- `from` (opcional) — ISO8601 datetime
- `to` (opcional) — ISO8601 datetime
- `limit` (default: 50) — máximo 200
- `offset` (default: 0)

**Response:**
```json
{
  "total": 14,
  "incidents": [
    {
      "id": "uuid",
      "timestamp": "ISO8601",
      "source_id": "CAM-01",
      "incident_type": "ROBBERY",
      "severity": "CRITICAL",
      "confidence": 0.94,
      "description": "...",
      "recommended_action": "...",
      "frame_hash": "sha256:abc123...",
      "chain_hash": "sha256:def456..."
    }
  ]
}
```

---

#### `GET /incidents/{incident_id}`
Detalle de un incidente específico, incluyendo el frame (si fue guardado).

---

### Auditoría

#### `GET /audit/verify`
Verifica la integridad del chain hash de toda la base de datos.

**Response:**
```json
{
  "integrity_valid": true,
  "total_records": 4821,
  "verified_at": "ISO8601",
  "first_record_hash": "sha256:...",
  "last_record_hash": "sha256:..."
}
```

---

#### `GET /audit/export`
Exporta el log completo como CSV para autoridades fiscalizadoras.

**Query params:**
- `from`, `to` — rango de fechas
- `format` — `csv` (default) o `json`

**Response:** Archivo descargable

---

### Sistema

#### `GET /health`
```json
{
  "status": "ok",
  "version": "1.0.0",
  "database": "connected",
  "gemini_api": "reachable",
  "uptime_seconds": 3600
}
```