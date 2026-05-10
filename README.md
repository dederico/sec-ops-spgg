# CertiVision SPGG

> Monitoreo municipal autónomo con IA — sin agentes humanos, sin puntos ciegos, sin corrupción.

**TechEx Intelligent Enterprise Solutions Hackathon 2026** — Proyecto para el municipio de San Pedro Garza García, Nuevo León.

---

## ¿Qué problema resuelve?

Los municipios invierten millones en infraestructura de cámaras de seguridad. El valor se destruye en la sala de monitoreo:

- Agentes humanos pueden **eliminar evidencia** con acceso físico a grabaciones
- Operadores con intereses pueden crear **puntos ciegos intencionales**
- Un humano monitoreando 20+ pantallas pierde el **90% de incidentes** después de 22 minutos
- No existe un **log auditable** de qué vio el agente y qué decisión tomó

CertiVision reemplaza la vigilancia humana con un pipeline de visión artificial que analiza, clasifica y registra cada frame de forma **autónoma e inmutable**.

---

## Arquitectura de alto nivel

```
┌─────────────────────────────────────────────────────────────┐
│                    FUENTES DE VIDEO                          │
│  [Webcam live]  [Archivo .mp4/.avi]  [RTSP stream futuro]   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND  (Python · FastAPI)                     │
│                                                              │
│  VideoIngester → FrameSampler → GeminiAnalyzer              │
│                                      │                       │
│                                      ▼                       │
│                              IncidentClassifier              │
│                                      │                       │
│                         ┌────────────┴────────────┐         │
│                         ▼                          ▼         │
│                   AlertBroadcaster          ImmutableLogger  │
│                   (WebSocket)               (PostgreSQL)     │
└──────────┬──────────────────────────────────────────────────┘
           │ WebSocket
           ▼
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND  (React · Vite)                        │
│                                                              │
│  LiveFeed Panel │ Alert Timeline │ Incident Map │ Audit Log  │
└─────────────────────────────────────────────────────────────┘
```

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| IA / Visión | Google Gemini 2.0 Flash (multimodal) |
| Backend | Python 3.12 · FastAPI · WebSockets |
| Procesamiento video | FFmpeg · OpenCV |
| Base de datos | PostgreSQL (append-only log) |
| Frontend | React 18 · Vite · Tailwind CSS |
| Mapas | Leaflet.js |
| Contenerización | Docker · Docker Compose |

---

## Estructura del repositorio

```
certivision/
├── README.md                  ← Este archivo
├── docs/
│   ├── ARCHITECTURE.md        ← Arquitectura detallada
│   ├── API.md                 ← Endpoints del backend
│   ├── DEMO_GUIDE.md          ← Guía paso a paso para la demo
│   └── SETUP.md               ← Instalación y configuración
├── backend/
│   ├── main.py                ← Entry point FastAPI
│   ├── ingester.py            ← Ingesta de video (archivo + webcam)
│   ├── analyzer.py            ← Integración con Gemini Vision
│   ├── classifier.py          ← Clasificación de incidentes
│   ├── broadcaster.py         ← WebSocket para el frontend
│   ├── logger.py              ← Log inmutable con hashing
│   ├── models.py              ← Schemas Pydantic
│   ├── database.py            ← Conexión PostgreSQL
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── LiveFeed.jsx
│   │   │   ├── AlertTimeline.jsx
│   │   │   ├── IncidentMap.jsx
│   │   │   └── AuditLog.jsx
│   │   └── hooks/
│   │       └── useWebSocket.js
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
└── .env.example
```

---

## Inicio rápido

```bash
# 1. Clona el repositorio
git clone https://github.com/tu-usuario/certivision-spgg
cd certivision-spgg

# 2. Copia y configura variables de entorno
cp .env.example .env
# Edita .env con tu GEMINI_API_KEY

# 3. Levanta todo con Docker Compose
docker compose up --build

# 4. Abre el dashboard
open http://localhost:5173
```

---

## Documentación

- [Arquitectura detallada](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [Guía de la demo](docs/DEMO_GUIDE.md)
- [Instalación local](docs/SETUP.md)

---

## Equipo

Proyecto desarrollado para el municipio de **San Pedro Garza García, Nuevo León, México**.

> *"La corrupción necesita dos cosas: oscuridad y memoria selectiva. CertiVision elimina ambas."*