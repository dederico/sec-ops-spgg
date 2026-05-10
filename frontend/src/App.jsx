import { useEffect, useState } from "react";

const API_URL = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

const starterPayloads = [
  {
    label: "Video persona caída",
    payload: {
      source: "file",
      source_path: "/app/demo_videos/person_down.mp4",
      camera_label: "CAM-DEMO-01",
      frame_sample_rate: 1,
    },
  },
  {
    label: "Video pelea",
    payload: {
      source: "file",
      source_path: "/app/demo_videos/fight.mp4",
      camera_label: "CAM-DEMO-02",
      frame_sample_rate: 1,
    },
  },
  {
    label: "Webcam simulada",
    payload: {
      source: "webcam",
      webcam_index: 0,
      camera_label: "CAM-SPGG-LIVE",
      frame_sample_rate: 1,
    },
  },
];

function App() {
  const [health, setHealth] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [events, setEvents] = useState([]);
  const [audit, setAudit] = useState(null);

  async function refreshAll() {
    const [healthResponse, sessionsResponse, incidentsResponse, auditResponse] = await Promise.all([
      fetch(`${API_URL}/health`),
      fetch(`${API_URL}/sessions`),
      fetch(`${API_URL}/incidents`),
      fetch(`${API_URL}/audit/verify`),
    ]);
    setHealth(await healthResponse.json());
    setSessions((await sessionsResponse.json()).sessions);
    setIncidents((await incidentsResponse.json()).incidents);
    setAudit(await auditResponse.json());
  }

  useEffect(() => {
    refreshAll();
    const ws = new WebSocket(WS_URL);
    ws.onopen = () => ws.send("subscribe");
    ws.onmessage = (message) => {
      const payload = JSON.parse(message.data);
      setEvents((current) => [payload, ...current].slice(0, 12));
      if (payload.type === "INCIDENT_ALERT") {
        setIncidents((current) => [payload.incident, ...current]);
      }
      refreshAll();
    };
    return () => ws.close();
  }, []);

  async function startSession(payload) {
    await fetch(`${API_URL}/sessions/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    refreshAll();
  }

  async function stopSession(sessionId) {
    await fetch(`${API_URL}/sessions/${sessionId}/stop`, { method: "POST" });
    refreshAll();
  }

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Hackathon MVP</p>
        <h1>CertiVision SPGG</h1>
        <p className="lede">
          Flujo de demo para sesiones, alertas en tiempo real y verificación de integridad.
        </p>
      </section>

      <section className="grid">
        <article className="card">
          <h2>Sistema</h2>
          <pre>{JSON.stringify(health, null, 2)}</pre>
          <pre>{JSON.stringify(audit, null, 2)}</pre>
        </article>

        <article className="card">
          <h2>Iniciar demo</h2>
          <div className="actions">
            {starterPayloads.map((item) => (
              <button key={item.label} onClick={() => startSession(item.payload)}>
                {item.label}
              </button>
            ))}
          </div>
        </article>
      </section>

      <section className="grid">
        <article className="card">
          <h2>Sesiones</h2>
          <ul className="list">
            {sessions.map((session) => (
              <li key={session.session_id}>
                <div>
                  <strong>{session.camera_label}</strong>
                  <span>{session.status}</span>
                </div>
                <div>
                  Frames: {session.frames_analyzed} | Incidentes: {session.incidents_detected}
                </div>
                {session.status === "ACTIVE" ? (
                  <button onClick={() => stopSession(session.session_id)}>Detener</button>
                ) : null}
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h2>Eventos WebSocket</h2>
          <ul className="list">
            {events.map((event, index) => (
              <li key={`${event.type}-${index}`}>
                <pre>{JSON.stringify(event, null, 2)}</pre>
              </li>
            ))}
          </ul>
        </article>
      </section>

      <section className="card">
        <h2>Incidentes</h2>
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
                  {incident.source_id} · {incident.confidence}
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
