# DEMO_GUIDE.md — Guía de demostración en vivo

Guía paso a paso para ejecutar la demo del hackathon TechEx 2026.

---

## Antes de la demo — Checklist

- [ ] `docker compose up` corriendo sin errores
- [ ] Dashboard abierto en `http://localhost:5173`
- [ ] Webcam probada y visible en el panel LiveFeed
- [ ] Videos de stock descargados en `backend/demo_videos/`
- [ ] `GEMINI_API_KEY` válida en `.env`
- [ ] Iluminación del cuarto adecuada para webcam
- [ ] "Asaltante" ensayado — sabe exactamente cuándo actuar

---

## Fase 1 — Videos de stock (5 minutos)

### Videos recomendados (dominio público / Creative Commons)

| # | Escena | Fuente sugerida | Duración ideal |
|---|--------|-----------------|----------------|
| 1 | Persona caída en calle | Pixabay / Pexels | 30s |
| 2 | Pelea en estacionamiento | Archive.org (CCTV footage) | 45s |
| 3 | Vehículo en zona peatonal | Pexels | 30s |

### Pasos

1. **Abrir el dashboard** — mostrar que está vacío, sin alertas, log limpio

2. **Narrar el contexto:**
   > "Este es el sistema CertiVision. No hay ningún agente humano detrás. Vamos a cargar un video de cámara de seguridad y el sistema va a analizar lo que ocurre en tiempo real."

3. **Cargar Video 1 — Persona caída:**
   ```bash
   curl -X POST http://localhost:8000/sessions/start \
     -H "Content-Type: application/json" \
     -d '{"source": "file", "source_path": "/app/demo_videos/person_down.mp4", "camera_label": "CAM-DEMO-01"}'
   ```
   - Esperar 5-15 segundos
   - Mostrar cómo aparece la alerta en el timeline
   - Mostrar la descripción generada por Gemini en español
   - Mostrar el hash SHA-256 del frame en el AuditLog

4. **Narrar el diferenciador:**
   > "Este registro ya está en la base de datos con su hash criptográfico. Nadie puede borrarlo. Nadie puede decir que no lo vio."

5. **Cargar Video 2 — Pelea** y repetir el proceso

6. **Mostrar el AuditLog:**
   > "Aquí está el trail completo. Cada frame analizado, cada decisión tomada por la IA, con timestamp y hash de integridad. Esto puede ser auditado por la contraloría municipal en cualquier momento."

---

## Fase 2 — Demo en vivo: Asalto simulado (3 minutos)

### Setup previo

- Webcam apuntando a la persona que será "víctima"
- "Asaltante" fuera de cuadro, listo para entrar
- Cuarto bien iluminado
- Pantalla del dashboard visible para los jueces

### Guión exacto

**[Presentador activa la webcam]**

```bash
curl -X POST http://localhost:8000/sessions/start \
  -H "Content-Type: application/json" \
  -d '{"source": "webcam", "webcam_index": 0, "camera_label": "CAM-SPGG-LIVE"}'
```

**[Presentador habla]:**
> "Ahora vamos a hacer algo diferente. Esta es una cámara en vivo. Soy yo. Y en unos segundos va a ocurrir algo."

**[Pausa de 5 segundos — el sistema está analizando frames normales]**

**[El 'asaltante' entra al cuadro, el presentador levanta las manos, el asaltante toma la cartera y sale]**

**[En los próximos 5-10 segundos, el dashboard debe mostrar:]**
- Badge de alerta ROJA: `ROBBERY — CRITICAL`
- Descripción: *"Se detecta una persona con las manos levantadas mientras otra le arrebata un objeto de entre sus pertenencias."*
- Acción recomendada: *"Despachar unidad de seguridad inmediatamente."*
- Thumbnail del frame

**[Presentador:]**
> "El sistema tardó [X] segundos en detectar el asalto. Sin que ningún humano estuviera mirando. Y este evento ya quedó registrado de forma permanente. Ningún agente puede borrarlo."

**[Mostrar el AuditLog con el nuevo registro]**

> "Este es el futuro del monitoreo municipal. Transparente. Autónomo. Incorruptible."

---

## Fase 3 — Verificación de integridad (1 minuto)

```bash
curl http://localhost:8000/audit/verify
```

Mostrar en pantalla:
```json
{
  "integrity_valid": true,
  "total_records": 23,
  "verified_at": "2026-05-19T...",
  ...
}
```

> "Todos los registros de esta sesión son íntegros. Ninguno fue modificado."

---

## Respuestas a preguntas frecuentes de los jueces

**"¿Qué pasa si la IA se equivoca?"**
> El sistema registra el nivel de confianza de cada detección. Umbrales configurables por severidad. Y en cualquier caso, la IA no puede *borrar* evidencia — solo puede clasificarla incorrectamente, lo cual es verificable.

**"¿Funciona con las cámaras existentes de SPGG?"**
> Sí. El sistema acepta streams RTSP que es el protocolo estándar de las cámaras IP municipales. Solo se necesita la URL del stream.

**"¿Es caro?"**
> Gemini 2.0 Flash cuesta ~$0.075 por millón de tokens de imagen. Una cámara analizando 1 frame/segundo = ~$6.48 USD al mes por cámara. Mucho menos que un agente humano.

**"¿Qué pasa con la privacidad?"**
> Los frames no se almacenan por defecto. Solo el análisis (JSON) y el hash. Cumple con la LFPDPPP. Para frames de incidentes CRITICAL se guarda thumbnail por 72 horas.

---

## Plan B — Si algo falla en la demo en vivo

Si la detección tarda más de 30 segundos o no responde:

1. Mostrar un video pre-grabado del asalto simulado que ya fue procesado
2. Abrir el AuditLog con registros reales de la sesión de prueba
3. Decir: "Aquí tienen el resultado de nuestra sesión de prueba de esta mañana"

**Siempre tener un respaldo funcional listo.**