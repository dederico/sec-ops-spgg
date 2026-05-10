# ARCHITECTURE.md — CertiVision SPGG

Arquitectura técnica detallada del sistema de monitoreo autónomo.

---

## 1. Visión general del pipeline

```
VIDEO INPUT
    │
    ▼
┌──────────────────┐
│   VideoIngester   │  Acepta: archivo .mp4/.avi, webcam (índice), RTSP URL (futuro)
│                  │  Output: stream de frames PIL.Image a 1 FPS (configurable)
└────────┬─────────┘
         │ frames (PIL.Image, timestamp, source_id)
         ▼
┌──────────────────┐
│  FrameSampler    │  Descarta frames idénticos (diff < umbral)
│                  │  Configurable: 1 frame/seg para demo, 0.5 para producción
└────────┬─────────┘
         │ frames seleccionados
         ▼
┌──────────────────┐
│  GeminiAnalyzer  │  Envía frame a Gemini 2.0 Flash con prompt estructurado
│                  │  Output: JSON con incident_type, confidence, description, bbox
└────────┬─────────┘
         │ AnalysisResult
         ▼
┌──────────────────┐
│IncidentClassifier│  Filtra falsos positivos (confidence < 0.75)
│                  │  Agrupa eventos del mismo incidente (ventana 30s)
│                  │  Genera Incident con ID único, severidad, recomendación
└────────┬─────────┘
         │ Incident (si aplica)
         ▼
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐  ┌──────────────┐
│Alerting│  │ImmutableLogger│
│(WS)    │  │(PostgreSQL)   │
└────────┘  └──────────────┘
    │                │
    ▼                ▼
Frontend         Audit Trail
(tiempo real)    (persistente)
```

---

## 2. Módulos del backend

### 2.1 VideoIngester (`ingester.py`)

Responsabilidad: abstraer la fuente de video y emitir frames normalizados.

```python
class VideoIngester:
    def __init__(self, source: str | int, fps: float = 1.0)
    async def stream_frames(self) -> AsyncGenerator[Frame, None]

@dataclass
class Frame:
    image: PIL.Image          # Frame como imagen PIL
    timestamp: datetime       # Timestamp exacto de captura
    source_id: str            # ID de la cámara/archivo
    frame_index: int          # Número de frame dentro de la sesión
    raw_bytes: bytes          # JPEG comprimido para almacenamiento
```

**Implementación clave:**
- Para webcam: usa `cv2.VideoCapture(0)` con threading para no bloquear el event loop
- Para archivos: usa FFmpeg subprocess + pipe para extraer frames a la tasa configurada
- Para RTSP (futuro): mismo approach que webcam con URL de stream

---

### 2.2 GeminiAnalyzer (`analyzer.py`)

Responsabilidad: enviar cada frame a Gemini y obtener análisis estructurado.

**Prompt del sistema (crítico):**

```python
SYSTEM_PROMPT = """
Eres un sistema de análisis de seguridad para cámaras municipales.
Analiza el frame de video y responde ÚNICAMENTE con un objeto JSON válido.
No incluyas explicaciones, markdown ni texto adicional.

Estructura de respuesta:
{
  "has_incident": boolean,
  "incident_type": "ASSAULT" | "ROBBERY" | "PERSON_DOWN" | "FIGHT" | "VEHICLE_RESTRICTED" | "CROWD" | "NORMAL",
  "confidence": float (0.0 - 1.0),
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "description": "descripción narrativa en español, máximo 2 oraciones",
  "recommended_action": "acción recomendada para el operador",
  "subjects_count": int,
  "bbox": {"x": int, "y": int, "w": int, "h": int} | null
}

Criterios de clasificación:
- ROBBERY: persona con manos levantadas, objeto siendo arrebatado, amenaza visible
- ASSAULT: contacto físico agresivo, postura de agresión
- PERSON_DOWN: persona en el suelo sin movimiento o con movimiento limitado
- FIGHT: dos o más personas en contacto físico agresivo
- VEHICLE_RESTRICTED: vehículo en zona peatonal o área prohibida
- CROWD: aglomeración inusual (>15 personas en área reducida)
- NORMAL: escena sin eventos de seguridad relevantes
"""
```

**Flujo:**
1. Convierte PIL.Image a base64 JPEG
2. Llama a `gemini-2.0-flash` con imagen + prompt
3. Parsea JSON de respuesta
4. Retorna `AnalysisResult` tipado (Pydantic)

---

### 2.3 ImmutableLogger (`logger.py`)

