import { useEffect, useRef, useState } from "react";

const API_URL = window.location.origin;
const WS_PROTOCOL = window.location.protocol === "https:" ? "wss:" : "ws:";
const WS_URL = `${WS_PROTOCOL}//${window.location.host}/ws`;

const TRANSLATIONS = {
  en: {
    hackathonMvp: "Hackathon MVP",
    heroTitle: "CertiVision SPGG",
    heroLede: "Show the source, the model interpretation, and the exact moment when observation becomes an alert.",
    livePriority: "LIVE ANALYSIS PRIORITY",
    fileDemoMode: "File demo mode",
    ahaMomentTag: "The AHA moment happens when the scene changes and the system verbalizes it",
    singleEndpoint: "Single endpoint: open this same page on laptop and phone",
    analyzedSource: "Analyzed Source",
    waitingSession: "Waiting for a session",
    alertTriggered: "ALERT TRIGGERED",
    liveAnalysis: "LIVE ANALYSIS",
    analyzing: "ANALYZING",
    source: "Source",
    pathOrStream: "Path or stream",
    operatorLiveInput: "Operator live input",
    observedSecond: "Observed second",
    frame: "Frame",
    modelInterpretation: "Model Interpretation",
    interpretationPlaceholder: "The model reading of the current scene should appear here.",
    confidence: "Confidence",
    severity: "Severity",
    risk: "Risk",
    subjects: "Subjects",
    family: "Family",
    dispatch: "Dispatch",
    inputTokens: "Input tokens",
    outputTokens: "Output tokens",
    totalTokens: "Total tokens",
    recommendedAction: "Recommended action",
    noRecommendation: "No recommendation yet.",
    whyReported: "Why it reported this",
    noReason: "No detailed justification yet.",
    observedElements: "Observed signals",
    ahaMoment: "AHA Moment",
    noAlarmYet: "No alarm yet",
    alarmPlaceholder: "When the model crosses the threshold, this card switches to critical and keeps the incident visible.",
    state: "State",
    observation: "Observation",
    trigger: "Trigger",
    waiting: "Waiting",
    triggeredSecond: "Triggered second",
    sceneSummary: "Scene summary",
    noSummary: "No summary yet",
    locationOps: "Location and Operational Response",
    deviceLocation: "Device location",
    noSharedLocation: "No shared location",
    approxAccuracy: "Approx. accuracy: {meters} m",
    locationSharedWhenAllowed: "Location is shared when the mobile source grants geolocation access.",
    openInMaps: "Open location in map",
    operationalSource: "Operational source",
    noActiveSource: "No active source",
    noSession: "No session",
    system: "System",
    integrity: "Integrity",
    valid: "VALID",
    pending: "PENDING",
    captureThisDevice: "Capture on this device",
    sameViewDevices: "Use this same view on both laptop and phone. No endpoint switching needed.",
    cameraLabel: "Camera label",
    useLaptopCamera: "Use this laptop camera",
    usePhoneCamera: "Use this phone camera",
    phoneNgrokHint: "If you open this page from the phone via ngrok, the phone button starts camera and analysis right here.",
    externalVideos: "External Videos",
    externalVideosHelp: "Upload a local file or download one from a public URL. Then trigger analysis from the list.",
    uploadVideo: "Upload video",
    downloadFromUrl: "Download from URL",
    analyze: "Analyze",
    sessions: "Sessions",
    sessionExplorer: "Session Explorer",
    sessionsHelp: "Open each session, inspect what the model interpreted, and read the full sequence without opening JSON.",
    frames: "frames",
    incidents: "incidents",
    noSessions: "No sessions recorded yet.",
    selectedSession: "Selected session",
    stopSession: "Stop session",
    refreshLog: "Refresh history",
    started: "Started",
    analyzedFrames: "Analyzed frames",
    detectedIncidents: "Detected incidents",
    geminiCalls: "Gemini calls",
    savedCalls: "Saved calls",
    sharedLocation: "Shared location",
    noLocation: "No location",
    nextInference: "Next inference",
    noWait: "No wait",
    sessionInterpretations: "Session interpretations",
    visibleRecords: "{count} visible records",
    noSessionInterpretations: "This session does not have saved interpretations yet.",
    selectSession: "Select a session to inspect its interpretations.",
    recentActivity: "Recent Activity",
    incidentTimeline: "Incident Timeline",
    sourceWebcam: "Webcam / Live feed",
    sourceMobile: "Phone / Live bridge",
    sourceRtsp: "IP camera",
    sourceFile: "Video file",
    heartbeat: "System heartbeat",
    analyzingSource: "Analyzing {source}",
    detectedSuffix: "detected",
    camera: "Camera",
    statusWord: "Status",
    analysisError: "Analysis error on {camera}",
    systemEvent: "System event",
    sharedLocationLabel: "Location shared from this device",
    startDemoToSee: "Start a demo to see live interpretation.",
  },
  es: {
    hackathonMvp: "Hackathon MVP",
    heroTitle: "CertiVision SPGG",
    heroLede: "Mostrar la fuente, la interpretación del modelo y el instante exacto en que se convierte en alerta.",
    livePriority: "LIVE ANALYSIS PRIORITARIO",
    fileDemoMode: "Modo demo por archivo",
    ahaMomentTag: "El AHA moment ocurre cuando la escena cambia y el sistema lo verbaliza",
    singleEndpoint: "Endpoint único: abre esta misma página en laptop y celular",
    analyzedSource: "Fuente Analizada",
    waitingSession: "Esperando una sesión",
    alertTriggered: "ALERTA DISPARADA",
    liveAnalysis: "LIVE ANALYSIS",
    analyzing: "ANALIZANDO",
    source: "Origen",
    pathOrStream: "Ruta o stream",
    operatorLiveInput: "Entrada en vivo del operador",
    observedSecond: "Segundo observado",
    frame: "Frame",
    modelInterpretation: "Interpretación del modelo",
    interpretationPlaceholder: "Aquí debe aparecer la lectura del modelo sobre lo que está viendo en la escena.",
    confidence: "Confianza",
    severity: "Severidad",
    risk: "Riesgo",
    subjects: "Sujetos",
    family: "Familia",
    dispatch: "Despacho",
    inputTokens: "Tokens entrada",
    outputTokens: "Tokens salida",
    totalTokens: "Tokens total",
    recommendedAction: "Acción recomendada",
    noRecommendation: "Sin recomendación todavía.",
    whyReported: "Por qué lo reporta",
    noReason: "Sin justificación detallada todavía.",
    observedElements: "Elementos observados",
    ahaMoment: "AHA Moment",
    noAlarmYet: "Sin alarma aún",
    alarmPlaceholder: "Cuando el modelo cruce el umbral, esta tarjeta cambia a estado crítico y deja visible el incidente.",
    state: "Estado",
    observation: "Observación",
    trigger: "Detonante",
    waiting: "Esperando",
    triggeredSecond: "Segundo disparado",
    sceneSummary: "Resumen de escena",
    noSummary: "Sin resumen todavía",
    locationOps: "Ubicación y Respuesta Operativa",
    deviceLocation: "Ubicación del dispositivo",
    noSharedLocation: "Sin ubicación compartida",
    approxAccuracy: "Precisión aproximada: {meters} m",
    locationSharedWhenAllowed: "La ubicación se comparte cuando la fuente móvil autoriza geolocalización.",
    openInMaps: "Abrir ubicación en mapa",
    operationalSource: "Fuente operativa",
    noActiveSource: "Sin fuente activa",
    noSession: "Sin sesión",
    system: "Sistema",
    integrity: "Integridad",
    valid: "VALIDA",
    pending: "PENDIENTE",
    captureThisDevice: "Captura en este dispositivo",
    sameViewDevices: "Usa esta misma vista tanto en laptop como en celular. Ya no necesitas cambiar de endpoint.",
    cameraLabel: "Etiqueta de cámara",
    useLaptopCamera: "Usar cámara de esta laptop",
    usePhoneCamera: "Usar cámara de este celular",
    phoneNgrokHint: "Si abres esta página desde el teléfono por ngrok, el botón de celular inicia cámara y análisis aquí mismo.",
    externalVideos: "Videos externos",
    externalVideosHelp: "Sube un archivo local o descarga uno desde una URL pública. Luego puedes disparar el análisis desde la lista.",
    uploadVideo: "Subir video",
    downloadFromUrl: "Descargar desde URL",
    analyze: "Analizar",
    sessions: "Sesiones",
    sessionExplorer: "Explorador de sesiones",
    sessionsHelp: "Aquí puedes entrar a cada sesión, ver qué interpretó el modelo y leer la secuencia completa sin abrir JSON.",
    frames: "frames",
    incidents: "incidentes",
    noSessions: "Todavía no hay sesiones registradas.",
    selectedSession: "Sesión seleccionada",
    stopSession: "Detener sesión",
    refreshLog: "Actualizar bitácora",
    started: "Inició",
    analyzedFrames: "Frames analizados",
    detectedIncidents: "Incidentes detectados",
    geminiCalls: "Llamadas a Gemini",
    savedCalls: "Llamadas ahorradas",
    sharedLocation: "Ubicación compartida",
    noLocation: "Sin ubicación",
    nextInference: "Siguiente inferencia",
    noWait: "Sin espera",
    sessionInterpretations: "Interpretaciones de la sesión",
    visibleRecords: "{count} registros visibles",
    noSessionInterpretations: "Esta sesión todavía no tiene interpretaciones guardadas.",
    selectSession: "Selecciona una sesión para ver sus interpretaciones.",
    recentActivity: "Actividad Reciente",
    incidentTimeline: "Timeline de Incidentes",
    sourceWebcam: "Webcam / Live feed",
    sourceMobile: "Celular / Live bridge",
    sourceRtsp: "Cámara IP",
    sourceFile: "Archivo de video",
    heartbeat: "Heartbeat del sistema",
    analyzingSource: "Analizando {source}",
    detectedSuffix: "detectado",
    camera: "Camara",
    statusWord: "Estado",
    analysisError: "Error de análisis en {camera}",
    systemEvent: "Evento del sistema",
    sharedLocationLabel: "Ubicación compartida desde este dispositivo",
    startDemoToSee: "Inicia una demo para ver la interpretación en vivo.",
  },
};

