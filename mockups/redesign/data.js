// Copy of the real project-hub data, taken by build_data.py. Do not edit by hand.
window.HUB = {
 "snapshot": "2026-10-16T09:06:19+00:00",
 "projects": [
  {
   "decisions": [
    {
     "date": "2026-10-16T07:54:19+00:00",
     "decision": "Encode NotchLC natively (numba + LZ4) instead of through Adobe Media Encoder; FFmpeg's notchlc decoder is the format reference and every test encode is decoded with it.",
     "reason": "AME forces Rec.709 blindly and exposes no colour-space control, and it is an external dependency; colour before encoding is the product's differentiator (PRODUCT.md:21, 25, 210; FORMAT.md:1-6)."
    },
    {
     "date": "2026-10-16T07:54:19+00:00",
     "decision": "Split UI and engine: a Python engine as a local WebSocket server (8765), with a PySide6 + dannyfm-ui app replacing the Electron UI, which is frozen.",
     "reason": "The Qt UI became the main UI and the engine stays unchanged behind its Pydantic contract (PRODUCT.md:116, 432; CLAUDE.md structure)."
    },
    {
     "date": "2026-10-16T07:54:20+00:00",
     "decision": "NotchLC on a CUDA GPU with automatic CPU fallback, in a warm persistent worker pool that is reused by every job and released after 300 s idle.",
     "reason": "Speed (Turbo >100 fps target met) without losing machines that have no usable GPU; the idle release frees GPU memory (REPORT.md:51, 89, 160-161; CLAUDE.md engine behaviour)."
    },
    {
     "date": "2026-10-16T07:54:20+00:00",
     "decision": "GPU colour = OCIO-baked 1D tables + affine + 65³ residual LUT, used for NotchLC only and only when the first frame's CPU-pixel share is ≤ 40 %.",
     "reason": "A single baked LUT exceeded the tolerance; HAP was slower on the GPU path (REPORT.md:60-68; RUN_PLAN.md:155, 164)."
    },
    {
     "date": "2026-10-16T07:54:20+00:00",
     "decision": "NotchLC bitstream: LZ4 block format 1, BT.601 coefficients at full range, AME's container layout (moov first) written by our own MOV writer.",
     "reason": "FFmpeg has quirks in LZF and format 2; the matrix was measured against AME's own encode; FFmpeg has no raw NotchLC muxer and Notch's decoder may be strict (FORMAT.md:8-10, 45-49, 243-261, 303-306)."
    },
    {
     "date": "2026-10-16T07:54:20+00:00",
     "decision": "H.264 uses h264_nvenc when a test encode works, else libx264; a failed NVENC encode is redone in software. No HEVC output.",
     "reason": "GPU speed where available without failing jobs on machines or drivers without NVENC; no HEVC codec exists in the product (REPORT.md:73-75; CLAUDE.md NVENC)."
    },
    {
     "date": "2026-10-16T07:54:20+00:00",
     "decision": "Engine clients authenticate with a per-launch secret through a mutual challenge-response handshake (engine:hello / engine:auth), and the engine validates every path it is given.",
     "reason": "Security scan F1–F8: an unauthenticated localhost WebSocket allowed overwrite/delete, arbitrary reads and probes, and the UI trusted any listener (CLAUDE-SECURITY-RESULTS.md; fixed in 2f90210, RUN_PLAN.md:288-290)."
    },
    {
     "date": "2026-10-16T07:54:20+00:00",
     "decision": "Default on_exists is \"version\": an existing output gets the next free _vN name instead of being overwritten; existing settings are migrated.",
     "reason": "Overwrite as default was an open security/data-loss finding; a new version never destroys a delivered file (RUN_PLAN.md:290, 325)."
    },
    {
     "date": "2026-10-16T07:54:20+00:00",
     "decision": "Every encode writes <final>.partial and renames it on success; cancel or failure deletes it, and a file already at the final name is never touched.",
     "reason": "A cancelled or crashed encode must never leave a truncated file under the final name or destroy an existing one (ROUND5_PLAN.md:57-63; CLAUDE.md partial outputs)."
    },
    {
     "date": "2026-10-16T07:54:20+00:00",
     "decision": "dannyfm-ui is changed only in its own repo (tests, version bump, tag), pinned by exact commit hash without -e, with app-only needs in the extension layer; no fork. FrameMorph moved to v0.2.0 in e7e3c9c.",
     "reason": "The FrameMorph fork (dannyfm-ui-notchpack) diverged from the package StageTrack uses; one shared package with pins keeps both apps stable (CLAUDE.md R1–R3)."
    }
   ],
   "description": "App de Windows (antes NotchPack) que convierte vídeo a NotchLC, ProRes, HAP y H.264 con color ACES/OCIO y GPU, para operadores de media server y producción virtual.",
   "id": "framemorph",
   "items": [
    {
     "created_at": "2026-10-16T07:54:00+00:00",
     "details": "Supersedes the pending approvals of run 3, run 4, round 2 and round 3. No approval recorded in ROUND5_PLAN.md.",
     "id": "27823017",
     "status": "open",
     "title": "Approve FrameMorph 0.3.0 screenshots",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:00+00:00",
     "details": "REPORT.md:220-237. Load the disguise_check files in disguise; review the ramp, alpha and flash/beep sync.",
     "id": "21113e76",
     "status": "open",
     "title": "Manual check: disguise test pack",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:00+00:00",
     "details": "REPORT.md:220-237. Open a Turbo encode in disguise and AME and compare with Best.",
     "id": "630b8cc5",
     "status": "open",
     "title": "Manual check: NotchLC Turbo file in disguise / AME",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:00+00:00",
     "details": "REPORT.md:220-237. Batch of 2–3 jobs; Turbo goes Verificando then Listo; \"omitir si existe\" shows Omitido; Incluir audio off; live theme switch; \"(vista: …)\" label.",
     "id": "2f2f70e8",
     "status": "open",
     "title": "Manual check: Qt app with the real engine",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:00+00:00",
     "details": "REPORT.md:235.",
     "id": "9567caba",
     "status": "open",
     "title": "Manual check: slow or disconnected network drive does not freeze the browser",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:00+00:00",
     "details": "REPORT.md:236.",
     "id": "5c29f071",
     "status": "open",
     "title": "Manual check: low-VRAM or non-NVIDIA machine falls back to CPU",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "REPORT.md:237.",
     "id": "4eaccc76",
     "status": "open",
     "title": "Manual check: NVENC H.264 output plays correctly",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1.",
     "id": "84253a96",
     "status": "open",
     "title": "NVENC fallback resets progress and switches GPU to CPU",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1.",
     "id": "b3a3b231",
     "status": "open",
     "title": "NVENC tests use a fake encoder; no test of a real mid-encode failure",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1. Round 5's .partial outputs may cover it, but no document says so: verify, then close.",
     "id": "9f66e994",
     "status": "open",
     "title": "\"Sobrescribir\" + cancel at start deletes the old file",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1.",
     "id": "602569ee",
     "status": "open",
     "title": "Private pool during GPU warm-up opens extra CUDA contexts; VRAM not counted",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1.",
     "id": "8d7cd95d",
     "status": "open",
     "title": "engine:info keeps a CUDA context (~240 MiB) while the engine lives",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1; marked as a known shortcut in the preset editor code.",
     "id": "57be4834",
     "status": "open",
     "title": "Preset editor does not update Turbo live when engine:info arrives",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1.",
     "id": "8db76954",
     "status": "open",
     "title": "GPU colour: rare LUT-corner error (tolerance +1)",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1.",
     "id": "bc98514e",
     "status": "open",
     "title": "A non-representative first frame may pick the slow colour path",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Accepted, not fixed in run 1. Legacy desktop/ app; matters only if it is used again.",
     "id": "6987aa3e",
     "status": "open",
     "title": "Frozen Electron app ignores turbo, verify_pending, skipped and include_audio",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Failed in the full desktop-qt run on the round 5 final commit (10 s against the 5 s limit) but passed in the next full run, after the free-port change, on an idle machine. Timing-sensitive: decide whether to loosen the limit or measure it differently.",
     "id": "e3ecc004",
     "status": "open",
     "title": "Flaky: test_adding_many_files_is_quick fails under load",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "ROUND5_PLAN.md:192; no resolution recorded.",
     "id": "309361b6",
     "status": "open",
     "title": "Round 5 check: Supr confirmation matches the row ✕",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "ROUND5_PLAN.md:192; no resolution recorded (commit 4a778e3 mentions \"close dialog counts Turbo verification\", not confirmed as the check).",
     "id": "a57e1b8a",
     "status": "open",
     "title": "Round 5 check: Turbo background verify counts as \"verificando\" in the close dialog",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "ROUND5_PLAN.md:204, 211: heavy-implementer launched, report in round5\\F_levels\\, log says \"Waiting on F\"; no outcome recorded. Context: AME outputs show a 1.0040 luma gain and black offsets that our encoder does not reproduce (FORMAT.md:263-275).",
     "id": "a2c86fe0",
     "status": "open",
     "title": "Record the outcome of F (AME levels analysis)",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Noted in the round 2 hand-off; never investigated.",
     "id": "66453b3f",
     "status": "open",
     "title": "Real queue.json and settings.json changed on 14/10 06:48–06:50; cause not investigated",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Suggested as a next step in the run 1 report, not decided. GPU colour is NotchLC-only today (HAP was slower); the ProRes/HAP/H.264 colour path runs at about 3.7 fps at 1080p on one process.",
     "id": "113b2a48",
     "status": "open",
     "title": "GPU colour for H.264, ProRes and HAP",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "\"Turbo/max PSNR >= AME Best\" is not proven structurally (AME luma gain and black offsets). Suggested: export the G001C001 clip from AME at Optimal, Excellent, Very Good and Good to compare.",
     "id": "d869fc05",
     "status": "open",
     "title": "DECIDE: Turbo vs AME Best claim",
     "type": "idea"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Four run 1 commits were written by Fable; only one carries the Fable trailer, the other three carry an Opus trailer. History not rewritten.",
     "id": "fb29bb38",
     "status": "open",
     "title": "DECIDE: wrong Opus trailers on Fable commits",
     "type": "idea"
    },
    {
     "created_at": "2026-10-16T07:54:01+00:00",
     "details": "Another session committed to dannyfm-ui main (\"README: a frozen app needs pathex as well as the data files\"); the run log says to report it to Danny. Not resolved in the repo.",
     "id": "0516a07f",
     "status": "open",
     "title": "DECIDE: dannyfm-ui commit 894b6e7 from another session",
     "type": "idea"
    }
   ],
   "name": "FrameMorph",
   "next_step": "Approve 0.3.0 screenshots and run the manual checks with real hardware",
   "phases": [
    {
     "id": "7be61a5e",
     "name": "Encoder NotchLC nativo (spike y primera versión)",
     "notes": "Encoder NotchLC propio con numba y LZ4, sin depender de AME: alfa, audio PCM, herramienta de QA y empaquetado con PyInstaller. Ramas aún sin fusionar en master.",
     "status": "done"
    },
    {
     "id": "2fd38d09",
     "name": "Motor por lotes y nueva UI PySide6",
     "notes": "Pool de procesos, codificación por segmentos, calidad Turbo y verificación en segundo plano. La UI pasa a PySide6 con dannyfm-ui y una cola al estilo Media Encoder; la app Electron queda congelada.",
     "status": "done"
    },
    {
     "id": "7bc6fca2",
     "name": "Run 1: GPU, color OCIO, NVENC y cola Qt",
     "notes": "NotchLC en GPU CUDA con caída a CPU, color OCIO en GPU, H.264 con NVENC, cola, ajustes e inspector en Qt, especificación con mockups y Turbo por encima de 100 fps. Quedan comprobaciones manuales.",
     "status": "done"
    },
    {
     "id": "5c38587a",
     "name": "Run 3: seguridad y rediseño B",
     "notes": "Cerrados los hallazgos de la auditoría de seguridad: secreto por arranque, reto-respuesta mutuo y validación de rutas. Ampliaciones de dannyfm-ui y rediseño B: cabina, cinta de lote, cola densa e inspector.",
     "status": "done"
    },
    {
     "id": "02799686",
     "name": "Run 4 y rondas 2–3: correcciones del rediseño",
     "notes": "Correcciones del rediseño B: preset propio, ETA del lote, NotchLC «Best», tamaño de interfaz, cajón Origen y nueva versión por defecto si la salida existe. Su aprobación pasa a la ronda 5.",
     "status": "done"
    },
    {
     "id": "96e31ec8",
     "name": "Marca FrameMorph e instalador de Windows (0.2.0)",
     "notes": "Nombre, logo, icono y pantalla de inicio de FrameMorph; instalador Inno Setup en español que detecta una versión instalada; un único archivo VERSION. No consta prueba de instalación en otra máquina.",
     "status": "done"
    },
    {
     "id": "89770af8",
     "name": "Ronda 5: FrameMorph 0.3.0",
     "notes": "Todos los ítems de la ronda hechos: formulario de trabajo único, comparador, salidas .partial, alfa por trabajo y cierre ordenado del motor. Versión 0.3.0 e instalador construido. Lo pendiente está en los ítems.",
     "status": "done"
    },
    {
     "id": "e6416243",
     "name": "Migración a dannyfm-ui fijado por versión",
     "notes": "La app usa dannyfm-ui v0.2.0 fijado por commit, sin modo editable, y deja su fork propio. Reglas del paquete compartido en CLAUDE.md. No consta una suite completa después del cambio.",
     "status": "done"
    },
    {
     "gate": "manual_test",
     "gate_approved": false,
     "gate_reason": "Needs real hardware (disguise, AME, non-NVIDIA/low-VRAM PCs, network drives) and Danny's screenshot approval.",
     "gate_set_by": "agent",
     "id": "18f7df74",
     "name": "Validación manual en hardware real",
     "notes": "Comprobaciones con hardware real: pack de prueba en disguise, Turbo en disguise y AME, app con motor real, unidades de red lentas, equipos sin NVIDIA o con poca VRAM y reproducción NVENC.",
     "status": "done"
    },
    {
     "gate": "manual_test",
     "gate_approved": false,
     "gate_reason": "Needs disguise and Pixera playback of >4 GB and real clips; merge to master only after Danny validates.",
     "gate_set_by": "agent",
     "id": "3db7944b",
     "name": "Validación en media servers y merge a master",
     "notes": "Validar archivos de más de 4 GB y clips reales en disguise y Pixera antes de fusionar en master. Ninguna rama de trabajo está fusionada todavía.",
     "status": "todo"
    },
    {
     "id": "7ff1adfb",
     "name": "Sprint 3: secuencias EXR (OpenImageIO + OCIO)",
     "notes": "Detección de secuencias e integración de OpenImageIO con OCIO fotograma a fotograma. EXR entra en el MVP; los documentos no indican su estado.",
     "status": "todo"
    },
    {
     "id": "b1520d42",
     "name": "v1.1: upscale con NVIDIA RTX Video Super Resolution",
     "notes": "Comprometido. Abierto: integrarlo con el SDK Maxine o con un envoltorio CLI, y comparar la calidad con Topaz en material LED real.",
     "status": "todo"
    },
    {
     "id": "807c7008",
     "name": "Fase 2: presets compartibles, multisalida e informes",
     "notes": "Presets de show compartibles, multisalida, archivo de show Proyecto > Actos > Canciones, informes PDF con miniaturas, manifiestos de gira con hashes y notificaciones. Sin estado.",
     "status": "todo"
    },
    {
     "id": "b236b344",
     "name": "Fase 3: proyectos, grupos y versionado",
     "notes": "Propuesta pendiente de revisión, nada construido: proyectos, grupos, nombres, carpetas vigiladas, renombrado, huellas de contenido, pestaña Proyecto y entrega a servidor. Hay mockups.",
     "status": "todo"
    }
   ],
   "repo_path": "C:\\Users\\moyad\\Documents\\Visual Projects\\Notchpack",
   "status": "active",
   "updated_at": "2026-10-16T09:05:47+00:00"
  },
  {
   "decisions": [
    {
     "date": "2026-10-16T08:27:41+00:00",
     "decision": "Los agentes no pueden borrar una fase con gate",
     "reason": "Borrar la fase sería una forma de saltarse el gate"
    }
   ],
   "description": "Hub local de proyectos: dashboard + MCP compartido entre Claude Desktop y Claude Code + mensajería entre sesiones",
   "id": "project-hub",
   "items": [
    {
     "created_at": "2026-10-16T07:59:07+00:00",
     "details": "Con datos reales (FrameMorph: 18 fases, notas largas) el diseño actual no se lee bien. Las letras B/I/F de los items no se entienden: la leyenda solo está en la cabecera y el tipo se repite debajo. Revisar cuando el hub tenga uso real.",
     "id": "892dcf46",
     "status": "planned",
     "title": "Rediseño del dashboard para que se lea bien de un vistazo",
     "type": "future_request"
    }
   ],
   "name": "project-hub",
   "next_step": "Rediseño: 3 propuestas de mockup (A cockpit, B split, C briefing) en curso con datos reales",
   "phases": [
    {
     "id": "5295032d",
     "name": "Datos y tests",
     "notes": "",
     "status": "done"
    },
    {
     "id": "e0e4e86a",
     "name": "Servidor MCP",
     "notes": "",
     "status": "done"
    },
    {
     "id": "304b7362",
     "name": "Dashboard",
     "notes": "Aprobado frente al mockup B",
     "status": "done"
    },
    {
     "id": "18deee33",
     "name": "CLI session-start y README",
     "notes": "",
     "status": "done"
    },
    {
     "id": "914dca55",
     "name": "Despliegue en el portátil",
     "notes": "Configs, arranque automático, repos en GitHub y 3 proyectos dados de alta. Tailscale queda opcional.",
     "status": "done"
    },
    {
     "id": "c8e3808f",
     "name": "Reservas de recursos, maquetación y edición de fases",
     "notes": "Reservas con caducidad, texto que salta de línea, update_phase/delete_phase, límites de longitud. Tests de clic en el repo.",
     "status": "done"
    },
    {
     "gate": "review",
     "gate_approved": true,
     "gate_reason": "Aprobar las capturas de la UI de gates antes de dar la fase por hecha",
     "gate_set_by": "user",
     "id": "ec151efb",
     "name": "Gates por fase (review / manual_test)",
     "notes": "Gates hechos y aprobados: datos, MCP, CLI, BIBLIA, API y dashboard. Subido a origin.",
     "status": "done"
    },
    {
     "id": "0c017ecd",
     "name": "Rediseño: propuesta y mockups",
     "notes": "",
     "status": "in_progress"
    },
    {
     "gate": "review",
     "gate_approved": false,
     "gate_reason": "Danny elige una de las propuestas de mockup",
     "gate_set_by": "agent",
     "id": "2362a0a7",
     "name": "Rediseño: implementación",
     "notes": "",
     "status": "todo"
    },
    {
     "gate": "manual_test",
     "gate_approved": false,
     "gate_reason": "Danny revisa el dashboard rediseñado con sus proyectos reales",
     "gate_set_by": "agent",
     "id": "75b72c79",
     "name": "Rediseño: validación con datos reales",
     "notes": "",
     "status": "todo"
    }
   ],
   "repo_path": "C:\\Users\\moyad\\Documents\\Visual Projects\\ProjectsDashboard",
   "status": "active",
   "updated_at": "2026-10-16T08:56:37+00:00"
  },
  {
   "decisions": [
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "dannyfm-ui is consumed by exact commit pin, non-editable; changed only in its own repo; app-specific needs go in the extension layer, never a fork (R1-R3)",
     "reason": "So a change made for one app (StageTrack, FrameMorph) cannot reach the other until it deliberately adopts it. CLAUDE.md; pyproject.toml pin 7bff4166 (v0.2.0)."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "A sensor's \"serves\" list and a slot's home zone reference areas by stable uid, never by name",
     "reason": "A rename must not orphan a reference, and a deleted area must never silently widen a sensor's scope (deletion leaves an explicit \"serves nothing\" state). docs/spec/04-tracking.md 4.7; docs/spec/13-project-schema.md; d2a5c27, 647df2c."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Stop rewinds placed virtual agents to their placements; it never deletes them",
     "reason": "Placed agents are setup state, not runtime state. docs/spec/05-outputs.md 5.5; cd98c93."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Stop and mute release every receiver: TUIO empty alive, PSN info reset, DMX blackout, before sockets close",
     "reason": "Stop must leave nothing live on the wire; a receiver must be told the people are gone. docs/spec/05-outputs.md 5.5; 00f7ed8."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Per-area id mode: shared (default, one session allocator) or independent (own numbering, never colliding)",
     "reason": "Areas that need their own ids get them without breaking standard receivers; migrated projects keep today's shared behaviour. docs/spec/04-tracking.md 4.7; docs/spec/05 5.8; 68a0aee."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Project-file schema changes go through the migration registry: one @migration(N) step per version, upward only, a shipped step is never edited, the original is kept as one .bak on first save",
     "reason": "Old projects must open with their behaviour intact, never silently widened or narrowed. docs/spec/13-project-schema.md; core/migrations.py; c44751a."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Windows distribution is a one-folder PyInstaller bundle plus an Inno Setup installer; a build must pass a bundle smoke check before the installer is made",
     "reason": "A one-file exe unpacks on every launch (slow on a show machine); an installer must never wrap an exe that cannot start. packaging/stagetrack.spec; packaging/build.ps1; e84c714."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Signal (dark) is the default theme; Graphite and Daylight are alternatives",
     "reason": "The app runs at front of house in a dark venue; a light UI would dazzle the operator and spill onto the stage. docs/spec/09-gui.md; gui/theme.py."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Tracked areas and hot areas are two separate lists, each with its own panel",
     "reason": "A hot area triggers actions and is a different thing from an area that scopes tracking. docs/spec/06-hotareas.md 6.1-6.2."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "One tracker per space with a shared id allocator; only the floor is clipped to the room; detections route by surface",
     "reason": "Walls and floor track independently without colliding ids. docs/spec/07-scenarios-and-spaces.md 7.4."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Accepted trade-offs: outputs are sent from the tracker thread; a solid obstacle ends a track instead of coasting; track ids are monotonic and never reused (PSN recycles 16-bit slots)",
     "reason": "Documented as deliberate limitations. docs/spec/16-limitations.md 16.4; docs/backlog.md accepted trade-offs."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Wire formats do not change without a reason",
     "reason": "Receivers in the field depend on them. .claude/loop.md."
    },
    {
     "date": "2026-10-16T08:05:38+00:00",
     "decision": "Build tests run against a sandbox (build.ps1 -DistRoot/-OutputDir); a refused build leaves the existing installer in place",
     "reason": "Every full suite run used to delete the real installer. tests/test_build_script.py; e64b794."
    }
   ],
   "description": "Tracking multi-sensor de personas para eventos en vivo (Orbbec, Azure Kinect, Hokuyo) con salida TUIO/OSC/PSN/DMX",
   "id": "stagetrack",
   "items": [
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "Solo en la primera apertura tras instalar; al volver a abrir sale bien. Sin diagnosticar. Aparece en limitaciones y en el backlog (nivel 2).",
     "id": "08d34937",
     "status": "open",
     "title": "El icono de la barra de tareas sale en blanco la primera vez que se abre",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "Limitaciones dice que la versión del formato de proyecto es 1 y que nunca se ha migrado un archivo real; el código está en la 4 con la cadena completa probada. El esquema dice 3. La especificación antigua da una cifra de tests vieja.",
     "id": "859023a6",
     "status": "open",
     "title": "Documentación desactualizada respecto al código",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "El generador se ha desviado de los archivos de presets que se entregan. Se corrigió su descripción, pero la desviación sigue. La especificación dice que no se vuelva a ejecutar. Backlog nivel 3.",
     "id": "d043fd27",
     "status": "open",
     "title": "Regenerar los presets con gen_presets.py cambiaría los que se distribuyen",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "RecordingConfig.format y DmxActionSettings.protocol existen en el esquema pero no hacen nada. Documentado en el apéndice de limitaciones.",
     "id": "8c1a7776",
     "status": "open",
     "title": "Ajustes sin efecto: formato de grabación y protocolo de las acciones DMX",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "En una ejecución completa en paralelo tardó 8,2 s con un límite de 8 s; ejecutado solo pasa. No se ha cambiado el límite.",
     "id": "c61c69b2",
     "status": "open",
     "title": "El test de tiempo del planificador falla a veces con la máquina cargada",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "Limitaciones y backlog dicen que la rejilla solo cubre el brazo mayor de una L; la especificación de espacios y un commit de la sesión autónoma dicen que ya está resuelto y probado. El repo se contradice.",
     "id": "e0c9cae2",
     "status": "open",
     "title": "Sin aclarar: rejilla de sensores por defecto en salas en forma de L",
     "type": "bug"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "Sigue listando cosas que commits posteriores dicen haber resuelto (presets, rejilla por defecto, migración de proyectos). Hace falta repasarlo y marcar lo cerrado.",
     "id": "92b9214a",
     "status": "open",
     "title": "Sin aclarar: ¿está al día el backlog?",
     "type": "idea"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "Las notas del bucle autónomo dicen que las fases E y F se trabajan en sesiones interactivas; el repo no dice qué elementos de la F siguen abiertos, si alguno.",
     "id": "dad875c2",
     "status": "open",
     "title": "Sin aclarar: qué queda de la fase F",
     "type": "idea"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "La cabecera del mapa de tests da un total mayor que la suma de las cifras de sus secciones. Sin conciliar.",
     "id": "184ff7bf",
     "status": "open",
     "title": "Sin aclarar: el total del mapa de tests no cuadra con sus secciones",
     "type": "idea"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "No hay archivo LICENSE ni licencia declarada en pyproject. Backlog nivel 1: decisión de Danny.",
     "id": "d56d5a32",
     "status": "open",
     "title": "Elegir una licencia para el proyecto",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "Los drivers existen pero no se han probado con dispositivos reales. Backlog nivel 1.",
     "id": "f10b18b3",
     "status": "open",
     "title": "Primera prueba con hardware real (Orbbec, Azure Kinect, Hokuyo)",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "Comprobar que los programas y equipos que reciben los datos los entienden bien. Backlog nivel 1.",
     "id": "b6fc82c8",
     "status": "open",
     "title": "Probar con receptores reales de TUIO, OSC, PSN y DMX",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "El servidor de control no pide autenticación y escucha en todas las interfaces, puerto 9000, por defecto. Backlog nivel 1.",
     "id": "4bf5d612",
     "status": "open",
     "title": "Decidir la autenticación del servidor de control OSC",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "Backlog nivel 2.",
     "id": "bf800b46",
     "status": "open",
     "title": "Medir la latencia y hacer una prueba de larga duración",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:16+00:00",
     "details": "El motor tiene un solo suelo y hoy se rechaza añadir otro. Backlog nivel 3.",
     "id": "bc982c61",
     "status": "open",
     "title": "Segunda planta: más de un suelo",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:17+00:00",
     "details": "Necesita una etapa de agrupamiento de puntos. Backlog nivel 3.",
     "id": "8d87420e",
     "status": "open",
     "title": "Soporte de LiDAR 3D",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:17+00:00",
     "details": "Backlog nivel 3.",
     "id": "98418497",
     "status": "open",
     "title": "Más LiDAR 2D: SICK TiM, LMS y LRS",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:17+00:00",
     "details": "Backlog nivel 5, sin programar.",
     "id": "1bbbe126",
     "status": "open",
     "title": "Plugins para disguise, Notch, Unreal y Unity",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:17+00:00",
     "details": "Hoy solo se admite OBJ. Documentado en limitaciones y en la especificación de geometría.",
     "id": "c16e2a98",
     "status": "open",
     "title": "Importar el recinto en FBX",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:17+00:00",
     "details": "Sin construir. Documentado en limitaciones.",
     "id": "4c46bc1f",
     "status": "open",
     "title": "Informe del montaje en PDF",
     "type": "future_request"
    },
    {
     "created_at": "2026-10-16T08:05:17+00:00",
     "details": "Sin construir. Documentado en limitaciones y en la especificación de geometría.",
     "id": "3b6a7db3",
     "status": "open",
     "title": "Marcar puntos libres sobre el modelo del recinto",
     "type": "future_request"
    }
   ],
   "name": "StageTrack",
   "next_step": "Revisar y fusionar la rama extract-ui-theme en hotareas; después, que Danny decida la licencia y la autenticación del control OSC.",
   "phases": [
    {
     "id": "9b90b885",
     "name": "Versión base (rama main)",
     "notes": "Primera versión completa del programa, la que está en la rama main. Desde entonces main no ha cambiado; todo lo posterior vive en otras ramas.",
     "status": "done"
    },
    {
     "id": "c52a180b",
     "name": "Zonas activas: disparadores, Art-Net/sACN y acciones",
     "notes": "Zonas que disparan acciones cuando alguien entra: modelo de datos, disparadores, salida Art-Net/sACN, acciones y comandos de control.",
     "status": "done"
    },
    {
     "id": "722e5b08",
     "name": "Base de la interfaz: espacios, menús y bienvenida",
     "notes": "Espacios de trabajo, preferencias por máquina, editor de zonas, menús con deshacer, pestañas de salidas, pantalla de bienvenida con demos, vista previa en vivo y monitor de datos.",
     "status": "done"
    },
    {
     "id": "390739d0",
     "name": "Sensores y salidas: catálogo, asistente, pruebas, DMX",
     "notes": "Catálogo de dispositivos, asistente para añadir sensores, botón para enviar un mensaje de prueba a cada salida y tarjeta de DMX.",
     "status": "done"
    },
    {
     "id": "4cf561fa",
     "name": "Geometría del recinto: OBJ, cobertura y rejilla",
     "notes": "Importar el recinto en OBJ con unidades, ejes y origen; cobertura calculada contra el edificio; rejilla del suelo. Quedan fuera FBX y marcar puntos libres en el modelo.",
     "status": "done"
    },
    {
     "id": "e0c105c1",
     "name": "Interfaz de operador y planificación de zonas",
     "notes": "Interfaz de operador sin marco de ventana, paneles laterales y barra de transporte; planificación de zonas, sensores en los bordes, gizmo de transformación y paredes inclinadas.",
     "status": "done"
    },
    {
     "id": "b03d0476",
     "name": "Auditorías: selección, motor, diseño y funciones",
     "notes": "Cuatro auditorías (selección en 3D, motor, diseño y funciones) con sus arreglos, fusionadas en la rama de trabajo.",
     "status": "done"
    },
    {
     "id": "abf4fa0a",
     "name": "Fase E: banda táctil, temas y huecos de intérprete",
     "notes": "Banda táctil en las paredes, tres temas de color (Signal, Graphite, Daylight) y huecos de intérprete que siguen a una persona concreta.",
     "status": "done"
    },
    {
     "id": "9e9bc65b",
     "name": "Fase F: defectos y sensores asignados a zonas",
     "notes": "Seis defectos arreglados, mejoras del gizmo, copiar y pegar, y que cada sensor sirva solo a sus zonas con numeración propia por zona. El repo no dice si queda algo de esta fase.",
     "status": "done"
    },
    {
     "id": "e6044282",
     "name": "Stop silencioso y migración de proyectos antiguos",
     "notes": "Stop deja todo en silencio y avisa a los receptores; los agentes virtuales vuelven a su sitio. Los proyectos antiguos se actualizan solos al abrirse y guardan una copia del original.",
     "status": "done"
    },
    {
     "id": "ead3ecd8",
     "name": "Sesión autónoma del backlog",
     "notes": "Una sesión autónoma trabajó el backlog y su rama se fusionó; incluye el panel de capas en tres grupos. No está claro qué entradas del backlog dejó cerradas del todo.",
     "status": "done"
    },
    {
     "id": "07d3ca29",
     "name": "Interfaz compartida dannyfm-ui y build más seguro",
     "notes": "La interfaz se separó en el paquete compartido dannyfm-ui, fijado en v0.2.0. El build comprueba que el programa arranca antes de crear el instalador. Rama sin fusionar.",
     "status": "done"
    },
    {
     "id": "8f38e0b7",
     "name": "Fusionar extract-ui-theme en hotareas y luego en main",
     "notes": "",
     "status": "todo"
    },
    {
     "id": "9798abfd",
     "name": "Backlog nivel 1: decisiones de Danny",
     "notes": "",
     "status": "todo"
    },
    {
     "id": "558a9570",
     "name": "Backlog nivel 2: latencia, larga duración e icono",
     "notes": "",
     "status": "todo"
    },
    {
     "id": "a8ac45ac",
     "name": "Backlog nivel 3: más sensores, plantas y presets",
     "notes": "",
     "status": "todo"
    },
    {
     "id": "80f16ee0",
     "name": "Backlog nivel 5: plugins para hosts (sin programar)",
     "notes": "",
     "status": "todo"
    }
   ],
   "repo_path": "C:\\Users\\moyad\\Documents\\Visual Projects\\Tracking App",
   "status": "active",
   "updated_at": "2026-10-16T08:14:32+00:00"
  }
 ],
 "messages": [
  {
   "body": "StageTrack (branch extract-ui-theme, not merged, not pushed):\n- 36443c1 consumes dannyfm-ui v0.2.0 pinned by hash, non-editable; app_id \"stagetrack\".\n- e64b794 build.ps1 deletes the installer only after its checks pass; build tests run against a sandbox (-DistRoot/-OutputDir) and cannot touch real dist or packaging\\Output; new test proves a refused build keeps the installer.\n- c5225e4 build.ps1 default paths resolved after param() (Windows PowerShell has no $PSScriptRoot there).\n- b99cbd6 CLAUDE.md: project-hub rules.\n- Suite 2700 passed (xdist). Fresh installer packaging\\Output\\StageTrack-Setup-0.1.0.exe built 2026-10-16 10:03, smoke check passed.\ndannyfm-ui: v0.2.0 (7bff416) unchanged; ac39c51 ignores the package's own .venv (83 tests green there).\nFrameMorph: e7e3c9c migrated to the pinned v0.2.0 (401 passed, 2 load-related failures that pass alone); the fork worktree ../dannyfm-ui-notchpack is removed, its branch kept and archived on the remote.\nproject-hub: phases, items, decisions and next_step filled from the repo.",
   "created_at": "2026-10-16T08:05:47+00:00",
   "from_project": "stagetrack",
   "id": "21669ad4",
   "kind": "report",
   "status": "unread",
   "title": "Session 2026-10-16: dannyfm-ui shared by pin, safer builds, project-hub filled",
   "to_project": "stagetrack"
  },
  {
   "body": "+ Gates review y manual_test con set_gate, approve y waiting-for-you\n+ set_phase_status rechaza a agentes en fases con gate\n+ Línea 'Autonomous work allowed up to phase N' en get_project, session-start y BIBLIA\n+ Dashboard: badges, controles, panel 'waiting for you'\n+ 106 tests y 6 checks de navegador en verde\n→ Falta: tu aprobación visual (mockups/impl-B-overview-gates.png, impl-B-project-gates.png) y commit",
   "created_at": "2026-10-16T08:27:41+00:00",
   "from_project": "project-hub",
   "id": "f1c194ed",
   "kind": "report",
   "status": "unread",
   "title": "Gates por fase listos para revisión",
   "to_project": "project-hub"
  },
  {
   "body": "+ Gates por fase en origin, fase marcada done\n+ Skill hub-sync: reclama task:<id> antes de trabajar un mensaje y lo libera al terminar\n→ Siguiente: probar /loop 5m /hub-sync en un repo registrado",
   "created_at": "2026-10-16T08:47:28+00:00",
   "from_project": "project-hub",
   "id": "2961c5a6",
   "kind": "report",
   "status": "unread",
   "title": "Gates subidos y fase cerrada",
   "to_project": "project-hub"
  },
  {
   "body": "Test task from Danny's project-hub chat, to verify that /loop + hub-sync picks up tasks on its own. Read-only: do not modify, commit or push anything. Post a report message with: current branch, whether the working tree is clean (list changed files if not), the last 3 commit subjects, and the time you picked up this task. Then mark this message done.",
   "created_at": "2026-10-16T08:49:26+00:00",
   "from_project": "user",
   "id": "df11bc36",
   "kind": "task",
   "status": "done",
   "title": "Prueba de hub-sync: informe de estado del repo",
   "to_project": "stagetrack"
  },
  {
   "body": "From Danny's project-hub chat (Danny asked the chat to run this redesign). This is also the first real test of /loop + hub-sync.\n\nSTEP 0 - gates (do this first, with set_gate):\n- Phase 2362a0a7 \"Rediseño: implementación\": gate review, reason \"Danny elige una de las propuestas de mockup\".\n- Phase 75b72c79 \"Rediseño: validación con datos reales\": gate manual_test, reason \"Danny revisa el dashboard rediseñado con sus proyectos reales\".\n\nSTEP 1 - do phase 0c017ecd \"Rediseño: propuesta y mockups\" only. Do not touch the dashboard code in this phase.\n\nProblem: with real data the dashboard is hard to read at a glance. Real projects now have 14-17 phases, 20-25 items and long notes (see framemorph and stagetrack in the real hub; read them through the MCP tools, never edit them). Concrete issues Danny reported:\n- Phase cards: with 14-17 phases the timeline wraps into several rows of tall cards and it is hard to see where the project is.\n- Item type letters B / I / F are not understood: the legend is only in the section header and the type is repeated as text below each item.\n- Long project views need a lot of scrolling; the important things (current phase, next step, gates waiting for Danny, unread reports) do not stand out.\n\nDeliver 2 or 3 clearly different proposals as static HTML mockups in mockups/ (redesign-A.html, redesign-B.html, ...) with PNG screenshots of the overview and of a project view, all rendered with a copy of the real framemorph and stagetrack data. Keep the current dark Console identity unless a proposal deliberately departs from it, and say so. Every proposal must: make the current phase, next step, waiting gates and unread reports visible without scrolling; make item types self-explanatory; handle 20 phases and 30 items; show phase notes without overflowing.\n\nWrite a short comparison (one paragraph per proposal: idea, what it fixes, trade-off) in your report message. Mark phase 0c017ecd done, post the report, mark this task done, and stop: the review gate on the implementation phase is where Danny chooses.",
   "created_at": "2026-10-16T08:51:16+00:00",
   "from_project": "user",
   "id": "6f779bff",
   "kind": "task",
   "status": "read",
   "title": "Rediseño del dashboard: gates y fase de propuesta con mockups",
   "to_project": "project-hub"
  },
  {
   "body": "hub-sync found no open tasks. The next phase, Validación manual en hardware real, now has a manual_test gate. It needs the 0.3.0 screenshots approved and the hardware checks listed in the items: disguise pack, Turbo in disguise/AME, app with the real engine, network drives, CPU fallback, NVENC playback. No autonomous work runs until the gate is approved.",
   "created_at": "2026-10-16T09:01:06+00:00",
   "from_project": "framemorph",
   "id": "b2811e35",
   "kind": "report",
   "status": "unread",
   "title": "Hardware validation waits for Danny",
   "to_project": "framemorph"
  },
  {
   "body": "Hardware validation is marked done. The next phase, Validación en media servers y merge a master, now has a manual_test gate. Engine tests already cover the >4 GB container structure (64-bit chunk offsets). Still to do on real hardware: play a >4 GB NotchLC file and real clips in disguise and Pixera. The work branches merge to master only after that.",
   "created_at": "2026-10-16T09:05:51+00:00",
   "from_project": "framemorph",
   "id": "3a64c485",
   "kind": "report",
   "status": "unread",
   "title": "Media server validation waits for Danny",
   "to_project": "framemorph"
  }
 ],
 "leases": [
  {
   "acquired_at": "2026-10-16T08:54:05+00:00",
   "expires_at": "2026-10-16T09:58:40+00:00",
   "project_id": "project-hub",
   "purpose": "Rediseño del dashboard: gates y mockups",
   "resource": "task:6f779bff"
  }
 ]
};
// ?stress=1 pads every project to 20 phases and 30 items with filler rows, to prove the layout scales.
(function () {
  if (!/[?&]stress=1/.test(location.search)) return;
  const types = ["bug", "idea", "future_request"];
  for (const p of HUB.projects) {
    for (let i = p.phases.length; i < 20; i++)
      p.phases.push({ id: "f" + i, name: "Fase de relleno " + (i + 1) + " con un nombre bastante largo para probar el corte",
        notes: "Notas de relleno: texto largo para comprobar que las notas de fase no se salen de su caja aunque ocupen varias líneas y lleven rutas como C:/Users/moyad/Documents/Visual Projects.",
        status: "todo" });
    for (let i = p.items.length; i < 30; i++)
      p.items.push({ id: "i" + i, type: types[i % 3], status: "open", created_at: HUB.snapshot,
        title: "Ítem de relleno " + (i + 1) + ": título largo para comprobar el corte en la lista de ítems",
        details: "Detalle de relleno." });
  }
})();
