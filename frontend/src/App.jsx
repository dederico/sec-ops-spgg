import { useEffect, useRef, useState } from "react";

const API_URL = window.location.origin;
const WS_PROTOCOL = window.location.protocol === "https:" ? "wss:" : "ws:";
const WS_URL = `${WS_PROTOCOL}//${window.location.host}/ws`;
const MOBILE_BRIDGE_URL = `${API_URL}/mobile-bridge`;

function App() {
  const [health, setHealth] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [activityFeed, setActivityFeed] = useState([]);
  const [audit, setAudit] = useState(null);
  const [latestAnalysis, setLatestAnalysis] = useState(null);
  const [latestAlert, setLatestAlert] = useState(null);
  const [liveMode, setLiveMode] = useState(false);
  const [sources, setSources] = useState([]);
  const [importUrl, setImportUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [activeCameraLabel, setActiveCameraLabel] = useState("CAM-SPGG-LIVE");
  const [deviceMode, setDeviceMode] = useState("observer");
  const [activeSessionId, setActiveSessionId] = useState("");
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const localVideoRef = useRef(null);
  const captureCanvasRef = useRef(null);
  const cameraStreamRef = useRef(null);
  const captureTimerRef = useRef(null);
  const fileVideoRef = useRef(null);
  const fileCaptureTimerRef = useRef(null);
  const [activeMediaUrl, setActiveMediaUrl] = useState("");
  const [activeMediaType, setActiveMediaType] = useState("");

  async function refreshAll() {
    const [healthResponse, sessionsResponse, incidentsResponse, auditResponse, sourcesResponse] = await Promise.all([
      fetch(`${API_URL}/health`),
      fetch(`${API_URL}/sessions`),
      fetch(`${API_URL}/incidents`),
      fetch(`${API_URL}/audit/verify`),
      fetch(`${API_URL}/sources`),
    ]);
    setHealth(await healthResponse.json());
    setSessions((await sessionsResponse.json()).sessions);
    setIncidents((await incidentsResponse.json()).incidents);
    setAudit(await auditResponse.json());
    setSources((await sourcesResponse.json()).sources);
  }

  function sourceLabel(source) {
    if (source === "webcam") return "Webcam / Live feed";
    if (source === "mobile") return "Celular / Live bridge";
    if (source === "rtsp") return "Cámara IP";
    return "Archivo de video";
  }

  function formatDateTime(value) {
    if (!value) return "--";
    return new Date(value).toLocaleString();
  }

  function appendActivity(entry) {
    setActivityFeed((current) => [entry, ...current].slice(0, 18));
  }

  function summarizeEvent(payload) {
    if (payload.type === "ANALYSIS_UPDATE") {
      const second = payload.analysis.frame_second ?? 0;
      const source = payload.analysis.camera_label;
      const basis = payload.analysis.detection_basis || "analysis";
      if (payload.analysis.status === "INCIDENT_DETECTED") {
        return {
          tone: "alert",
          title: `${payload.analysis.incident_type} detectado`,
          detail: `${source} · t=${second}s · ${payload.analysis.trigger_reason || payload.analysis.model_interpretation}`,
        };
      }
      return {
        tone: "info",
        title: `Analizando ${source}`,
        detail: `t=${second}s · ${basis} · ${payload.analysis.narrator_caption || payload.analysis.model_interpretation}`,
      };
    }
    if (payload.type === "INCIDENT_ALERT") {
      return {
        tone: "alert",
        title: `Alerta ${payload.incident.incident_type}`,
        detail: `${payload.incident.source_id} · ${Math.round(payload.incident.confidence * 100)}% · ${payload.incident.description}`,
      };
    }
    if (payload.type === "CAMERA_STATUS") {
      return {
        tone: payload.status === "ACTIVE" ? "info" : "neutral",
        title: `Camara ${payload.source_id}`,
        detail: `Estado ${payload.status}${payload.source_path ? ` · ${payload.source_path}` : ""}`,
      };
    }
    if (payload.type === "ANALYSIS_ERROR") {
      return {
        tone: "alert",
        title: `Error de analisis en ${payload.camera_label}`,
        detail: payload.message,
      };
    }
    if (payload.type === "HEARTBEAT") {
      return {
        tone: "neutral",
        title: "Heartbeat del sistema",
        detail: `${payload.cameras_active} camaras activas · ${payload.frames_analyzed} frames analizados`,
      };
    }
    return {
      tone: "neutral",
      title: payload.type,
      detail: "Evento del sistema",
    };
  }

  async function refreshHistory(sessionId) {
    if (!sessionId) {
      setAnalysisHistory([]);
      return;
    }
    const response = await fetch(`${API_URL}/sessions/${sessionId}/analysis-history`);
    if (!response.ok) {
      return;
    }
    const payload = await response.json();
    setAnalysisHistory(payload.history || []);
  }

  useEffect(() => {
    if (!sessions.length) {
      if (selectedSessionId) {
        setSelectedSessionId("");
        setAnalysisHistory([]);
      }
      return;
    }

    const stillExists = sessions.some((session) => session.session_id === selectedSessionId);
    if (selectedSessionId && stillExists) {
      return;
    }

    const preferredSession =
      sessions.find((session) => session.session_id === activeSessionId) ||
      sessions.find((session) => session.status === "ACTIVE") ||
      sessions[0];

    if (preferredSession) {
      setSelectedSessionId(preferredSession.session_id);
    }
  }, [sessions, activeSessionId, selectedSessionId]);

  useEffect(() => {
    if (selectedSessionId) {
      refreshHistory(selectedSessionId);
    }
  }, [selectedSessionId]);

  useEffect(() => {
    refreshAll();
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => ws.send("subscribe");
    ws.onmessage = (message) => {
      const payload = JSON.parse(message.data);
      appendActivity({ ...summarizeEvent(payload), timestamp: new Date().toLocaleTimeString() });
      if (payload.type === "ANALYSIS_UPDATE") {
        setLatestAnalysis(payload.analysis);
        setLiveMode(payload.analysis.source === "webcam" || payload.analysis.source === "mobile");
        setAnalysisHistory((current) => {
          const next = [
            ...current,
            {
              frame_number: payload.analysis.frame_number,
              frame_second: payload.analysis.frame_second,
              description: payload.analysis.model_interpretation,
              signals: payload.analysis.observed_signals || [],
              incident_type: payload.analysis.incident_type,
              has_incident: payload.analysis.status === "INCIDENT_DETECTED",
              ai_mode: payload.analysis.ai_mode,
              detection_basis: payload.analysis.detection_basis,
              trigger_reason: payload.analysis.trigger_reason,
            },
          ];
          return next.slice(-20);
        });
      }
      if (payload.type === "INCIDENT_ALERT") {
        setLatestAlert(payload.incident);
        setIncidents((current) => [payload.incident, ...current]);
      }
      refreshAll();
    };
    return () => {
      ws.close();
      stopLocalCapture();
      stopFilePlayback();
    };
  }, []);

  async function startSession(payload) {
    if (activeSessionId) {
      await fetch(`${API_URL}/sessions/${activeSessionId}/stop`, { method: "POST" });
    }
    setLiveMode(payload.source === "webcam" || payload.source === "mobile");
    setLatestAlert(null);
    setLatestAnalysis(null);
    const response = await fetch(`${API_URL}/sessions/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    setActiveSessionId(data.session_id);
    setSelectedSessionId(data.session_id);
    setAnalysisHistory([]);
    refreshAll();
  }

  async function stopSession(sessionId) {
    const session = sessions.find((item) => item.session_id === sessionId);
    if (session?.source === "webcam") {
      stopLocalCapture();
    }
    if (session?.source === "file") {
      stopFilePlayback();
    }
    await fetch(`${API_URL}/sessions/${sessionId}/stop`, { method: "POST" });
    if (sessionId === activeSessionId) {
      setActiveSessionId("");
    }
    if (sessionId === selectedSessionId) {
      setSelectedSessionId("");
      setAnalysisHistory([]);
    }
    refreshAll();
  }

  function stopLocalCapture() {
    if (captureTimerRef.current) {
      clearInterval(captureTimerRef.current);
      captureTimerRef.current = null;
    }
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current = null;
    }
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = null;
    }
  }

  function stopFilePlayback() {
    if (fileCaptureTimerRef.current) {
      clearInterval(fileCaptureTimerRef.current);
      fileCaptureTimerRef.current = null;
    }
    if (fileVideoRef.current) {
      fileVideoRef.current.pause();
      fileVideoRef.current.src = "";
      fileVideoRef.current.load();
    }
    setActiveMediaType("");
    setActiveMediaUrl("");
  }

  async function postCurrentFrame(cameraLabel) {
    const video = localVideoRef.current;
    if (!video || !video.videoWidth) {
      return;
    }
    const canvas = captureCanvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const frame_b64 = canvas.toDataURL("image/jpeg", 0.92);
    await fetch(`${API_URL}/live/frame`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ camera_label: cameraLabel, frame_b64 }),
    });
  }

  async function startBrowserLiveAnalysis() {
    const cameraLabel = activeCameraLabel || "CAM-SPGG-LIVE";
    stopFilePlayback();
    stopLocalCapture();
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    cameraStreamRef.current = stream;
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = stream;
      await localVideoRef.current.play();
    }
    await startSession({
      source: "webcam",
      webcam_index: 0,
      camera_label: cameraLabel,
      frame_sample_rate: 1,
    });
    await postCurrentFrame(cameraLabel);
    captureTimerRef.current = setInterval(() => {
      postCurrentFrame(cameraLabel).catch(() => {});
    }, 1200);
    setActiveMediaType("webcam");
    setDeviceMode("publisher");
  }

  async function startThisDeviceCamera(sourceType = "mobile") {
    const cameraLabel = activeCameraLabel || (sourceType === "mobile" ? "CAM-SPGG-PHONE" : "CAM-SPGG-LIVE");
    stopFilePlayback();
    stopLocalCapture();
    const stream = await navigator.mediaDevices.getUserMedia({
      video: sourceType === "mobile" ? { facingMode: "environment" } : true,
      audio: false,
    });
    cameraStreamRef.current = stream;
    if (localVideoRef.current) {
      localVideoRef.current.srcObject = stream;
      await localVideoRef.current.play();
    }
    await startSession({
      source: sourceType,
      webcam_index: sourceType === "webcam" ? 0 : undefined,
      camera_label: cameraLabel,
      frame_sample_rate: 1,
    });
    await postCurrentFrame(cameraLabel);
    captureTimerRef.current = setInterval(() => {
      postCurrentFrame(cameraLabel).catch(() => {});
    }, 1200);
    setActiveMediaType(sourceType);
    setDeviceMode("publisher");
  }

  async function uploadVideo() {
    if (!selectedFile) {
      return;
    }
    const formData = new FormData();
    formData.append("file", selectedFile);
    await fetch(`${API_URL}/sources/upload`, { method: "POST", body: formData });
    setSelectedFile(null);
    refreshAll();
  }

  async function importVideoUrl() {
    if (!importUrl.trim()) {
      return;
    }
    await fetch(`${API_URL}/sources/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: importUrl.trim() }),
    });
    setImportUrl("");
    refreshAll();
  }

  async function postFileFrame(cameraLabel) {
    const video = fileVideoRef.current;
    if (!video || !video.videoWidth) {
      return;
    }
    const canvas = captureCanvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const frame_b64 = canvas.toDataURL("image/jpeg", 0.92);
    await fetch(`${API_URL}/live/frame`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ camera_label: cameraLabel, frame_b64 }),
    });
  }

  async function startUploadedSource(path, name) {
    stopLocalCapture();
    stopFilePlayback();
    const cameraLabel = `FILE-${name.replace(/\.[^.]+$/, "").toUpperCase()}`;
    await startSession({
      source: "file",
      source_path: path,
      camera_label: cameraLabel,
      frame_sample_rate: 1,
    });
    setActiveMediaType("file");
    setActiveMediaUrl(`${API_URL}${path}`);
    setTimeout(async () => {
      const video = fileVideoRef.current;
      if (!video) {
        return;
      }
      video.src = `${API_URL}${path}`;
      await video.play();
      await postFileFrame(cameraLabel);
      fileCaptureTimerRef.current = setInterval(() => {
        postFileFrame(cameraLabel).catch(() => {});
      }, 1200);
    }, 150);
  }

  function renderPrimaryMedia() {
    if (activeMediaType === "file" && activeMediaUrl) {
      return <video ref={fileVideoRef} className="hero-frame" controls autoPlay muted playsInline />;
    }
    if (!latestAnalysis) {
      return <div className="empty-frame">Inicia una demo para ver la interpretación en vivo.</div>;
    }
    return <img src={latestAnalysis.frame_b64} alt={latestAnalysis.incident_type} className="hero-frame" />;
  }

  const selectedSession = sessions.find((session) => session.session_id === selectedSessionId) || null;

  return (
    <main className="shell">
      <canvas ref={captureCanvasRef} className="hidden-canvas" />
      <section className="hero">
        <p className="eyebrow">Hackathon MVP</p>
        <h1>CertiVision SPGG</h1>
        <p className="lede">
          Mostrar la fuente, la interpretación del modelo y el instante exacto en que se convierte en alerta.
        </p>
        <div className="hero-badges">
          <span className={`hero-pill ${liveMode ? "hero-pill-live" : ""}`}>
            {liveMode ? "LIVE ANALYSIS PRIORITARIO" : "Modo demo por archivo"}
          </span>
          <span className="hero-pill">El AHA moment ocurre cuando la escena cambia y el sistema lo verbaliza</span>
          <span className="hero-pill">
            Endpoint unico: abre esta misma pagina en laptop y celular
          </span>
        </div>
      </section>

      <section className="aha-grid">
        <article className="stage-card">
          <div className="stage-header">
            <div>
              <p className="section-kicker">Fuente Analizada</p>
              <h2>
                {latestAnalysis ? latestAnalysis.camera_label : "Esperando una sesión"}
              </h2>
            </div>
            <span className={`status-pill ${latestAnalysis?.status === "INCIDENT_DETECTED" ? "danger" : "live"}`}>
              {latestAnalysis?.status === "INCIDENT_DETECTED"
                ? "ALERTA DISPARADA"
                : latestAnalysis?.source === "webcam"
                  ? "LIVE ANALYSIS"
                  : "ANALIZANDO"}
            </span>
          </div>
          <div className="frame-shell">
            {renderPrimaryMedia()}
            {latestAnalysis ? (
              <div className="frame-overlay">
                <div className="overlay-top">
                  <span className="overlay-pill">{latestAnalysis.source_runtime || "stream"}</span>
                  <span className="overlay-pill">{latestAnalysis.detection_basis || "unknown_basis"}</span>
                  <span className="overlay-pill">t={latestAnalysis.frame_second ?? 0}s</span>
                </div>
                <div className="overlay-cc">
                  {latestAnalysis.narrator_caption || latestAnalysis.model_interpretation}
                </div>
              </div>
            ) : null}
          </div>
          <div className="source-meta">
            <div>
              <span>Origen</span>
              <strong>
                {latestAnalysis?.source === "webcam"
                  ? "Webcam / Live feed"
                  : latestAnalysis?.source === "mobile"
                    ? "Celular / Live bridge"
                    : "Archivo de video"}
              </strong>
            </div>
            <div>
              <span>Ruta o stream</span>
              <strong>{latestAnalysis?.source_path || "Entrada en vivo del operador"}</strong>
            </div>
            <div>
              <span>Segundo observado</span>
              <strong>{latestAnalysis?.frame_second ?? 0}s</strong>
            </div>
            <div>
              <span>Frame</span>
              <strong>{latestAnalysis?.frame_number || 0}</strong>
            </div>
          </div>
        </article>

        <article className="aha-card">
          <p className="section-kicker">Interpretación del modelo</p>
          <h2>{latestAnalysis?.incident_type || "NORMAL"}</h2>
          <p className="aha-copy">
            {latestAnalysis?.model_interpretation ||
              "Aquí debe aparecer la lectura del modelo sobre lo que está viendo en la escena."}
          </p>
          <div className="metrics">
            <div>
              <span>Confianza</span>
              <strong>{latestAnalysis ? `${Math.round(latestAnalysis.confidence * 100)}%` : "--"}</strong>
            </div>
            <div>
              <span>Severidad</span>
              <strong>{latestAnalysis?.severity || "--"}</strong>
            </div>
            <div>
              <span>Sujetos</span>
              <strong>{latestAnalysis?.subjects_count ?? "--"}</strong>
            </div>
            <div>
              <span>Tokens entrada</span>
              <strong>{latestAnalysis?.input_tokens ?? "--"}</strong>
            </div>
            <div>
              <span>Tokens salida</span>
              <strong>{latestAnalysis?.output_tokens ?? "--"}</strong>
            </div>
            <div>
              <span>Tokens total</span>
              <strong>{latestAnalysis?.total_tokens ?? "--"}</strong>
            </div>
          </div>
          <div className="recommendation">
            <span>Acción recomendada</span>
            <p>{latestAnalysis?.recommended_action || "Sin recomendación todavía."}</p>
          </div>
          <div className="recommendation">
            <span>Por qué lo reporta</span>
            <p>{latestAnalysis?.trigger_reason || "Sin justificación detallada todavía."}</p>
          </div>
          <div className="signals-block">
            <span>Elementos observados</span>
            <ul className="signals-list">
              {(latestAnalysis?.observed_signals || []).map((signal) => (
                <li key={signal}>{signal}</li>
              ))}
            </ul>
          </div>
        </article>

        <article className={`alarm-card ${latestAlert ? "alarm-on" : ""}`}>
          <p className="section-kicker">AHA Moment</p>
          <h2>{latestAlert ? `${latestAlert.incident_type} detectado` : "Sin alarma aún"}</h2>
          <p className="aha-copy">
            {latestAlert
              ? latestAlert.description
              : "Cuando el modelo cruce el umbral, esta tarjeta cambia a estado crítico y deja visible el incidente."}
          </p>
          <div className="alarm-strip">
            <span>Estado</span>
            <strong>{latestAlert ? latestAlert.severity : "Observación"}</strong>
          </div>
          <div className="alarm-strip">
            <span>Detonante</span>
            <strong>{latestAlert ? `${Math.round(latestAlert.confidence * 100)}% confianza` : "Esperando"}</strong>
          </div>
          <div className="alarm-strip">
            <span>Segundo disparado</span>
            <strong>{latestAlert?.detected_at_second ?? "--"}s</strong>
          </div>
          <div className="alarm-strip">
            <span>Resumen de escena</span>
            <strong>{latestAlert?.scene_summary || "Sin resumen todavía"}</strong>
          </div>
        </article>
      </section>

      <section className="grid">
        <article className="card">
          <h2>Sistema</h2>
          <div className="system-grid">
            <div>
              <span>API</span>
              <strong>{health?.status || "--"}</strong>
            </div>
            <div>
              <span>DB</span>
              <strong>{health?.database || "--"}</strong>
            </div>
            <div>
              <span>Gemini</span>
              <strong>{health?.gemini_api || "--"}</strong>
            </div>
            <div>
              <span>Modo IA</span>
              <strong>{health?.ai_mode || "--"}</strong>
            </div>
            <div>
              <span>Integridad</span>
              <strong>{audit?.integrity_valid ? "VALIDA" : "PENDIENTE"}</strong>
            </div>
          </div>
        </article>

        <article className="card">
          <h2>Captura en este dispositivo</h2>
          <p className="helper-copy">
            Usa esta misma vista tanto en laptop como en celular. Ya no necesitas cambiar de endpoint.
          </p>
          <div className="actions">
            <input
              className="app-input"
              value={activeCameraLabel}
              onChange={(event) => setActiveCameraLabel(event.target.value)}
              placeholder="Etiqueta de camara"
            />
            <button onClick={() => startThisDeviceCamera("webcam")}>Usar cámara de esta laptop</button>
            <button onClick={() => startThisDeviceCamera("mobile")}>Usar cámara de este celular</button>
          </div>
          <p className="helper-copy">
            Si abres esta página desde el teléfono por `ngrok`, el botón de celular inicia cámara y análisis aquí mismo.
          </p>
          <div className="frame-shell compact">
            <video ref={localVideoRef} className="hero-frame" autoPlay muted playsInline />
          </div>
        </article>

        <article className="card">
          <h2>Videos externos</h2>
          <p className="helper-copy">Sube un archivo local o descarga uno desde una URL publica. Luego puedes disparar el analisis desde la lista.</p>
          <div className="stacked-actions">
            <input className="app-input" type="file" accept="video/*" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} />
            <button onClick={uploadVideo} disabled={!selectedFile}>Subir video</button>
            <input
              className="app-input"
              value={importUrl}
              onChange={(event) => setImportUrl(event.target.value)}
              placeholder="https://.../video.mp4"
            />
            <button onClick={importVideoUrl} disabled={!importUrl.trim()}>Descargar desde URL</button>
          </div>
          <ul className="list source-list">
            {sources.map((source) => (
              <li key={source.path}>
                <div className="session-head">
                  <strong>{source.name}</strong>
                  <button onClick={() => startUploadedSource(source.path, source.name)}>Analizar</button>
                </div>
                <div>{source.path}</div>
                <div>{Math.round(source.size_bytes / 1024)} KB</div>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="sessions-section">
        <div className="section-headline">
          <div>
            <p className="section-kicker">Sesiones</p>
            <h2>Explorador de sesiones</h2>
          </div>
          <p className="helper-copy">
            Aquí puedes entrar a cada sesión, ver qué interpretó el modelo y leer la secuencia completa sin abrir JSON.
          </p>
        </div>
        <div className="sessions-layout">
          <aside className="session-rail">
            {sessions.length ? (
              sessions.map((session) => (
                <button
                  key={session.session_id}
                  className={`session-tab ${selectedSessionId === session.session_id ? "session-tab-active" : ""}`}
                  onClick={() => setSelectedSessionId(session.session_id)}
                >
                  <div className="session-tab-top">
                    <strong>{session.camera_label}</strong>
                    <span className={`status-pill ${session.status === "ACTIVE" ? "live" : ""}`}>{session.status}</span>
                  </div>
                  <div className="session-tab-meta">
                    {sourceLabel(session.source)} · {session.source_path || "live"}
                  </div>
                  <div className="session-tab-stats">
                    <span>{session.frames_analyzed} frames</span>
                    <span>{session.incidents_detected} incidentes</span>
                    <span>{session.total_tokens} tokens</span>
                  </div>
                </button>
              ))
            ) : (
              <div className="empty-session-state">Todavía no hay sesiones registradas.</div>
            )}
          </aside>

          <div className="session-detail">
            {selectedSession ? (
              <>
                <div className="session-detail-header">
                  <div>
                    <p className="section-kicker">Sesión seleccionada</p>
                    <h3>{selectedSession.camera_label}</h3>
                  </div>
                  <div className="session-detail-actions">
                    {selectedSession.status === "ACTIVE" ? (
                      <button onClick={() => stopSession(selectedSession.session_id)}>Detener sesión</button>
                    ) : null}
                    <button onClick={() => refreshHistory(selectedSession.session_id)}>Actualizar bitácora</button>
                  </div>
                </div>

                <div className="session-detail-grid">
                  <div>
                    <span>Origen</span>
                    <strong>{sourceLabel(selectedSession.source)}</strong>
                  </div>
                  <div>
                    <span>Ruta o stream</span>
                    <strong>{selectedSession.source_path || "Entrada en vivo del operador"}</strong>
                  </div>
                  <div>
                    <span>Inició</span>
                    <strong>{formatDateTime(selectedSession.started_at)}</strong>
                  </div>
                  <div>
                    <span>Estado</span>
                    <strong>{selectedSession.status}</strong>
                  </div>
                  <div>
                    <span>Frames analizados</span>
                    <strong>{selectedSession.frames_analyzed}</strong>
                  </div>
                  <div>
                    <span>Incidentes detectados</span>
                    <strong>{selectedSession.incidents_detected}</strong>
                  </div>
                  <div>
                    <span>Llamadas a Gemini</span>
                    <strong>{selectedSession.gemini_calls}</strong>
                  </div>
                  <div>
                    <span>Llamadas ahorradas</span>
                    <strong>{selectedSession.saved_calls}</strong>
                  </div>
                  <div>
                    <span>Tokens de entrada</span>
                    <strong>{selectedSession.input_tokens}</strong>
                  </div>
                  <div>
                    <span>Tokens de salida</span>
                    <strong>{selectedSession.output_tokens}</strong>
                  </div>
                  <div>
                    <span>Tokens totales</span>
                    <strong>{selectedSession.total_tokens}</strong>
                  </div>
                  <div>
                    <span>Siguiente inferencia</span>
                    <strong>{selectedSession.next_inference_at ? formatDateTime(selectedSession.next_inference_at) : "Sin espera"}</strong>
                  </div>
                </div>

                <div className="session-narrative">
                  <div className="session-head">
                    <h3>Interpretaciones de la sesión</h3>
                    <span>{analysisHistory.length} registros visibles</span>
                  </div>
                  <ul className="list narrative-list">
                    {analysisHistory.length ? (
                      [...analysisHistory].reverse().map((item, index) => (
                        <li key={`${item.frame_number}-${index}`} className="narrative-entry">
                          <div className="session-head">
                            <strong>
                              t={item.frame_second}s · frame {item.frame_number}
                            </strong>
                            <span className={`status-pill ${item.has_incident ? "danger" : "live"}`}>{item.incident_type}</span>
                          </div>
                          <p className="narrative-description">{item.description}</p>
                          <div className="narrative-meta">
                            <span>{item.detection_basis}</span>
                            <span>{item.ai_mode}</span>
                          </div>
                          {item.trigger_reason ? <div className="narrative-reason">{item.trigger_reason}</div> : null}
                          {item.signals?.length ? (
                            <ul className="signals-list">
                              {item.signals.map((signal) => (
                                <li key={signal}>{signal}</li>
                              ))}
                            </ul>
                          ) : null}
                        </li>
                      ))
                    ) : (
                      <li>Esta sesión todavía no tiene interpretaciones guardadas.</li>
                    )}
                  </ul>
                </div>
              </>
            ) : (
              <div className="empty-session-state">Selecciona una sesión para ver sus interpretaciones.</div>
            )}
          </div>
        </div>
      </section>

      <section className="grid">
        <article className="card">
          <h2>Actividad Reciente</h2>
          <ul className="list">
            {activityFeed.map((event, index) => (
              <li key={`${event.title}-${index}`} className={`activity-item activity-${event.tone}`}>
                <div className="session-head">
                  <strong>{event.title}</strong>
                  <span>{event.timestamp}</span>
                </div>
                <div>{event.detail}</div>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="card">
        <h2>Timeline de Incidentes</h2>
        <div className="incident-grid">
          {incidents.map((incident) => (
            <article key={incident.id} className="incident">
              <img src={incident.frame_b64} alt={incident.incident_type} />
              <div>
                <p className={`severity severity-${incident.severity.toLowerCase()}`}>
                  {incident.incident_type} · {incident.severity}
                </p>
                <p>{incident.description}</p>
                <small>
                  {incident.source_id} · {Math.round(incident.confidence * 100)}% confianza
                </small>
              </div>
            </article>
          ))}
        </div>
      </section>

    </main>
  );
}

export default App;