function App() {
  const [language, setLanguage] = useState(() => localStorage.getItem("certivision-language") || "en");
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
  const deviceLocationRef = useRef(null);
  const dictionary = TRANSLATIONS[language] || TRANSLATIONS.en;

  function t(key, params = {}) {
    const template = dictionary[key] || TRANSLATIONS.en[key] || key;
    return Object.entries(params).reduce(
      (text, [paramKey, value]) => text.replaceAll(`{${paramKey}}`, String(value)),
      template,
    );
  }

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
    if (source === "webcam") return t("sourceWebcam");
    if (source === "mobile") return t("sourceMobile");
    if (source === "rtsp") return t("sourceRtsp");
    return t("sourceFile");
  }

  function formatDateTime(value) {
    if (!value) return "--";
    return new Date(value).toLocaleString(language === "es" ? "es-MX" : "en-US");
  }

  function formatCoords(location) {
    if (!location?.latitude || !location?.longitude) {
      return "--";
    }
    return `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
  }

  function riskClass(riskLevel) {
    if (riskLevel === "RED") return "risk-red";
    if (riskLevel === "YELLOW") return "risk-yellow";
    return "risk-green";
  }

  async function getSharedLocation() {
    if (!("geolocation" in navigator)) {
      return null;
    }
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) =>
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy_meters: position.coords.accuracy,
            shared_at: new Date().toISOString(),
            label: t("sharedLocationLabel"),
          }),
        () => resolve(null),
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 15000 },
      );
    });
  }

  function appendActivity(entry) {
    setActivityFeed((current) => [entry, ...current].slice(0, 18));
  }

  function summarizeEvent(payload) {
    if (payload.type === "ANALYSIS_UPDATE") {
      const second = payload.analysis.frame_second ?? 0;
      const source = payload.analysis.camera_label;
      const basis = payload.analysis.detection_basis || "analysis";
      const scenario = payload.analysis.scenario_label || payload.analysis.incident_type;
      if (payload.analysis.status === "INCIDENT_DETECTED") {
        return {
          tone: "alert",
          title: `${scenario} ${t("detectedSuffix")}`,
          detail: `${source} · t=${second}s · ${payload.analysis.trigger_reason || payload.analysis.model_interpretation}`,
        };
      }
      return {
        tone: "info",
        title: t("analyzingSource", { source }),
        detail: `t=${second}s · ${basis} · ${payload.analysis.narrator_caption || payload.analysis.model_interpretation}`,
      };
    }
    if (payload.type === "INCIDENT_ALERT") {
      return {
        tone: "alert",
        title: `Alerta ${payload.incident.scenario_label || payload.incident.incident_type}`,
        detail: `${payload.incident.source_id} · ${Math.round(payload.incident.confidence * 100)}% · ${payload.incident.description}`,
      };
    }
    if (payload.type === "CAMERA_STATUS") {
      return {
        tone: payload.status === "ACTIVE" ? "info" : "neutral",
        title: `${t("camera")} ${payload.source_id}`,
        detail: `${t("statusWord")} ${payload.status}${payload.source_path ? ` · ${payload.source_path}` : ""}`,
      };
    }
    if (payload.type === "ANALYSIS_ERROR") {
      return {
        tone: "alert",
        title: t("analysisError", { camera: payload.camera_label }),
        detail: payload.message,
      };
    }
    if (payload.type === "HEARTBEAT") {
      return {
        tone: "neutral",
        title: t("heartbeat"),
        detail:
          language === "es"
            ? `${payload.cameras_active} cámaras activas · ${payload.frames_analyzed} frames analizados`
            : `${payload.cameras_active} active cameras · ${payload.frames_analyzed} analyzed frames`,
      };
    }
    return {
      tone: "neutral",
      title: payload.type,
      detail: t("systemEvent"),
    };
  }

  useEffect(() => {
    localStorage.setItem("certivision-language", language);
  }, [language]);

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
              incident_family: payload.analysis.incident_family,
              scenario_label: payload.analysis.scenario_label,
              dispatch_target: payload.analysis.dispatch_target,
              has_incident: payload.analysis.status === "INCIDENT_DETECTED",
              risk_level: payload.analysis.risk_level,
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
    deviceLocationRef.current = null;
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
      body: JSON.stringify({ camera_label: cameraLabel, frame_b64, device_location: deviceLocationRef.current }),
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
    deviceLocationRef.current = sourceType === "mobile" ? await getSharedLocation() : null;
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
      device_location: deviceLocationRef.current,
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
      return <div className="empty-frame">{t("startDemoToSee")}</div>;
    }
    return <img src={latestAnalysis.frame_b64} alt={latestAnalysis.incident_type} className="hero-frame" />;
  }

  const selectedSession = sessions.find((session) => session.session_id === selectedSessionId) || null;
  const activeLocation = latestAnalysis?.device_location || latestAlert?.device_location || selectedSession?.device_location || null;
  const activeRiskLevel = latestAnalysis?.risk_level || latestAlert?.risk_level || "GREEN";
  const activeScenario = latestAnalysis?.scenario_label || latestAlert?.scenario_label || latestAnalysis?.incident_type || "NORMAL";

  return (
    <main className="shell">
      <canvas ref={captureCanvasRef} className="hidden-canvas" />
      <section className="hero">
        <div className="hero-topbar">
          <div>
            <p className="eyebrow">{t("hackathonMvp")}</p>
            <h1>{t("heroTitle")}</h1>
          </div>
          <div className="language-switch" role="tablist" aria-label="Language switch">
            <button
              type="button"
              className={language === "en" ? "lang-active" : "lang-idle"}
              onClick={() => setLanguage("en")}
            >
              EN
            </button>
            <button
              type="button"
              className={language === "es" ? "lang-active" : "lang-idle"}
              onClick={() => setLanguage("es")}
            >
              ES
            </button>
          </div>
        </div>
        <p className="lede">{t("heroLede")}</p>
        <div className="hero-badges">
          <span className={`hero-pill ${liveMode ? "hero-pill-live" : ""}`}>
            {liveMode ? t("livePriority") : t("fileDemoMode")}
          </span>
          <span className="hero-pill">{t("ahaMomentTag")}</span>
          <span className="hero-pill">{t("singleEndpoint")}</span>
        </div>
      </section>

      <section className="aha-grid">
        <article className="stage-card">
          <div className="stage-header">
            <div>
              <p className="section-kicker">{t("analyzedSource")}</p>
              <h2>
                {latestAnalysis ? latestAnalysis.camera_label : t("waitingSession")}
              </h2>
            </div>
            <span className={`status-pill ${latestAnalysis?.status === "INCIDENT_DETECTED" ? "danger" : "live"}`}>
              {latestAnalysis?.status === "INCIDENT_DETECTED"
                ? t("alertTriggered")
                : latestAnalysis?.source === "webcam"
                  ? t("liveAnalysis")
                  : t("analyzing")}
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
              <span>{t("source")}</span>
              <strong>{latestAnalysis ? sourceLabel(latestAnalysis.source) : t("noActiveSource")}</strong>
            </div>
            <div>
              <span>{t("pathOrStream")}</span>
              <strong>{latestAnalysis?.source_path || t("operatorLiveInput")}</strong>
            </div>
            <div>
              <span>{t("observedSecond")}</span>
              <strong>{latestAnalysis?.frame_second ?? 0}s</strong>
            </div>
            <div>
              <span>{t("frame")}</span>
              <strong>{latestAnalysis?.frame_number || 0}</strong>
            </div>
          </div>
        </article>

        <article className="aha-card">
          <p className="section-kicker">{t("modelInterpretation")}</p>
          <h2>{latestAnalysis?.scenario_label || latestAnalysis?.incident_type || "NORMAL"}</h2>
          <p className="aha-copy">
            {latestAnalysis?.model_interpretation || t("interpretationPlaceholder")}
          </p>
          <div className="metrics">
            <div>
              <span>{t("confidence")}</span>
              <strong>{latestAnalysis ? `${Math.round(latestAnalysis.confidence * 100)}%` : "--"}</strong>
            </div>
            <div>
              <span>{t("severity")}</span>
              <strong>{latestAnalysis?.severity || "--"}</strong>
            </div>
            <div>
              <span>{t("risk")}</span>
              <strong>{latestAnalysis?.risk_level || "--"}</strong>
            </div>
            <div>
              <span>{t("subjects")}</span>
              <strong>{latestAnalysis?.subjects_count ?? "--"}</strong>
            </div>
            <div>
              <span>{t("family")}</span>
              <strong>{latestAnalysis?.incident_family || "--"}</strong>
            </div>
            <div>
              <span>{t("dispatch")}</span>
              <strong>{latestAnalysis?.dispatch_target || "--"}</strong>
            </div>
            <div>
              <span>{t("inputTokens")}</span>
              <strong>{latestAnalysis?.input_tokens ?? "--"}</strong>
            </div>
            <div>
              <span>{t("outputTokens")}</span>
              <strong>{latestAnalysis?.output_tokens ?? "--"}</strong>
            </div>
            <div>
              <span>{t("totalTokens")}</span>
              <strong>{latestAnalysis?.total_tokens ?? "--"}</strong>
            </div>
          </div>
          <div className="recommendation">
            <span>{t("recommendedAction")}</span>
            <p>{latestAnalysis?.recommended_action || t("noRecommendation")}</p>
          </div>
          <div className="recommendation">
            <span>{t("whyReported")}</span>
            <p>{latestAnalysis?.trigger_reason || t("noReason")}</p>
          </div>
          <div className="signals-block">
            <span>{t("observedElements")}</span>
            <ul className="signals-list">
              {(latestAnalysis?.observed_signals || []).map((signal) => (
                <li key={signal}>{signal}</li>
              ))}
            </ul>
          </div>
        </article>

        <article className={`alarm-card ${latestAlert ? "alarm-on" : ""}`}>
          <p className="section-kicker">{t("ahaMoment")}</p>
          <h2>{latestAlert ? `${latestAlert.scenario_label || latestAlert.incident_type} ${t("detectedSuffix")}` : t("noAlarmYet")}</h2>
          <p className="aha-copy">
            {latestAlert
              ? latestAlert.description
              : t("alarmPlaceholder")}
          </p>
          <div className="alarm-strip">
            <span>{t("state")}</span>
            <strong>{latestAlert ? `${latestAlert.risk_level} · ${latestAlert.severity}` : t("observation")}</strong>
          </div>
          <div className="alarm-strip">
            <span>{t("trigger")}</span>
            <strong>{latestAlert ? `${Math.round(latestAlert.confidence * 100)}% ${t("confidence").toLowerCase()}` : t("waiting")}</strong>
          </div>
          <div className="alarm-strip">
            <span>{t("triggeredSecond")}</span>
            <strong>{latestAlert?.detected_at_second ?? "--"}s</strong>
          </div>
          <div className="alarm-strip">
            <span>{t("sceneSummary")}</span>
            <strong>{latestAlert?.scene_summary || t("noSummary")}</strong>
          </div>
        </article>
      </section>

      <section className={`operations-strip ${riskClass(activeRiskLevel)}`}>
        <div className="operations-head">
          <div>
            <p className="section-kicker">{t("locationOps")}</p>
            <h2>{activeScenario}</h2>
          </div>
          <span className={`status-pill ${activeRiskLevel === "RED" ? "danger" : "live"}`}>{activeRiskLevel}</span>
        </div>
        <div className="operations-grid">
          <div>
            <span>{t("deviceLocation")}</span>
            <strong>{activeLocation ? formatCoords(activeLocation) : t("noSharedLocation")}</strong>
            <p className="helper-copy">
              {activeLocation
                ? t("approxAccuracy", { meters: Math.round(activeLocation.accuracy_meters || 0) })
                : t("locationSharedWhenAllowed")}
            </p>
            {activeLocation ? (
              <a href={`https://maps.google.com/?q=${activeLocation.latitude},${activeLocation.longitude}`} target="_blank" rel="noreferrer">
                {t("openInMaps")}
              </a>
            ) : null}
          </div>
          <div>
            <span>{t("recommendedAction")}</span>
            <strong>{latestAnalysis?.recommended_action || latestAlert?.recommended_action || (language === "es" ? "Continuar monitoreo." : "Continue monitoring.")}</strong>
            <p className="helper-copy">
              {latestAnalysis?.dispatch_target || latestAlert?.dispatch_target || "MONITOREO"} · {latestAnalysis?.incident_family || latestAlert?.incident_family || "NORMAL"}
            </p>
          </div>
          <div>
            <span>{t("operationalSource")}</span>
            <strong>{latestAnalysis ? sourceLabel(latestAnalysis.source) : t("noActiveSource")}</strong>
            <p className="helper-copy">
              {latestAnalysis?.camera_label || selectedSession?.camera_label || t("noSession")} · {latestAnalysis?.source_path || selectedSession?.source_path || "live stream"}
            </p>
          </div>
        </div>
      </section>

      <section className="grid">
        <article className="card">
          <h2>{t("system")}</h2>
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
              <span>{t("integrity")}</span>
              <strong>{audit?.integrity_valid ? t("valid") : t("pending")}</strong>
            </div>
          </div>
        </article>

        <article className="card">
          <h2>{t("captureThisDevice")}</h2>
          <p className="helper-copy">{t("sameViewDevices")}</p>
          <div className="actions">
            <input
              className="app-input"
              value={activeCameraLabel}
              onChange={(event) => setActiveCameraLabel(event.target.value)}
              placeholder={t("cameraLabel")}
            />
            <button onClick={() => startThisDeviceCamera("webcam")}>{t("useLaptopCamera")}</button>
            <button onClick={() => startThisDeviceCamera("mobile")}>{t("usePhoneCamera")}</button>
          </div>
          <p className="helper-copy">{t("phoneNgrokHint")}</p>
          <div className="frame-shell compact">
            <video ref={localVideoRef} className="hero-frame" autoPlay muted playsInline />
          </div>
        </article>

        <article className="card">
          <h2>{t("externalVideos")}</h2>
          <p className="helper-copy">{t("externalVideosHelp")}</p>
          <div className="stacked-actions">
            <input className="app-input" type="file" accept="video/*" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} />
            <button onClick={uploadVideo} disabled={!selectedFile}>{t("uploadVideo")}</button>
            <input
              className="app-input"
              value={importUrl}
              onChange={(event) => setImportUrl(event.target.value)}
              placeholder="https://.../video.mp4"
            />
            <button onClick={importVideoUrl} disabled={!importUrl.trim()}>{t("downloadFromUrl")}</button>
          </div>
          <ul className="list source-list">
            {sources.map((source) => (
              <li key={source.path}>
                <div className="session-head">
                  <strong>{source.name}</strong>
                  <button onClick={() => startUploadedSource(source.path, source.name)}>{t("analyze")}</button>
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
            <p className="section-kicker">{t("sessions")}</p>
            <h2>{t("sessionExplorer")}</h2>
          </div>
          <p className="helper-copy">{t("sessionsHelp")}</p>
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
                    <span>{session.frames_analyzed} {t("frames")}</span>
                    <span>{session.incidents_detected} {t("incidents")}</span>
                    <span>{session.total_tokens} tokens</span>
                  </div>
                </button>
              ))
            ) : (
              <div className="empty-session-state">{t("noSessions")}</div>
            )}
          </aside>

          <div className="session-detail">
            {selectedSession ? (
              <>
                <div className="session-detail-header">
                  <div>
                    <p className="section-kicker">{t("selectedSession")}</p>
                    <h3>{selectedSession.camera_label}</h3>
                  </div>
                  <div className="session-detail-actions">
                    {selectedSession.status === "ACTIVE" ? (
                      <button onClick={() => stopSession(selectedSession.session_id)}>{t("stopSession")}</button>
                    ) : null}
                    <button onClick={() => refreshHistory(selectedSession.session_id)}>{t("refreshLog")}</button>
                  </div>
                </div>

                <div className="session-detail-grid">
                  <div>
                    <span>{t("source")}</span>
                    <strong>{sourceLabel(selectedSession.source)}</strong>
                  </div>
                  <div>
                    <span>{t("pathOrStream")}</span>
                    <strong>{selectedSession.source_path || t("operatorLiveInput")}</strong>
                  </div>
                  <div>
                    <span>{t("started")}</span>
                    <strong>{formatDateTime(selectedSession.started_at)}</strong>
                  </div>
                  <div>
                    <span>{t("state")}</span>
                    <strong>{selectedSession.status}</strong>
                  </div>
                  <div>
                    <span>{t("analyzedFrames")}</span>
                    <strong>{selectedSession.frames_analyzed}</strong>
                  </div>
                  <div>
                    <span>{t("detectedIncidents")}</span>
                    <strong>{selectedSession.incidents_detected}</strong>
                  </div>
                  <div>
                    <span>{t("geminiCalls")}</span>
                    <strong>{selectedSession.gemini_calls}</strong>
                  </div>
                  <div>
                    <span>{t("savedCalls")}</span>
                    <strong>{selectedSession.saved_calls}</strong>
                  </div>
                  <div>
                    <span>{t("inputTokens")}</span>
                    <strong>{selectedSession.input_tokens}</strong>
                  </div>
                  <div>
                    <span>{t("outputTokens")}</span>
                    <strong>{selectedSession.output_tokens}</strong>
                  </div>
                  <div>
                    <span>{t("totalTokens")}</span>
                    <strong>{selectedSession.total_tokens}</strong>
                  </div>
                  <div>
                    <span>{t("sharedLocation")}</span>
                    <strong>{selectedSession.device_location ? formatCoords(selectedSession.device_location) : t("noLocation")}</strong>
                  </div>
                  <div>
                    <span>{t("nextInference")}</span>
                    <strong>{selectedSession.next_inference_at ? formatDateTime(selectedSession.next_inference_at) : t("noWait")}</strong>
                  </div>
                </div>

                <div className="session-narrative">
                  <div className="session-head">
                    <h3>{t("sessionInterpretations")}</h3>
                    <span>{t("visibleRecords", { count: analysisHistory.length })}</span>
                  </div>
                  <ul className="list narrative-list">
                    {analysisHistory.length ? (
                      [...analysisHistory].reverse().map((item, index) => (
                        <li key={`${item.frame_number}-${index}`} className="narrative-entry">
                          <div className="session-head">
                            <strong>
                              t={item.frame_second}s · frame {item.frame_number}
                            </strong>
                            <span className={`status-pill ${item.has_incident ? "danger" : "live"}`}>{item.scenario_label || item.incident_type}</span>
                          </div>
                          <p className="narrative-description">{item.description}</p>
                          <div className="narrative-meta">
                            <span>{item.detection_basis}</span>
                            <span>{item.ai_mode}</span>
                            <span>{item.incident_family || "NORMAL"}</span>
                            <span>{item.dispatch_target || "MONITOREO"}</span>
                            <span>{item.risk_level || "GREEN"}</span>
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
                      <li>{t("noSessionInterpretations")}</li>
                    )}
                  </ul>
                </div>
              </>
            ) : (
              <div className="empty-session-state">{t("selectSession")}</div>
            )}
          </div>
        </div>
      </section>

      <section className="grid">
        <article className="card">
          <h2>{t("recentActivity")}</h2>
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
        <h2>{t("incidentTimeline")}</h2>
        <div className="incident-grid">
          {incidents.map((incident) => (
            <article key={incident.id} className="incident">
              <img src={incident.frame_b64} alt={incident.incident_type} />
              <div>
                <p className={`severity severity-${incident.severity.toLowerCase()}`}>
                  {incident.scenario_label || incident.incident_type} · {incident.risk_level || incident.severity}
                </p>
                <p>{incident.description}</p>
                <small>
                  {incident.source_id} · {Math.round(incident.confidence * 100)}% {t("confidence").toLowerCase()}
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
