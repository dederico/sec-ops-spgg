# CertiVision SPGG

> Autonomous municipal video intelligence for safer public spaces, faster response, and auditable AI decisions.

**TechEx Intelligent Enterprise Solutions Hackathon 2026**  
Project built for **San Pedro Garza García, Nuevo León, Mexico**.

---

## English

### What It Does

CertiVision SPGG is an AI-assisted municipal monitoring system designed to analyze live camera feeds and uploaded videos, detect risk scenarios, explain what the model sees, and recommend operational responses.

The project focuses on:

- Live and uploaded video analysis
- Structured incident interpretation
- Risk classification using `GREEN / YELLOW / RED`
- Recommended municipal dispatch actions
- Session traceability and human-readable audit history
- Mobile capture with optional shared device location

### Why It Matters

Municipal camera infrastructure often loses value at the monitoring layer:

- Human operators miss events when watching too many screens
- Evidence handling can become inconsistent
- Monitoring decisions are rarely auditable
- Fast-moving incidents are hard to interpret consistently

CertiVision is built to make monitoring more explainable, structured, and operationally useful.

### Current Capabilities

- `premium-demo`: premium image-based live analysis flow
- `economic-demo`: reduced-cost demo flow with controlled inference
- `vision-premium-demo`: experimental branch where Gemini analyzes uploaded videos as real video instead of isolated snapshots

### Stack

- **Backend:** Python 3.12, FastAPI, WebSockets
- **Frontend:** React 18, Vite
- **AI:** Google Gemini
- **Video tooling:** FFmpeg

### Local Run

```bash
./init_demo.sh
```

Or with ngrok:

```bash
START_NGROK=true ./init_demo.sh
```

Then open:

```txt
http://localhost:8000/
```

### Main Flows

- Analyze this device camera from the main dashboard
- Upload a local video and analyze it
- Import a remote video URL and analyze it
- Review sessions and narrative analysis from the main UI

### Repository Branches

- `main`
- `economic-demo`
- `premium-demo`
- `vision-premium-demo`

---

## Español

### Qué Hace

CertiVision SPGG es un sistema de monitoreo municipal asistido por IA, diseñado para analizar cámaras en vivo y videos cargados, detectar escenarios de riesgo, explicar lo que ve el modelo y recomendar respuestas operativas.

El proyecto se enfoca en:

- Análisis en vivo y de videos cargados
- Interpretación estructurada de incidentes
- Clasificación de riesgo con `VERDE / AMARILLO / ROJO`
- Acciones recomendadas para despacho municipal
- Trazabilidad por sesión y auditoría legible para humanos
- Captura móvil con ubicación compartida opcional

### Por Qué Importa

La infraestructura de cámaras municipales suele perder valor en la capa de monitoreo:

- Los operadores humanos pierden eventos al vigilar demasiadas pantallas
- El manejo de evidencia puede volverse inconsistente
- Las decisiones de monitoreo rara vez son auditables
- Los incidentes rápidos son difíciles de interpretar de forma consistente

CertiVision busca hacer el monitoreo más explicable, estructurado y útil para operación real.

### Capacidades Actuales

- `premium-demo`: flujo premium de análisis en vivo basado en imágenes
- `economic-demo`: flujo demo de costo controlado
- `vision-premium-demo`: rama experimental donde Gemini analiza videos cargados como video real, no solo snapshots

### Stack

- **Backend:** Python 3.12, FastAPI, WebSockets
- **Frontend:** React 18, Vite
- **IA:** Google Gemini
- **Video:** FFmpeg

### Ejecución Local

```bash
./init_demo.sh
```

O con ngrok:

```bash
START_NGROK=true ./init_demo.sh
```

Después abre:

```txt
http://localhost:8000/
```

### Flujos Principales

- Analizar la cámara de este dispositivo desde la vista principal
- Subir un video local y analizarlo
- Importar un video remoto por URL y analizarlo
- Revisar sesiones y bitácora narrativa desde la misma interfaz

### Ramas del Repositorio

- `main`
- `economic-demo`
- `premium-demo`
- `vision-premium-demo`

---

## Notes

- Uploaded files are stored under `uploads/`
- Some demo data may be ephemeral unless you persist storage in deployment
- For production deployment, configure environment variables such as:
  - `GEMINI_API_KEY`
  - `ENABLE_REAL_AI=true`
  - `GEMINI_MODEL`
  - `GEMINI_VIDEO_FPS`