Responsabilidad: registrar cada análisis con integridad criptográfica.

```sql
-- Tabla principal (append-only, sin UPDATE ni DELETE)
CREATE TABLE incident_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_id   TEXT NOT NULL,
    frame_index INTEGER NOT NULL,
    frame_hash  TEXT NOT NULL,         -- SHA-256 del frame JPEG
    analysis    JSONB NOT NULL,        -- Salida completa de Gemini
    incident_id UUID,                  -- Agrupa frames del mismo incidente
    chain_hash  TEXT NOT NULL          -- SHA-256 del registro anterior + este
);

-- El chain_hash garantiza que no se puedan insertar registros retroactivos
-- Similar a una blockchain simplificada
```

**Verificación de integridad:**
```python
def verify_chain_integrity(session_id: str) -> bool:
    """
    Recorre todos los registros de una sesión en orden y
    verifica que cada chain_hash sea correcto.
    Retorna False si cualquier registro fue manipulado.
    """
```

---

### 2.4 AlertBroadcaster (`broadcaster.py`)

Responsabilidad: emitir alertas en tiempo real al frontend vía WebSocket.

```python
# Formato del mensaje WebSocket
{
    "type": "INCIDENT_ALERT",
    "incident": {
        "id": "uuid",
        "timestamp": "ISO8601",
        "type": "ROBBERY",
        "severity": "CRITICAL",
        "confidence": 0.94,
        "description": "Se detecta una persona con las manos levantadas...",
        "recommended_action": "Despachar unidad de seguridad inmediatamente",
        "source_id": "CAM-01",
        "frame_b64": "base64..."   # El frame donde ocurrió
    }
}

# Heartbeat cada 5 segundos
{
    "type": "HEARTBEAT",
    "timestamp": "ISO8601",
    "cameras_active": 1,
    "frames_analyzed": 142
}
```

---

## 3. Frontend — componentes principales

### 3.1 LiveFeed (`LiveFeed.jsx`)
- Muestra el video de la cámara activa
- Overlay de bounding box cuando hay incidente detectado
- Badge de estado: ANALIZANDO / INCIDENTE DETECTADO / NORMAL

### 3.2 AlertTimeline (`AlertTimeline.jsx`)
- Lista cronológica inversa de incidentes
- Cada alerta muestra: tipo, severidad, confianza, descripción, thumbnail del frame
- Color-coded por severidad (rojo = CRITICAL, naranja = HIGH, amarillo = MEDIUM)

### 3.3 IncidentMap (`IncidentMap.jsx`)
- Mapa de Leaflet centrado en San Pedro Garza García
- Pins con color de severidad en ubicación de cada cámara
- Click en pin → últimos 5 incidentes de esa cámara

### 3.4 AuditLog (`AuditLog.jsx`)
- Tabla de todos los registros con su hash SHA-256
- Botón "Verificar integridad" → llama al endpoint de verificación
- Exportar CSV para entidades fiscalizadoras

---

## 4. Modelos de datos (Pydantic)

```python
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

class AnalysisResult(BaseModel):
    has_incident: bool
    incident_type: IncidentType
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity
    description: str
    recommended_action: str
    subjects_count: int
    bbox: BoundingBox | None

class Incident(BaseModel):
    id: UUID
    timestamp: datetime
    source_id: str
    analysis: AnalysisResult
    frame_hash: str
    chain_hash: str
    frame_b64: str | None  # Solo para transmisión WS, no persiste
```

---

## 5. Variables de entorno (`.env`)

```env
# Gemini
GEMINI_API_KEY=your_key_here

# Base de datos
DATABASE_URL=postgresql://certivision:password@localhost:5432/certivision_db

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRAME_SAMPLE_RATE=1.0          # Frames por segundo a analizar
CONFIDENCE_THRESHOLD=0.75      # Mínimo para generar alerta
INCIDENT_COOLDOWN_SECONDS=30   # No re-alertar el mismo incidente

# Frontend
VITE_WS_URL=ws://localhost:8000/ws
VITE_API_URL=http://localhost:8000
```

---

## 6. Consideraciones de seguridad y privacidad

- **Los frames analizados no se almacenan por defecto** — solo el hash SHA-256 y el JSON de análisis
- El frame thumbnail se guarda únicamente cuando `severity >= HIGH` y solo por 72 horas
- En producción, todos los endpoints requieren autenticación JWT
- Los logs de auditoría son accesibles a la contraloría municipal mediante API key separada
- Cumple con la Ley Federal de Protección de Datos Personales en Posesión de Particulares (LFPDPPP)