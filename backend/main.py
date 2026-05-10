from __future__ import annotations

import asyncio
import os
import re
import shutil
from pathlib import Path
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from urllib.request import urlopen
from uuid import UUID

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .models import (
    AuditVerifyResponse,
    Incident,
    IncidentsListResponse,
    SessionResponse,
    SessionsListResponse,
    SessionStartRequest,
    SessionStopResponse,
    SessionSummary,
)
from .analyzer import analyze_frame_b64, can_use_real_ai, get_analyzer_config
from .store import InMemoryStore, build_mock_frame

load_dotenv()

app = FastAPI(title="CertiVision SPGG", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = InMemoryStore()
connections: set[WebSocket] = set()
boot_time = datetime.now(UTC)
BASELINE_INFERENCE_INTERVAL_SECONDS = float(os.getenv("BASELINE_INFERENCE_INTERVAL_SECONDS", "5"))
ALERT_INFERENCE_INTERVAL_SECONDS = float(os.getenv("ALERT_INFERENCE_INTERVAL_SECONDS", "2.5"))
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
FRONTEND_DIST_DIR = Path("frontend/dist")
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="frontend-assets")

MOBILE_BRIDGE_HTML = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CertiVision Mobile Bridge</title>
    <style>
      body { margin:0; font-family:Arial,sans-serif; background:#08111f; color:#e2e8f0; }
      main { width:min(680px, calc(100vw - 24px)); margin:0 auto; padding:24px 0 40px; }
      .card { background:#0f172a; border:1px solid rgba(148,163,184,.18); border-radius:24px; padding:18px; margin-bottom:16px; }
      video { width:100%; border-radius:18px; background:#020617; }
      button { border:0; border-radius:999px; padding:12px 16px; background:#f59e0b; color:#111827; font-weight:700; }
      input { width:100%; padding:12px; border-radius:14px; border:1px solid rgba(148,163,184,.24); background:#111827; color:#fff; margin-bottom:12px; }
      p { line-height:1.6; color:#cbd5e1; }
      .status { font-size:14px; color:#7dd3fc; }
      .actions { display:flex; gap:12px; flex-wrap:wrap; }
    </style>
  </head>
  <body>
    <main>
      <div class="card">
        <h1>CertiVision Mobile Bridge</h1>
        <p>Conecta la camara del celular y envia snapshots en vivo al backend para analisis inmediato.</p>
        <input id="cameraLabel" value="CAM-SPGG-PHONE" />
        <div class="actions">
          <button id="startBtn">Iniciar camara y analisis</button>
          <button id="stopBtn">Detener</button>
        </div>
        <p class="status" id="status">Esperando inicio...</p>
      </div>
      <div class="card">
        <video id="video" autoplay playsinline muted></video>
      </div>
    </main>
    <script>
      const statusEl = document.getElementById("status");
      const video = document.getElementById("video");
      const canvas = document.createElement("canvas");
      let timer = null;
      let stream = null;
      let currentSessionId = null;

      async function startAnalysisSession(label) {
        const response = await fetch("/sessions/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: "mobile",
            camera_label: label,
            frame_sample_rate: 1
          })
        });
        const payload = await response.json();
        currentSessionId = payload.session_id;
        return payload;
      }

      async function stopAnalysisSession() {
        if (!currentSessionId) return;
        await fetch("/sessions/" + currentSessionId + "/stop", { method: "POST" });
        currentSessionId = null;
      }

      async function postFrame() {
        const label = document.getElementById("cameraLabel").value || "CAM-SPGG-PHONE";
        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 360;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const frame_b64 = canvas.toDataURL("image/jpeg", 0.76);
        await fetch("/live/frame", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ camera_label: label, frame_b64 })
        });
        statusEl.textContent = "Transmitiendo a " + label + " · " + new Date().toLocaleTimeString();
      }
      document.getElementById("startBtn").addEventListener("click", async () => {
        const label = document.getElementById("cameraLabel").value || "CAM-SPGG-PHONE";
        await stopAnalysisSession();
        if (timer) clearInterval(timer);
        if (stream) stream.getTracks().forEach((track) => track.stop());
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
        video.srcObject = stream;
        await video.play();
        await startAnalysisSession(label);
        timer = setInterval(() => { postFrame().catch(() => {}); }, 1200);
        await postFrame();
        statusEl.textContent = "Camara activa y analisis iniciado en " + label + ".";
      });
      document.getElementById("stopBtn").addEventListener("click", async () => {
        if (timer) {
          clearInterval(timer);
          timer = null;
        }
        if (stream) {
          stream.getTracks().forEach((track) => track.stop());
          stream = null;
        }
        video.srcObject = null;
        await stopAnalysisSession();
        statusEl.textContent = "Captura detenida.";
      });
    </script>
  </body>
</html>
"""

COMMAND_CENTER_HTML = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CertiVision Demo Command Center</title>
    <style>
      body { margin: 0; font-family: Arial, sans-serif; background: linear-gradient(180deg, #08111f, #111827); color: #e5eefc; }
      main { width: min(1100px, calc(100vw - 24px)); margin: 0 auto; padding: 24px 0 48px; }
      .hero { margin-bottom: 16px; }
      .eyebrow { font-size: 12px; text-transform: uppercase; letter-spacing: .18em; color: #7dd3fc; }
      h1 { margin: 8px 0; font-size: clamp(34px, 6vw, 64px); line-height: .95; }
      p { color: #cbd5e1; line-height: 1.6; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
      .card { background: rgba(15, 23, 42, 0.82); border: 1px solid rgba(148,163,184,.18); border-radius: 24px; padding: 18px; }
      .metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
      .metric { background: rgba(30, 41, 59, 0.9); border-radius: 18px; padding: 14px; }
      .metric span { display: block; color: #94a3b8; font-size: 12px; margin-bottom: 6px; }
      .metric strong { font-size: 20px; }
      .actions, .stack { display: flex; flex-wrap: wrap; gap: 10px; }
      button, a.button { border: 0; border-radius: 999px; padding: 12px 16px; background: linear-gradient(135deg, #fb923c, #facc15); color: #22130a; font-weight: 700; text-decoration: none; cursor: pointer; display: inline-block; }
      .secondary { background: rgba(14, 165, 233, 0.14); color: #7dd3fc; box-shadow: inset 0 0 0 1px rgba(125, 211, 252, .22); }
      input { width: 100%; padding: 12px 14px; border-radius: 16px; border: 1px solid rgba(148,163,184,.22); background: rgba(15, 23, 42, .9); color: #fff; margin-bottom: 12px; }
      .log { margin-top: 12px; background: #020617; border-radius: 18px; padding: 14px; min-height: 120px; font-size: 13px; white-space: pre-wrap; word-break: break-word; }
      video { width: 100%; border-radius: 18px; background: #020617; border: 1px solid rgba(148,163,184,.18); }
      ul { margin: 0; padding-left: 18px; color: #cbd5e1; }
      li { margin-bottom: 8px; }
      @media (max-width: 720px) { .metrics { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <div class="eyebrow">Hackathon Command Center</div>
        <h1>CertiVision<br>SPGG</h1>
        <p>Panel central para correr la demo: abrir dashboard, conectar celular, disparar sesiones de prueba y verificar que Gemini real está activo.</p>
      </section>

      <section class="grid">
        <article class="card">
          <h2>Estado del sistema</h2>
          <div class="metrics" id="metrics"></div>
          <div class="actions" style="margin-top:12px;">
            <button class="secondary" onclick="refreshHealth()">Actualizar estado</button>
          </div>
        </article>

        <article class="card">
          <h2>Rutas principales</h2>
          <div class="stack">
            <a class="button" href="/dashboard" target="_blank" rel="noreferrer">Abrir dashboard</a>
            <a class="button secondary" href="/mobile-bridge" target="_blank" rel="noreferrer">Abrir mobile bridge</a>
            <a class="button secondary" href="/sources" target="_blank" rel="noreferrer">Ver fuentes JSON</a>
            <a class="button secondary" href="/health" target="_blank" rel="noreferrer">Ver health JSON</a>
          </div>
          <p style="margin-top:12px;">Si expones este backend con ngrok, comparte la URL de <code>/mobile-bridge</code> con el celular. El dashboard se puede quedar abierto en tu laptop.</p>
        </article>
      </section>

      <section class="grid" style="margin-top:16px;">
        <article class="card">
          <h2>Webcam laptop</h2>
          <input id="webcamLabel" value="CAM-SPGG-LIVE" />
          <div class="actions">
            <button onclick="startLaptopWebcam()">Abrir webcam y analizar</button>
            <button class="secondary" onclick="stopLaptopWebcam()">Detener webcam</button>
            <button onclick="startPreset('mobile')">Iniciar celular</button>
            <button onclick="startPreset('person_down')">Correr persona caída</button>
            <button onclick="startPreset('fight')">Correr pelea</button>
          </div>
          <div style="margin-top:12px;">
            <video id="laptopVideo" autoplay playsinline muted></video>
          </div>
          <div class="log" id="sessionLog">Esperando acción...</div>
        </article>

        <article class="card">
          <h2>Video externo</h2>
          <input id="importUrl" placeholder="https://.../video.mp4" />
          <div class="actions">
            <button onclick="importSource()">Descargar video desde URL</button>
            <button class="secondary" onclick="loadSources()">Actualizar lista</button>
          </div>
          <div class="log" id="sourcesLog">Sin fuentes cargadas.</div>
        </article>
      </section>
    </main>

    <script>
      let laptopStream = null;
      let laptopTimer = null;
      let laptopSessionId = null;
      const laptopCanvas = document.createElement("canvas");

      async function refreshHealth() {
        const response = await fetch("/health");
        const health = await response.json();
        const metrics = document.getElementById("metrics");
        metrics.innerHTML = [
          ["API", health.status],
          ["Modo IA", health.ai_mode],
          ["Gemini", health.gemini_api],
          ["Modelo", health.gemini_model],
          ["Billing risk", health.real_ai_enabled ? "REAL CALLS ON" : "MOCK"],
          ["Uptime", String(health.uptime_seconds) + "s"],
        ].map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`).join("");
      }

      async function startPreset(kind) {
        const payloads = {
          mobile: { source: "mobile", camera_label: "CAM-SPGG-PHONE", frame_sample_rate: 1 },
          person_down: { source: "file", source_path: "/uploads/person_down.mp4", camera_label: "CAM-DEMO-01", frame_sample_rate: 1 },
          fight: { source: "file", source_path: "/uploads/fight.mp4", camera_label: "CAM-DEMO-02", frame_sample_rate: 1 }
        };
        const response = await fetch("/sessions/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payloads[kind]),
        });
        const data = await response.json();
        document.getElementById("sessionLog").textContent = JSON.stringify(data, null, 2);
      }

      async function startLaptopWebcam() {
        const label = document.getElementById("webcamLabel").value.trim() || "CAM-SPGG-LIVE";
        await stopLaptopWebcam();

        laptopStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        const video = document.getElementById("laptopVideo");
        video.srcObject = laptopStream;
        await video.play();

        const response = await fetch("/sessions/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: "webcam",
            webcam_index: 0,
            camera_label: label,
            frame_sample_rate: 1
          })
        });
        const data = await response.json();
        laptopSessionId = data.session_id;
        document.getElementById("sessionLog").textContent = JSON.stringify(data, null, 2);

        async function sendFrame() {
          if (!video.videoWidth) return;
          laptopCanvas.width = video.videoWidth;
          laptopCanvas.height = video.videoHeight;
          const ctx = laptopCanvas.getContext("2d");
          ctx.drawImage(video, 0, 0, laptopCanvas.width, laptopCanvas.height);
          const frame_b64 = laptopCanvas.toDataURL("image/jpeg", 0.76);
          await fetch("/live/frame", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ camera_label: label, frame_b64 })
          });
        }

        await sendFrame();
        laptopTimer = setInterval(() => { sendFrame().catch(() => {}); }, 1200);
      }

      async function stopLaptopWebcam() {
        if (laptopTimer) {
          clearInterval(laptopTimer);
          laptopTimer = null;
        }
        if (laptopStream) {
          laptopStream.getTracks().forEach((track) => track.stop());
          laptopStream = null;
        }
        const video = document.getElementById("laptopVideo");
        if (video) {
          video.srcObject = null;
        }
        if (laptopSessionId) {
          await fetch("/sessions/" + laptopSessionId + "/stop", { method: "POST" });
          laptopSessionId = null;
        }
      }

      async function importSource() {
        const url = document.getElementById("importUrl").value.trim();
        if (!url) return;
        const response = await fetch("/sources/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url }),
        });
        const data = await response.json();
        document.getElementById("sourcesLog").textContent = JSON.stringify(data, null, 2);
        await loadSources();
      }

      async function loadSources() {
        const response = await fetch("/sources");
        const data = await response.json();
        if (!data.sources.length) {
          document.getElementById("sourcesLog").textContent = "Sin fuentes cargadas.";
          return;
        }
        document.getElementById("sourcesLog").textContent = data.sources
          .map((source) => `${source.name}\\n${source.path}\\n${Math.round(source.size_bytes / 1024)} KB`)
          .join("\\n\\n");
      }

      refreshHealth().catch(() => {});
      loadSources().catch(() => {});
    </script>
  </body>
</html>
"""


async def broadcast(payload: dict) -> None:
    stale: list[WebSocket] = []
    for ws in connections:
        try:
            await ws.send_json(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        connections.discard(ws)


def extract_retry_delay_seconds(message: str) -> float | None:
    patterns = [
        r"retry in ([0-9]+(?:\.[0-9]+)?)s",
        r"'retryDelay': '([0-9]+)s'",
    ]
    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            return float(match.group(1))
    return None


async def run_mock_pipeline(session_id: UUID) -> None:
    session = await store.get_session(session_id)
    if not session:
        return
    if not can_use_real_ai():
        await broadcast(
            {
                "type": "ANALYSIS_ERROR",
                "camera_label": session.request.camera_label,
                "message": "Real AI is disabled. Set ENABLE_REAL_AI=true and configure GEMINI_API_KEY.",
            }
        )
        return
    for frame_number in range(1, 600):
        session = await store.get_session(session_id)
        if not session or session.status != "ACTIVE":
            return
        await asyncio.sleep(1.2)
        session = await store.register_frame(session_id)
        live_frame = await store.get_live_frame(session.request.camera_label)
        active_ai_mode = "gemini"
        detection_basis = "gemini_live_frame"
        if not live_frame:
            await broadcast(
                {
                    "type": "ANALYSIS_UPDATE",
                    "analysis": {
                        "session_id": str(session_id),
                        "camera_label": session.request.camera_label,
                        "source": session.request.source.value,
                        "source_path": session.request.source_path,
                        "frame_number": frame_number,
                        "frame_second": round(frame_number / session.request.frame_sample_rate, 2),
                        "status": "WAITING_FOR_VIDEO",
                        "frame_b64": build_mock_frame(
                            session.request,
                            frame_number,
                            "Esperando video real",
                            "La sesion esta activa pero aun no han llegado frames reales desde la fuente.",
                            "LOW",
                        ),
                        "model_interpretation": "Sin frame real disponible todavía.",
                        "recommended_action": "Verificar permisos de cámara, reproducción del video o bridge móvil.",
                        "incident_type": "NORMAL",
                        "severity": "LOW",
                        "confidence": 0,
                        "subjects_count": 0,
                        "ai_mode": active_ai_mode,
                        "detection_basis": "waiting_for_video",
                        "observed_signals": [],
                        "trigger_reason": "No hay frame disponible para análisis.",
                        "narrator_caption": "Esperando señal de video...",
                        "source_runtime": "live_stream" if session.request.source.value in {"webcam", "mobile", "rtsp"} else "file_stream",
                    },
                }
            )
            continue
        should_analyze, skip_reason = await store.should_analyze_frame(
            session_id=session_id,
            frame_b64=live_frame,
            now=datetime.now(UTC),
            baseline_interval_seconds=BASELINE_INFERENCE_INTERVAL_SECONDS,
            alert_interval_seconds=ALERT_INFERENCE_INTERVAL_SECONDS,
        )
        if not should_analyze:
            rate_state = await store.get_rate_control_state(session_id)
            last_analysis = (rate_state or {}).get("last_analysis") if rate_state else None
            fallback_description = "Analisis en pausa para respetar la cuota disponible de Gemini."
            await broadcast(
                {
                    "type": "ANALYSIS_UPDATE",
                    "analysis": {
                        "session_id": str(session_id),
                        "camera_label": session.request.camera_label,
                        "source": session.request.source.value,
                        "source_path": session.request.source_path,
                        "frame_number": session.frames_analyzed,
                        "frame_second": round(session.frames_analyzed / session.request.frame_sample_rate, 2),
                        "status": "SKIPPED_FRAME",
                        "frame_b64": live_frame,
                        "model_interpretation": last_analysis["description"] if last_analysis else fallback_description,
                        "recommended_action": last_analysis["recommended_action"] if last_analysis else "Esperar a que termine la ventana de backoff o reducir la frecuencia de pruebas.",
                        "incident_type": last_analysis["incident_type"] if last_analysis else "NORMAL",
                        "severity": last_analysis["severity"] if last_analysis else "LOW",
                        "confidence": last_analysis["confidence"] if last_analysis else 0,
                        "subjects_count": last_analysis["subjects_count"] if last_analysis else 0,
                        "ai_mode": active_ai_mode,
                        "detection_basis": skip_reason,
                        "observed_signals": last_analysis.get("observed_signals", []) if last_analysis else [],
                        "trigger_reason": f"Se omitió llamada a Gemini por {skip_reason}.",
                        "narrator_caption": last_analysis.get("narrator_caption") if last_analysis else "Pausa temporal por cuota de Gemini.",
                        "source_runtime": "live_stream" if session.request.source.value in {"webcam", "mobile", "rtsp"} else "file_stream",
                        "gemini_calls": (rate_state or {}).get("gemini_calls", 0),
                        "saved_calls": (rate_state or {}).get("saved_calls", 0),
                        "next_inference_at": (rate_state or {}).get("next_inference_at"),
                        "input_tokens": (rate_state or {}).get("input_tokens", 0),
                        "output_tokens": (rate_state or {}).get("output_tokens", 0),
                        "total_tokens": (rate_state or {}).get("total_tokens", 0),
                    },
                }
            )
            continue
        try:
            current_analysis = await asyncio.to_thread(analyze_frame_b64, live_frame)
            await store.register_gemini_call(
                session_id,
                input_tokens=current_analysis.input_tokens,
                output_tokens=current_analysis.output_tokens,
                total_tokens=current_analysis.total_tokens,
            )
        except Exception as exc:
            retry_delay = extract_retry_delay_seconds(str(exc))
            if retry_delay is not None:
                next_inference_at = datetime.now(UTC) + timedelta(seconds=retry_delay + 1)
                await store.register_backoff(session_id, next_inference_at)
            await broadcast(
                {
                    "type": "ANALYSIS_ERROR",
                    "camera_label": session.request.camera_label,
                    "message": str(exc),
                    "retry_delay_seconds": retry_delay,
                }
            )
            continue

        source_runtime = "live_stream" if session.request.source.value in {"webcam", "mobile", "rtsp"} else "file_stream"
        await store.append_analysis_event(session_id, frame_number, current_analysis, active_ai_mode, detection_basis)
        rate_state = await store.get_rate_control_state(session_id)
        await broadcast(
            {
                "type": "ANALYSIS_UPDATE",
                "analysis": {
                    "session_id": str(session_id),
                    "camera_label": session.request.camera_label,
                    "source": session.request.source.value,
                    "source_path": session.request.source_path,
                    "frame_number": frame_number,
                    "frame_second": round(frame_number / session.request.frame_sample_rate, 2),
                    "status": "ANALYZING",
                    "frame_b64": live_frame
                    or build_mock_frame(
                        session.request,
                        frame_number,
                        "Analizando escena",
                        current_analysis.description,
                        current_analysis.severity.value,
                    ),
                    "model_interpretation": current_analysis.description,
                    "recommended_action": current_analysis.recommended_action,
                    "incident_type": current_analysis.incident_type.value,
                    "severity": current_analysis.severity.value,
                    "confidence": current_analysis.confidence,
                    "subjects_count": current_analysis.subjects_count,
                    "ai_mode": active_ai_mode,
                    "detection_basis": detection_basis,
                    "observed_signals": current_analysis.observed_signals,
                    "trigger_reason": current_analysis.trigger_reason,
                    "narrator_caption": current_analysis.narrator_caption or current_analysis.description,
                    "source_runtime": source_runtime,
                    "gemini_calls": (rate_state or {}).get("gemini_calls", 0),
                    "saved_calls": (rate_state or {}).get("saved_calls", 0),
                    "next_inference_at": (rate_state or {}).get("next_inference_at"),
                    "input_tokens": (rate_state or {}).get("input_tokens", 0),
                    "output_tokens": (rate_state or {}).get("output_tokens", 0),
                    "total_tokens": (rate_state or {}).get("total_tokens", 0),
                },
            }
        )
        await broadcast(
            {
                "type": "HEARTBEAT",
                "timestamp": datetime.now(UTC).isoformat(),
                "cameras_active": sum(1 for item in await store.list_sessions() if item.status == "ACTIVE"),
                "frames_analyzed": sum(item.frames_analyzed for item in await store.list_sessions()),
                "incidents_today": len(store.incidents),
            }
        )
        if not current_analysis.has_incident:
            continue
        analysis = current_analysis
        incident = await store.add_incident(session_id, analysis)
        await broadcast(
            {
                "type": "ANALYSIS_UPDATE",
                "analysis": {
                    "session_id": str(session_id),
                    "camera_label": session.request.camera_label,
                    "source": session.request.source.value,
                    "source_path": session.request.source_path,
                    "frame_number": frame_number,
                    "frame_second": round(frame_number / session.request.frame_sample_rate, 2),
                    "status": "INCIDENT_DETECTED",
                    "frame_b64": incident.frame_b64,
                    "model_interpretation": analysis.description,
                    "recommended_action": analysis.recommended_action,
                    "incident_type": analysis.incident_type.value,
                    "severity": analysis.severity.value,
                    "confidence": analysis.confidence,
                    "subjects_count": analysis.subjects_count,
                    "ai_mode": active_ai_mode,
                    "detection_basis": detection_basis,
                    "observed_signals": analysis.observed_signals,
                    "trigger_reason": analysis.trigger_reason,
                    "narrator_caption": analysis.narrator_caption or analysis.description,
                    "source_runtime": source_runtime,
                    "gemini_calls": (rate_state or {}).get("gemini_calls", 0),
                    "saved_calls": (rate_state or {}).get("saved_calls", 0),
                    "next_inference_at": (rate_state or {}).get("next_inference_at"),
                    "input_tokens": (rate_state or {}).get("input_tokens", 0),
                    "output_tokens": (rate_state or {}).get("output_tokens", 0),
                    "total_tokens": (rate_state or {}).get("total_tokens", 0),
                },
            }
        )
        await broadcast({"type": "INCIDENT_ALERT", "incident": incident.model_dump(mode="json")})


@app.get("/health")
async def health() -> dict:
    analyzer_config = get_analyzer_config()
    real_ai_active = can_use_real_ai()
    return {
        "status": "ok",
        "version": app.version,
        "database": "mocked",
        "gemini_api": "configured" if analyzer_config.api_key_present else "not_configured",
        "ai_mode": "gemini" if real_ai_active else "mock",
        "gemini_key_configured": analyzer_config.api_key_present,
        "real_ai_enabled": analyzer_config.enabled,
        "gemini_model": analyzer_config.model,
        "uptime_seconds": int((datetime.now(UTC) - boot_time).total_seconds()),
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> FileResponse:
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(
            status_code=503,
            detail="Frontend build not found. Run the init script to build the dashboard first.",
        )
    return FileResponse(index_file)


@app.get("/dashboard")
async def dashboard_alias() -> FileResponse:
    return await dashboard()


@app.get("/control", response_class=HTMLResponse)
async def command_center() -> str:
    return COMMAND_CENTER_HTML


@app.get("/mobile-bridge", response_class=HTMLResponse)
async def mobile_bridge() -> str:
    return MOBILE_BRIDGE_HTML


@app.get("/sources")
async def list_sources() -> dict:
    files = sorted(
        [
            {
                "name": file.name,
                "path": f"/uploads/{file.name}",
                "size_bytes": file.stat().st_size,
            }
            for file in UPLOADS_DIR.iterdir()
            if file.is_file()
        ],
        key=lambda item: item["name"].lower(),
    )
    return {"sources": files}


@app.post("/sources/upload")
async def upload_source(file: UploadFile = File(...)) -> dict:
    filename = Path(file.filename or "upload.bin").name
    destination = UPLOADS_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "uploaded", "filename": filename, "path": f"/uploads/{filename}"}


@app.post("/sources/import")
async def import_source(payload: dict) -> dict:
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http/https URLs are supported")
    filename = Path(parsed.path).name or f"source-{int(datetime.now(UTC).timestamp())}.mp4"
    destination = UPLOADS_DIR / filename

    def _download() -> None:
        with urlopen(url, timeout=30) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)

    await asyncio.to_thread(_download)
    return {"status": "downloaded", "filename": filename, "path": f"/uploads/{filename}"}


@app.post("/live/frame")
async def ingest_live_frame(payload: dict) -> dict:
    camera_label = payload.get("camera_label")
    frame_b64 = payload.get("frame_b64")
    if not camera_label or not frame_b64:
        raise HTTPException(status_code=400, detail="camera_label and frame_b64 are required")
    await store.update_live_frame(camera_label, frame_b64)
    return {"status": "accepted", "camera_label": camera_label}


@app.post("/sessions/start", response_model=SessionResponse)
async def start_session(request: SessionStartRequest) -> SessionResponse:
    session = await store.create_session(request)
    session.task = asyncio.create_task(run_mock_pipeline(session.session_id))
    await broadcast(
        {
            "type": "CAMERA_STATUS",
            "source_id": request.camera_label,
            "status": "ACTIVE",
            "source": request.source.value,
            "source_path": request.source_path,
        }
    )
    return SessionResponse(
        session_id=session.session_id,
        status="STARTED",
        camera_label=request.camera_label,
        started_at=session.started_at,
    )


@app.post("/sessions/{session_id}/stop", response_model=SessionStopResponse)
async def stop_session(session_id: UUID) -> SessionStopResponse:
    session = await store.stop_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await broadcast(
        {
            "type": "CAMERA_STATUS",
            "source_id": session.request.camera_label,
            "status": "STOPPED",
            "source": session.request.source.value,
            "source_path": session.request.source_path,
        }
    )
    return SessionStopResponse(
        session_id=session_id,
        status="STOPPED",
        frames_analyzed=session.frames_analyzed,
        incidents_detected=session.incidents_detected,
        duration_seconds=int((datetime.now(UTC) - session.started_at).total_seconds()),
    )


@app.get("/sessions", response_model=SessionsListResponse)
async def list_sessions() -> SessionsListResponse:
    sessions = await store.list_sessions()
    return SessionsListResponse(
        sessions=[
            SessionSummary(
                session_id=session.session_id,
                camera_label=session.request.camera_label,
                source=session.request.source,
                source_path=session.request.source_path,
                status=session.status,
                started_at=session.started_at,
                frames_analyzed=session.frames_analyzed,
                incidents_detected=session.incidents_detected,
                gemini_calls=session.gemini_calls,
                saved_calls=session.saved_calls,
                next_inference_at=session.next_inference_at,
                input_tokens=session.input_tokens,
                output_tokens=session.output_tokens,
                total_tokens=session.total_tokens,
            )
            for session in sessions
        ]
    )


@app.get("/sessions/{session_id}/analysis-history")
async def session_analysis_history(session_id: UUID) -> dict:
    session = await store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    history = await store.get_analysis_history(session_id)
    return {
        "session_id": str(session_id),
        "camera_label": session.request.camera_label,
        "source": session.request.source.value,
        "history": history,
    }


@app.get("/incidents", response_model=IncidentsListResponse)
async def list_incidents(limit: int = 50, offset: int = 0) -> IncidentsListResponse:
    incidents = store.incidents[offset : offset + min(limit, 200)]
    return IncidentsListResponse(total=len(store.incidents), incidents=incidents)


@app.get("/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: UUID) -> Incident:
    incident = await store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@app.get("/audit/verify", response_model=AuditVerifyResponse)
async def audit_verify() -> AuditVerifyResponse:
    integrity_valid, first_hash, last_hash = await store.verify_integrity()
    return AuditVerifyResponse(
        integrity_valid=integrity_valid,
        total_records=len(store.incidents),
        verified_at=datetime.now(UTC),
        first_record_hash=first_hash,
        last_record_hash=last_hash,
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connections.discard(websocket)
    except Exception:
        connections.discard(websocket)


@app.on_event("shutdown")
async def shutdown() -> None:
    sessions = await store.list_sessions()
    for session in sessions:
        if session.task and not session.task.done():
            session.task.cancel()
            with suppress(asyncio.CancelledError):
                await session.task
