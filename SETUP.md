# SETUP.md — Instalación y configuración

---

## Requisitos previos

- Docker Desktop instalado y corriendo
- Python 3.12+ (para desarrollo local sin Docker)
- Node.js 20+ (para desarrollo local del frontend)
- API Key de Google Gemini: https://aistudio.google.com/apikey
- Webcam (para la demo en vivo)

---

## Opción A — Docker Compose (recomendado para demo)

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/certivision-spgg
cd certivision-spgg
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env`:
```env
GEMINI_API_KEY=AIza...tu_key_aqui
DATABASE_URL=postgresql://certivision:certivision123@db:5432/certivision_db
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
FRAME_SAMPLE_RATE=1.0
CONFIDENCE_THRESHOLD=0.75
INCIDENT_COOLDOWN_SECONDS=30
VITE_WS_URL=ws://localhost:8000/ws
VITE_API_URL=http://localhost:8000
```

### 3. Descargar videos de demo

```bash
mkdir -p backend/demo_videos
# Descarga manual desde Pexels/Pixabay y coloca los archivos aquí:
# backend/demo_videos/person_down.mp4
# backend/demo_videos/fight.mp4
# backend/demo_videos/vehicle_restricted.mp4
```

### 4. Levantar servicios

```bash
docker compose up --build
```

Servicios que se levantan:
- `db` — PostgreSQL en puerto 5432
- `backend` — FastAPI en puerto 8000
- `frontend` — React/Vite en puerto 5173

### 5. Verificar que todo funciona

```bash
# Health check del backend
curl http://localhost:8000/health

# Abrir el dashboard
open http://localhost:5173
```

---

## Opción B — Desarrollo local (sin Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Iniciar PostgreSQL aparte (o usar Docker solo para la DB)
docker run -d \
  --name certivision-db \
  -e POSTGRES_USER=certivision \
  -e POSTGRES_PASSWORD=certivision123 \
  -e POSTGRES_DB=certivision_db \
  -p 5432:5432 \
  postgres:16

# Crear tablas
python database.py --init

# Iniciar el backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Disponible en http://localhost:5173
```

---

## `requirements.txt` — Backend

```txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
websockets==12.0
google-generativeai==0.8.0
Pillow==10.4.0
opencv-python-headless==4.10.0.84
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.35
pydantic==2.8.0
pydantic-settings==2.5.0
python-dotenv==1.0.1
aiofiles==24.1.0
httpx==0.27.0
```

---

## `package.json` — Frontend (dependencias clave)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "leaflet": "^1.9.4",
    "react-leaflet": "^4.2.1",
    "lucide-react": "^0.439.0",
    "date-fns": "^3.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^3.4.0",
    "vite": "^5.4.0"
  }
}
```

---

## `docker-compose.yml`

```yaml
version: '3.9'

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: certivision
      POSTGRES_PASSWORD: certivision123
      POSTGRES_DB: certivision_db
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U certivision"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    devices:
      - /dev/video0:/dev/video0   # Webcam para la demo en vivo
    volumes:
      - ./backend/demo_videos:/app/demo_videos:ro

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    environment:
      - VITE_WS_URL=ws://localhost:8000/ws
      - VITE_API_URL=http://localhost:8000

volumes:
  pg_data:
```

---

## Solución de problemas comunes

### La webcam no es detectada dentro del contenedor

En Linux, agregar tu usuario al grupo `video`:
```bash
sudo usermod -aG video $USER
# Luego reiniciar sesión
```

En macOS, Docker Desktop requiere permisos de cámara — aceptar en System Settings > Privacy > Camera.

### Error: `GEMINI_API_KEY invalid`

Verificar en https://aistudio.google.com que la key esté activa y tenga acceso a `gemini-2.0-flash`.

### El análisis tarda más de 30 segundos

Reducir la tasa de muestreo:
```env
FRAME_SAMPLE_RATE=0.5   # 1 frame cada 2 segundos
```

O reducir la calidad del frame antes de enviar a Gemini (en `analyzer.py`, cambiar el resize a 640x480).