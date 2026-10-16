// Copy of the real project-hub data, taken by build_data.py. Do not edit by hand.
window.HUB = {
 "snapshot": "2026-10-16T09:39:56+00:00",
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
     "details": "Resolved: the 14/10 06:48–06:50 changes were Danny opening the app by hand (recorded in the project hand-off).",
     "id": "66453b3f",
     "status": "done",
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
     "id": "064158ed",
     "name": "Limpieza 0.3.x y cierre de pendientes",
     "notes": "",
     "status": "in_progress"
    },
    {
     "id": "365ff059",
     "name": "Tanda 6: idioma español / inglés (0.4.0)",
     "notes": "",
     "status": "todo"
    },
    {
     "id": "2fe0d43b",
     "name": "Tanda 7a: medida de decodificación para el visor",
     "notes": "",
     "status": "todo"
    },
    {
     "id": "bfc475b1",
     "name": "Tanda 7b: visor de vídeo integrado (0.5.0)",
     "notes": "",
     "status": "todo"
    },
    {
     "id": "cedb25c3",
     "name": "Rendimiento: alfa en GPU y color GPU en HAP/ProRes/H.264",
     "notes": "",
     "status": "todo"
    },
    {
     "gate": "manual_test",
     "gate_approved": false,
     "gate_reason": "Needs real hardware (disguise, AME, non-NVIDIA/low-VRAM PCs, network drives) and Danny's screenshot approval.",
     "gate_set_by": "user",
     "id": "18f7df74",
     "name": "Validación manual en hardware real",
     "notes": "Marcada como done por error el 16/10: las pruebas con hardware real no están hechas. Quedan para más adelante, con gate manual_test.",
     "status": "todo"
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
   "updated_at": "2026-10-16T09:10:41+00:00"
  },
  {
   "decisions": [
    {
     "date": "2026-10-16T08:27:41+00:00",
     "decision": "Los agentes no pueden borrar una fase con gate",
     "reason": "Borrar la fase sería una forma de saltarse el gate"
    },
    {
     "date": "2026-10-16T09:39:39+00:00",
     "decision": "Main conserva el commit de los mockups A/B/C (sin subir); solo el código de C sale de main y queda en la rama redesign-c",
     "reason": "Volver main a origin habría quitado los mockups A/B/C y los datos que usa el mockup D; reescribir main no hacía falta para apartar la C"
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
   "next_step": "Mockup D en curso: organización de B, mejoras de C e identidad dannyfm-ui",
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
     "notes": "3 propuestas con datos reales: A riel cockpit, B lista partida (ambas Console), C briefing (se aparta de Console). HTML y capturas en mockups/redesign-*.",
     "status": "done"
    },
    {
     "gate": "review",
     "gate_approved": true,
     "gate_reason": "Danny elige una de las propuestas de mockup",
     "gate_set_by": "agent",
     "id": "2362a0a7",
     "name": "Rediseño: mockup D (mezcla con ADN dannyfm-ui)",
     "notes": "La C se paró a medias y queda en una rama como referencia. D: organización del diseño Console B, mejoras de la C y colores, fuente y espaciados de dannyfm-ui.",
     "status": "in_progress"
    },
    {
     "gate": "review",
     "gate_approved": true,
     "gate_reason": "Danny aprueba el mockup D antes de implementarlo",
     "gate_set_by": "agent",
     "id": "e8a10b56",
     "name": "Rediseño D: implementación",
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
    },
    {
     "id": "a768c7ed",
     "name": "Registro de actividad y botón Resumen",
     "notes": "",
     "status": "todo"
    }
   ],
   "repo_path": "C:\\Users\\moyad\\Documents\\Visual Projects\\ProjectsDashboard",
   "status": "active",
   "updated_at": "2026-10-16T09:39:50+00:00"
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
   "next_step": "Danny: aprobar y mover hotareas y main a extract-ui-theme (avance rápido, solo local); después decidir licencia y autenticación OSC.",
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
     "gate": "review",
     "gate_approved": true,
     "gate_reason": "Mover main y hotareas necesita el visto bueno de Danny: el permiso local bloqueó la fusión.",
     "gate_set_by": "agent",
     "id": "8f38e0b7",
     "name": "Fusionar extract-ui-theme en hotareas y luego en main",
     "notes": "Revisada: avance rápido limpio (hotareas +9, main +119), suite verde, solo CLAUDE.md cambió después. Mover las ramas lo bloqueó el permiso: lo hace Danny o lo autoriza.",
     "status": "todo"
    },
    {
     "gate": "review",
     "gate_approved": true,
     "gate_reason": "Licencia, autenticación OSC y pruebas con hardware real: decisiones de Danny.",
     "gate_set_by": "agent",
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
   "updated_at": "2026-10-16T09:37:58+00:00"
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
   "status": "done",
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
  },
  {
   "body": "+ Gates puestos: review en Rediseño: implementación, manual_test en validación\n+ mockups/redesign-A/B/C.html con capturas overview, proyecto (framemorph) y stress (20 fases, 30 ítems). Datos: copia real del hub.\n+ Las tres cumplen: fase actual, next step, gates y reports sin scroll a 1440x900; tipos con palabra; notas sin desbordar.\n\nA · Cockpit rail (Console): panel de estado de 4 celdas arriba y fases en un riel de una sola línea; la actual lleva nombre y notas debajo. Ítems en tres columnas Bugs / Ideas / Requests. Overview: tabla \"waiting for you\" y proyectos con mini riel. Coste: las otras fases solo muestran su número hasta pasar el ratón; se pierde el kanban por estado.\n\nB · Split ledger (Console): lista vertical de fases a la izquierda (hechas plegadas, actual abierta con notas) y panel \"now\" a la derecha. Ítems en tabla con etiqueta bug/idea/request y filtros con contador. Overview inbox-first. Coste: nombres de fase recortados (notas con un clic); tabla menos visual que el kanban.\n\nC · Briefing (se aparta de Console: fuente sans, 15px, más aire, esquinas redondeadas; misma paleta): resumen en frases arriba, avisos por gate y report, timeline vertical, ítems como listas con título y recuento. Overview con un bloque por proyecto, el más urgente primero. Coste: menos densa; con 30 ítems la columna se alarga.\n\n→ Elige A, B o C (o mezcla) y aprueba el gate de implementación.\nNota: playwright no está en el Python del sistema; las capturas se hicieron con un venv temporal.",
   "created_at": "2026-10-16T09:07:47+00:00",
   "from_project": "project-hub",
   "id": "b29941c0",
   "kind": "report",
   "status": "unread",
   "title": "Rediseño: 3 propuestas listas para elegir",
   "to_project": "project-hub"
  },
  {
   "body": "Phase: Limpieza 0.3.x y cierre de pendientes (064158ed). No gate.\n\nContext: FrameMorph (repo C:\\Users\\moyad\\Documents\\Visual Projects\\Notchpack), branch feature/gpu-ui, version 0.3.0, now on dannyfm-ui v0.2.0 pinned by commit. The engine already picks a free port. Several round 5 leftovers and open hub items need closing.\n\nRules for this task:\n- Do not merge to master. Commit on feature/gpu-ui.\n- Tests and offscreen runs set NOTCHPACK_USER_DATA to a temp folder; never touch %APPDATA%\\notchpack-desktop. Set TEMP and TMP to a private folder (e.g. %LOCALAPPDATA%\\Temp\\framemorph-cleanup) for every process, so painted UI assets never clash with other sessions.\n- Do not modify dannyfm-ui or StageTrack. If FrameMorph needs something the pinned package lacks, report it; do not fork.\n- Never run the FrameMorph installer. Never filter test output in a way that could hide failures. Never weaken a test or raise a limit to make it pass.\n- While working, run only the tests for what you change; run the full engine and desktop-qt suites (including end-to-end) once, at the end, on the final commit.\n\nWork:\n1. Row audio and alpha icons: today they only switch the setting off. Show each icon whenever the source has that stream and the job's codec can carry it; draw it dimmed when the setting is off and normal when on; a click toggles it both ways and follows the selection rule (on a selected row it applies to the whole selection). Tooltips \"Incluir audio\" / \"Incluir alfa\" with the current state. Tests, plus an offscreen screenshot in the report.\n2. Item e3ecc004 (test_adding_many_files_is_quick, 10 s in one full run, ~2 s alone): first check whether earlier tests leak state (windows, timers, threads, queue contents) that slows it; fix any leak in the tests. Then make the test measure the app's own work so machine load cannot fail it (e.g. process CPU time, or counting the expensive operations per added file), keeping the same intent: adding 200 files must stay cheap. Do not just raise the limit. Close the item with what you found.\n3. Item 9f66e994 (\"Sobrescribir\" + cancel at start deletes the old file): write a test that reproduces it on the current .partial mechanism. If it no longer happens, close the item citing the test; if it does, fix it and close.\n4. Items 309361b6 (Supr confirmation matches the row ✕) and a57e1b8a (Turbo background verification counts as in progress in the close dialog): confirm each with a test, fix if needed, close both.\n5. Engine start failures: if the engine exits during startup, the splash shows a short readable message (e.g. \"No se pudo abrir un puerto de red\", \"Falta un archivo del programa: <name>\") and a button that opens the logs folder, instead of the raw Python/PyInstaller text; the full traceback stays in engine.log. Test it with a simulated startup failure.\n6. Item a2c86fe0 (outcome of F): post a report to this inbox with the full F table from round5\\F_levels\\: for each AME level (Best, Optimal, Excellent, Very Good, Good) and each FrameMorph level (max, high, standard, small, turbo) on G001C001: file size, average bitrate, AME level gain and offset against the source, PSNR and ΔE00 both raw and after compensating AME's gain and offset, plus your proposed name mapping and a one-line honest description for Turbo. Rename nothing; Danny decides. Then mark the item done pointing to that report.\n7. Item 66453b3f: close it as resolved. The 14/10 06:48–06:50 changes to queue.json and settings.json were Danny opening the app by hand (recorded in the project hand-off).\n8. Run the full suites once at the end on the final commit and read every summary in full.\n9. If any app or engine code changed, set VERSION to 0.3.1 and build the installer from the final commit (cd desktop-qt; powershell -ExecutionPolicy Bypass -File packaging\\build.ps1); if only tests changed, do not build. Do not run it.\n\nReport: per point what changed and commit hashes, the e3ecc004 cause, full suite summaries, the installer file name and build number if built, and an updated manual check list for anything visible.",
   "created_at": "2026-10-16T09:09:07+00:00",
   "from_project": "user",
   "id": "68b1f156",
   "kind": "task",
   "status": "read",
   "title": "Phase \"Limpieza 0.3.x y cierre de pendientes\": round 5 leftovers and open items",
   "to_project": "framemorph"
  },
  {
   "body": "Phase: Tanda 6: idioma español / inglés (0.4.0) (365ff059). Starts after phase \"Limpieza 0.3.x y cierre de pendientes\" is done. Gate: review, set by you before the installer is built (step 6).\n\nContext: FrameMorph (repo C:\\Users\\moyad\\Documents\\Visual Projects\\Notchpack), branch feature/gpu-ui. Today every visible text is Spanish and written straight in the code; the Inno Setup installer is Spanish only. Choosing English in an older installer left the app in Spanish, which confused the user. Goal: a real Spanish/English interface.\n\nRules for this task:\n- Do not merge to master. Commit on feature/gpu-ui.\n- Tests and offscreen runs set NOTCHPACK_USER_DATA to a temp folder; never touch %APPDATA%\\notchpack-desktop. Set TEMP and TMP to a private folder (e.g. %LOCALAPPDATA%\\Temp\\framemorph-i18n) for every process.\n- Do not modify dannyfm-ui or StageTrack. If a text lives inside the pinned dannyfm-ui package, report it instead of forking.\n- Never run the FrameMorph installer. Never filter test output in a way that could hide failures.\n- While working, run only the tests for what you change; full engine and desktop-qt suites (including end-to-end) once at the end, on the final commit.\n\nWork:\n1. Move every user-visible text of desktop-qt to Qt's translation system (tr() with compiled .qm files bundled in the build): window and dialog texts, menus, buttons, tooltips, status bar and toast messages, splash phases and errors, empty states, shortcut lists, help texts. Engine messages that reach the user are mapped to translatable texts in the UI. Logs and engine.log stay in English.\n2. Spanish keeps today's wording exactly. English is a natural, short translation in the same tone; Notch quality names (Best, Optimal, …), codec names and units are not translated.\n3. Ajustes › Apariencia gets \"Idioma\" (Español / English). The change applies after restarting the app, and the settings dialog says so.\n4. Default language: the language chosen in the installer; if none is recorded, the Windows UI language when it is Spanish or English; otherwise Spanish. The installer offers Español / English again, shows its own pages and dialogs in the chosen language, and passes the choice to the app. An existing user setting always wins over the installer choice.\n5. Tests: a test that fails if a user-visible string in desktop-qt is not wrapped for translation; both languages load; switching the setting takes effect after restart; layouts with English texts do not clip (check the widest dialogs and the queue row).\n6. Offscreen screenshots of every main view and dialog in English and in Spanish, in C:\\Users\\moyad\\Desktop\\NotchPack_test\\redesign\\implemented\\round6\\. Then set a review gate on this phase (\"English texts and layouts need Danny's approval before the installer\"), post a report with the screenshot folder and the full list of English strings next to their Spanish source, and stop.\n7. After Danny approves: apply his text changes if any, set VERSION to 0.4.0, run the full suites once on the final commit, build the installer (cd desktop-qt; powershell -ExecutionPolicy Bypass -File packaging\\build.ps1) and confirm from the built files that the AppId is unchanged. Do not run it.\n\nReport: what changed with commit hashes, any text that could not be translated and why, full suite summaries, installer file name and build number, and a manual check list (install over 0.3.x choosing English; switch language in Ajustes; reinstall keeps the user's language).",
   "created_at": "2026-10-16T09:09:24+00:00",
   "from_project": "user",
   "id": "9f31a3fa",
   "kind": "task",
   "status": "unread",
   "title": "Phase \"Tanda 6: idioma español / inglés (0.4.0)\": Spanish and English interface",
   "to_project": "framemorph"
  },
  {
   "body": "Phase: Tanda 7a: medida de decodificación para el visor (2fe0d43b). Starts after phase \"Tanda 6: idioma español / inglés (0.4.0)\" is done. Gate: review, set by you at the end (decision for Danny).\n\nContext: FrameMorph (repo C:\\Users\\moyad\\Documents\\Visual Projects\\Notchpack), branch feature/gpu-ui. The next feature is an integrated video viewer built on the existing \"Comparar\" window: play the source, and compare the source with the real encoded output, frame-accurate. Before building it, we need to know whether FFmpeg's CPU decoders are fast enough, or whether FrameMorph needs its own GPU NotchLC decoder (the inverse of our CUDA encoder). This task only measures and reports; no app changes.\n\nRules for this task:\n- No changes to the app or engine code; measurement scripts go in engine/qa or a new tools folder and are committed on feature/gpu-ui. Do not merge to master.\n- Set TEMP and TMP to a private folder for every process; never touch %APPDATA%\\notchpack-desktop. Do not modify dannyfm-ui or StageTrack.\n\nMeasure, with the bundled FFmpeg, on this machine (report CPU and GPU models):\n1. Decode speed (fps) at 1920×1080 and 3840×2160 for: NotchLC from our encoder at max, high and turbo, and with alpha; NotchLC exported by AME (C:\\Users\\moyad\\Desktop\\NotchPack_test\\ame_exports\\); HAP, HAP Q, HAP Alpha; ProRes 422 HQ and 4444; H.264. Use 25, 50 and 60 fps clips where available. Report single-thread and multi-thread decode.\n2. The extra cost of getting each decoded frame to screen: conversion to 8-bit RGBA (and to a display-size image of about 1280 px wide), and the OCIO view transform on GPU at display size.\n3. Real-time verdict per format and resolution: can it play at the clip's own frame rate, at full resolution and at display size?\n4. For HAP: whether its DXT data could be uploaded to the GPU directly as compressed textures instead of being decoded on the CPU, and the expected gain.\n5. A short estimate for a FrameMorph GPU NotchLC decoder (CUDA, decoding straight into a texture): effort, risks, and how it would be validated bit-exact against FFmpeg's notchlc decoder on the test clips (colour, alpha, >4 GB).\n6. Whether FFmpeg's notchlc decoder output matches what our own verification step decodes, frame for frame, on our test clips.\n\nThen set a review gate on this phase (\"Danny decides whether the viewer needs a GPU NotchLC decoder\"), post a report with the tables and a recommendation, and stop.",
   "created_at": "2026-10-16T09:09:38+00:00",
   "from_project": "user",
   "id": "5e2521ea",
   "kind": "task",
   "status": "unread",
   "title": "Phase \"Tanda 7a: medida de decodificación para el visor\": can FFmpeg play our files in real time?",
   "to_project": "framemorph"
  },
  {
   "body": "Phase: Tanda 7b: visor de vídeo integrado (0.5.0) (bfc475b1). Starts only after phase \"Tanda 7a: medida de decodificación para el visor\" is done and Danny has approved its gate. If Danny decided to build a GPU NotchLC decoder, that comes as its own task; this task uses the decode path Danny approved in 7a, behind an interface that lets the decoder be swapped later. Gate: review, set by you before the installer is built (step 7).\n\nContext: FrameMorph (repo C:\\Users\\moyad\\Documents\\Visual Projects\\Notchpack), branch feature/gpu-ui. The \"Comparar\" window already exists (lado a lado, A/B with Space, cortinilla; live re-render on colour changes; follows the inspector's job). It shows still frames. Goal: turn it into the app's viewer, used to review clips before converting and to check finished outputs.\n\nRules for this task:\n- Do not merge to master. Commit on feature/gpu-ui.\n- Tests and offscreen runs set NOTCHPACK_USER_DATA to a temp folder; never touch %APPDATA%\\notchpack-desktop. Set TEMP and TMP to a private folder for every process.\n- Do not modify dannyfm-ui or StageTrack; if a hook is missing in the pinned package, report it.\n- Never run the FrameMorph installer. Never filter test output in a way that could hide failures.\n- While working, run only the tests for what you change; full engine and desktop-qt suites (including end-to-end) once at the end, on the final commit.\n- All new user-visible texts go through the translation system, in Spanish and English.\n\nWork:\n1. One window, \"Visor\" (the current Comparar window extended). Sources: the original; the original with the job's colour as preview (today's Después); and, for finished jobs, the real encoded output file. Comparison modes stay: lado a lado, A/B, cortinilla. \"Comparar con el original\" in a finished job's ··· menu opens original vs real output.\n2. Playback: Space play/pause, J/K/L (reverse, stop, forward; repeated presses speed up), ←/→ one frame, Home/End, loop toggle, timeline with timecode and frame number. When paused, always show the exact frame at full resolution. If playback cannot keep real time, scale playback to the display size and drop frames, and show that it is dropping; in comparison modes both sides stay on the same frame.\n3. Display: the job's OCIO view transform (the same \"(vista: …)\" as today) so log and ACES material looks right; alpha shown over a checkerboard, with a toggle to see the alpha channel alone.\n4. Audio: plays in sync (audio is the master clock, video follows), with mute and volume. Scrubbing silences audio.\n5. Opening: double-click a clip in Origen or a row in the queue opens the Visor on it. Size, mode and volume are remembered in settings.json.\n6. Tests: frame accuracy (the frame shown for a given time matches a reference decode), A/B and cortinilla stay on the same frame during playback, the output file is used for finished jobs, audio/video sync within one frame on a test clip.\n7. Offscreen screenshots of every mode, in C:\\Users\\moyad\\Desktop\\NotchPack_test\\redesign\\implemented\\round7\\. Then set a review gate on this phase (\"Viewer needs Danny's visual approval and a mouse test before the installer\"), post a report with measured playback fps per format and resolution and the screenshot folder, and stop.\n8. After Danny approves: apply his changes, set VERSION to 0.5.0, run the full suites once on the final commit, build the installer (cd desktop-qt; powershell -ExecutionPolicy Bypass -File packaging\\build.ps1), confirm the AppId is unchanged. Do not run it.\n\nReport: what changed with commit hashes, playback fps tables, full suite summaries, installer file name and build number, and a manual check list.",
   "created_at": "2026-10-16T09:09:56+00:00",
   "from_project": "user",
   "id": "af8e8a03",
   "kind": "task",
   "status": "unread",
   "title": "Phase \"Tanda 7b: visor de vídeo integrado (0.5.0)\": viewer built on the comparator",
   "to_project": "framemorph"
  },
  {
   "body": "Phase: Rendimiento: alfa en GPU y color GPU en HAP/ProRes/H.264 (cedb25c3). Starts after phase \"Tanda 7b: visor de vídeo integrado (0.5.0)\" is done. No gate.\n\nContext: FrameMorph (repo C:\\Users\\moyad\\Documents\\Visual Projects\\Notchpack), branch feature/gpu-ui. Two measured slow paths: (a) NotchLC with alpha on GPU runs about 3.6× slower than without alpha (about 40 fps against 145 fps on the round 5 test clip); (b) colour transforms for HAP, ProRes and H.264 run on CPU at about 3.7 fps at 1080p on one process (item 113b2a48); GPU colour exists only for NotchLC.\n\nRules for this task:\n- Do not merge to master. Commit on feature/gpu-ui.\n- Tests set NOTCHPACK_USER_DATA to a temp folder; never touch %APPDATA%\\notchpack-desktop. Set TEMP and TMP to a private folder for every process.\n- Do not modify dannyfm-ui or StageTrack. Never run the FrameMorph installer. Never filter test output in a way that could hide failures; never loosen a quality tolerance to make a test pass.\n- While working, run only the tests for what you change; full engine and desktop-qt suites (including end-to-end) once at the end, on the final commit.\n\nWork:\n1. Alpha: profile a NotchLC GPU encode with and without alpha on the same clip and find where the extra time goes (e.g. the alpha plane handled on CPU, extra transfers, serialisation). Fix it so alpha costs as little as possible on GPU. Output must stay identical (bit-exact) to the current encoder for the same input; prove it on the test clips. Report fps before and after.\n2. GPU colour for HAP, ProRes and H.264: reuse the existing GPU OCIO path (with its CPU residue LUT) where it is faster end to end; keep the CPU path as fallback. Results must match the current CPU path within the existing colour tolerances (ΔE00 and levels with engine/qa), on the colour test clips. Report fps per codec at 1080p and 2160p before and after, and keep CPU wherever GPU is not faster (as with HAP before).\n3. If any app or engine code changed, set VERSION to the next patch version after the current one, run the full suites once on the final commit and build the installer (cd desktop-qt; powershell -ExecutionPolicy Bypass -File packaging\\build.ps1). Do not run it. Close item 113b2a48 with the results.\n\nReport: profiling findings, what changed with commit hashes, fps tables before and after, accuracy results, full suite summaries, installer file name and build number.",
   "created_at": "2026-10-16T09:10:08+00:00",
   "from_project": "user",
   "id": "a5576e5f",
   "kind": "task",
   "status": "unread",
   "title": "Phase \"Rendimiento: alfa en GPU y color GPU en HAP/ProRes/H.264\": speed work",
   "to_project": "framemorph"
  },
  {
   "body": "Phase \"Validación manual en hardware real\" (18f7df74) was marked done by mistake; it is back to todo with its manual_test gate, and its items (0.3.0 screenshot approval and the manual checks) stay open. Report 3a64c485 (\"Hardware validation is marked done\") is obsolete. The new phases before it (064158ed, 365ff059, 2fe0d43b, bfc475b1, cedb25c3) each have a task in this inbox; work them in that order.",
   "created_at": "2026-10-16T09:10:21+00:00",
   "from_project": "user",
   "id": "9e92ed49",
   "kind": "message",
   "status": "unread",
   "title": "Hardware validation was marked done by mistake",
   "to_project": "framemorph"
  },
  {
   "body": "From Danny's project-hub chat: Danny chose proposal C (Briefing) from mockups/redesign-C.html for phase 2362a0a7 \"Rediseño: implementación\". Danny approves the review gate himself in the dashboard; start the phase only once it shows as approved.\n\nImplement C in the real dashboard, overview and project view, as in the mockup: summary sentences at the top, alerts for waiting gates and unread reports, vertical phase timeline with done phases collapsed and the current one highlighted, items as lists per type with the type explained, the overview with one block per project and the most urgent first. Keep every existing feature working (gates controls, resources, posting and marking messages, item moves, filters, keyboard shortcuts, polling without losing focus or typed text). Update the browser click checks to the new layout and keep them all passing, run the full test suite, and take new screenshots of the overview and of the framemorph and stagetrack project views with a copy of the real data.\n\nThen mark the phase done, post a report with the screenshots, and stop at the manual_test gate of phase 75b72c79, where Danny validates with his real projects.",
   "created_at": "2026-10-16T09:13:37+00:00",
   "from_project": "user",
   "id": "26006a44",
   "kind": "task",
   "status": "done",
   "title": "Rediseño: Danny elige la propuesta C (Briefing)",
   "to_project": "project-hub"
  },
  {
   "body": "From Danny's project-hub chat, approved by Danny. Addendum to task 26006a44 (implement proposal C); do both in the same phase 2362a0a7, once its gate is approved.\n\nDanny clicked the wrong card twice: the gate controls only appear on the selected card and cards look alike, so he marked a manual_test phase done instead of approving a review gate. In the redesigned dashboard:\n- A phase with a review gate that is waiting shows an \"Aprobar\" button always visible on its own card and in the \"waiting for you\" alert, without having to select the card first.\n- A manual_test phase shows its own \"Marcar como hecha\" button the same way.\n- Both actions ask for confirmation in a small inline dialog that names the project and the phase (\"¿Aprobar el gate de «Rediseño: implementación» en project-hub?\"), never a browser alert.\n- Changing a phase status to done from the status selector also asks for confirmation when the phase has a gate.\n- The selected card must be clearly distinct from the others.\nAdd click checks for these confirmations.",
   "created_at": "2026-10-16T09:16:25+00:00",
   "from_project": "user",
   "id": "ae400381",
   "kind": "task",
   "status": "done",
   "title": "Rediseño C: añadido sobre los controles de gates",
   "to_project": "project-hub"
  },
  {
   "body": "+ Leídas las tareas de implementar C y el añadido de los botones de gates\n→ No empiezo: el gate review de Rediseño: implementación sigue sin aprobar. En cuanto lo apruebes, el loop arranca las dos tareas juntas.\n! Rediseño: validación con datos reales aparece como done, aunque tiene un gate manual_test. Parece el clic equivocado que describes; devuélvela a todo en el dashboard si no era la intención.",
   "created_at": "2026-10-16T09:18:00+00:00",
   "from_project": "project-hub",
   "id": "277f5e00",
   "kind": "report",
   "status": "unread",
   "title": "Propuesta C: esperando tu aprobación del gate",
   "to_project": "project-hub"
  },
  {
   "body": "From Danny's project-hub chat, approved by Danny. Phase a768c7ed \"Registro de actividad y botón Resumen\". Start it only after phase 2362a0a7 \"Rediseño: implementación\" is done, and build it in the redesigned (proposal C) UI. No gate on this phase.\n\nGoal: when Danny wakes up he presses one button, sees what happened in every project since the last summary, and copies a short text per project to paste into that project's Claude chat, which then reads the details from the hub and plans the next steps. No AI is involved: the summary is assembled from hub data.\n\n1. Activity log: the data layer appends one event per change to activity/events.jsonl in the data folder, under the same lock and atomic-write rules: timestamp, project_id, event type (phase status changed, phase added/renamed/deleted, gate set/changed/approved/removed, item added/updated/closed, decision logged, message posted/marked, project updated), who did it (agent, dashboard or the message's from_project) and a short text (old → new where it applies). Existing data is not rewritten; history starts now.\n2. \"Resumen\" button in the dashboard: shows, per project with activity since the last summary, in this order: gates waiting for Danny, unread reports (title and body), phases that changed status, decisions logged by agents, items opened and closed, anything blocked. Projects with no activity get one line saying so. The time of the last summary is stored in the data folder; the view shows \"desde <fecha y hora>\" and Danny can also pick \"últimas 24 h\". Opening the summary marks the new point in time only when Danny presses \"Marcar como visto\", so closing the view by accident loses nothing.\n3. \"Copiar para el chat\" per project: copies a short Spanish text (at most about 6 lines) that states the period, what changed in one line each (phases done, number of new reports, number of agent decisions, gates waiting) and ends with: \"Revisa el proyecto <id> en project-hub (get_project y read_inbox) y prepara los siguientes pasos.\" It must not paste the full details; the chat reads them from the hub.\n4. MCP: add get_activity(project_id optional, since optional) so chats can read the same history.\n5. Tests: events written for each kind of change (including from the dashboard), the summary grouping and the \"since\" handling, the copied text, and a click check of the button, \"Marcar como visto\" and \"Copiar para el chat\". Use a temporary data folder, never the real one. Run the full suite and the click checks.\n\nThen mark the phase done, post a report with a screenshot of the summary built from a copy of the real data, and continue only with what the hub allows.",
   "created_at": "2026-10-16T09:20:53+00:00",
   "from_project": "user",
   "id": "89d0b4d6",
   "kind": "task",
   "status": "unread",
   "title": "Registro de actividad y botón \"Resumen\" con texto para pegar en cada chat",
   "to_project": "project-hub"
  },
  {
   "body": "Applies to every pending task in this inbox. Before launching a full test suite (the full engine suite, the full desktop-qt suite or the end-to-end run), reserve the resource \"cpu:full-suite\" with claim_resource. If it is taken, do not start the suite: work on something else in the task and try the claim again later. Release it with release_resource as soon as the suite finishes, whether it passed or failed. Targeted test runs during work do not need the reservation.",
   "created_at": "2026-10-16T09:26:57+00:00",
   "from_project": "user",
   "id": "c91a8873",
   "kind": "message",
   "status": "unread",
   "title": "Reserve \"cpu:full-suite\" before any full test run",
   "to_project": "framemorph"
  },
  {
   "body": "Revisado: hotareas y main son antecesores directos de extract-ui-theme, así que las dos fusiones son avances rápidos (hotareas +9 commits, main +119). La suite completa pasó (2700) y después solo cambió CLAUDE.md. El pin de dannyfm-ui es un hash completo. La rama auto/backlog ya está dentro.\nNo se movió ninguna rama: el permiso local bloqueó el cambio de main y hotareas. No hay remoto, así que no se publicaría nada.\nPara hacerlo: git fetch . extract-ui-theme:hotareas extract-ui-theme:main (no toca el árbol de trabajo).\nPuse una puerta de revisión en esta fase y en \"Backlog nivel 1\" (decisiones de Danny) para que el bucle no repita la fase. El cambio sin guardar en first_stage_test.yaml sigue intacto.",
   "created_at": "2026-10-16T09:29:47+00:00",
   "from_project": "stagetrack",
   "id": "f2dd1949",
   "kind": "report",
   "status": "unread",
   "title": "Fusión de extract-ui-theme lista para revisar, bloqueada por permiso",
   "to_project": "stagetrack"
  },
  {
   "body": "Repo: C:\\Users\\moyad\\Documents\\Visual Projects\\Tracking App (StageTrack). Branch extract-ui-theme holds the dannyfm-ui extraction (dannyfm-ui v0.2.0 pinned by hash, non-editable, app_id \"stagetrack\"), the build.ps1 bundle smoke check, the sandboxed build tests (-DistRoot/-OutputDir) and the project-hub rules in CLAUDE.md. It was branched from hotareas at c44751a and has never been merged.\n\nResource rule: before any full test suite run, claim the resource \"cpu:full-suite\" with claim_resource. If it is busy, do another part of this task and retry. Release it with release_resource when the suite finishes, including when it fails.\n\nDo not stop for confirmation; state findings in the report.\n\n1. Report the HEAD of extract-ui-theme and of hotareas, and list any commits on hotareas after c44751a. Both working trees must be clean; if not, stop and report.\n2. Merge extract-ui-theme into hotareas (fast-forward if possible). If there are conflicts, do not resolve anything that needs a design choice: set a gate on the phase \"Fusionar extract-ui-theme en hotareas y luego en main\", describe the conflicts, and stop.\n3. Full suite with xdist (-n auto), under the resource rule. It must be green. If the only failure is the planner timing test and it passes when run alone, report both timings as a flake (hub item c61c69b2) and do not change its limit.\n4. Run build.ps1 in full: the smoke check passes. Report the installer path and timestamp. Do not run the installer.\n5. Do not push. Do not delete extract-ui-theme. Do not touch main.\n\nDefinition of done: hotareas contains extract-ui-theme, suite green (or the planner flake reported), fresh installer built, report posted to the hub.",
   "created_at": "2026-10-16T09:30:37+00:00",
   "from_project": "user",
   "id": "e432f420",
   "kind": "task",
   "status": "read",
   "title": "1/5 Merge extract-ui-theme into hotareas",
   "to_project": "stagetrack"
  },
  {
   "body": "Start only after task \"1/5 Merge extract-ui-theme into hotareas\" is done. Work on branch hotareas.\n\nRepos (in C:\\Users\\moyad\\Documents\\Visual Projects): StageTrack (\"Tracking App\") and the shared UI package dannyfm-ui (..\\dannyfm-ui, remote https://github.com/DannyFM-Artist/dannyfm-ui.git, current release v0.2.0 at 7bff416, own venv at ..\\dannyfm-ui\\.venv). StageTrack pins the package by commit hash and installs it non-editable. The chrome colour tokens of the three themes (Signal, Graphite, Daylight) live in the package's themes.yaml. StageTrack's themes.yaml is an overlay with the 3D scene tokens, sensor and wall palettes and coverage ramps. The transport glyphs are in the package; the transport QSS is in StageTrack.\nRules: R1 dannyfm-ui changes only in its own repo, tests green, version bump, annotated tag. R2 apps pin an exact commit and install non-editable. R3 app-only things live in the app's extension layer. Do not touch FrameMorph (..\\Notchpack); it adopts v0.3.0 on its own decision.\n\nResource rule: before any full test suite run (StageTrack or package), claim the resource \"cpu:full-suite\" with claim_resource. If it is busy, do another part of this task and retry. Release it with release_resource when the suite finishes, including when it fails.\n\nProblem, confirmed by Danny on the installed build:\n- Daylight is too bright to work with (near-white surfaces).\n- In Daylight the 3D viewport is unreadable: light-blue grid, frusta and labels on a near-white background.\n- In Daylight the transport Play button is enabled but its glyph is invisible until pressed. This is a contrast problem, not a state problem. It matters in a show: an invisible Play is unacceptable.\n\nDo not stop for confirmation except at the gate below.\n\n1. Transport: make Play, Pause, Stop, Step and Record glyphs visible in every theme and every state, fixing the colour where it is defined (package or StageTrack transport QSS, per R3).\n2. Daylight chrome, in dannyfm-ui: no window or panel background lighter than #DADDDE (starting point; report the values chosen). Contrast against the background each element sits on: at least 4.5:1 for text, at least 3:1 for icons, glyphs, input borders and focus indicators (WCAG 2.x). Signal and Graphite unchanged. Add a test computing these contrast ratios for the relevant token pairs in all three themes; it must fail on the current Daylight tokens, and any assertion that already passes is labelled as a guard.\n3. Daylight 3D scene, in StageTrack's overlay: the viewport is dark in every theme. Daylight's scene tokens get a dark background and grid, with labels, frusta, walls and areas readable at the step-2 thresholds. Reusing Graphite's scene tokens for Daylight is acceptable. Extend the contrast test to scene token pairs; it must fail on the current Daylight scene tokens.\n4. Before tagging: run the package suite in its own venv (green). Install the package editable into a temporary venv (not StageTrack's) or otherwise render StageTrack against the candidate without changing StageTrack's pin, and save before/after PNGs of Daylight for Setup, Tune, Operate, Output Manager and Welcome to a folder outside the repo. Also confirm Signal and Graphite are pixel-identical before/after in those five views (write a minimal offscreen harness outside the repo if none exists).\nGATE: set a gate on the phase this work belongs to (add a phase \"Daylight y contraste del transporte\" if none fits), with the PNG folder path and the chosen colour values, and wait for Danny's visual approval. Do not tag or push before approval. If Danny asks for different values, adjust and regenerate the PNGs under the same gate.\n5. After approval: bump dannyfm-ui to 0.3.0, commit, annotated tag v0.3.0, push main and the tag. In StageTrack, bump the pin to the full commit hash of v0.3.0, reinstall non-editable, confirm dannyfm_ui resolves into site-packages. Full StageTrack suite with xdist (-n auto), under the resource rule: green (planner timing flake: if it is the only failure and passes alone, report it). Commit on hotareas. Run build.ps1 in full; report the installer path and timestamp. Do not run the installer. Do not push StageTrack.\n\nReport: the transport fix and where it lives; chosen Daylight chrome and scene values; contrast table for all three themes before and after; tests that failed on the old tokens and which are guards; tag and pinned hash; pixel-diff result; PNG folder; suite result; installer path; commit hashes.",
   "created_at": "2026-10-16T09:31:02+00:00",
   "from_project": "user",
   "id": "41e0bb70",
   "kind": "task",
   "status": "unread",
   "title": "2/5 Daylight: readable chrome, dark 3D viewport, visible transport (dannyfm-ui v0.3.0)",
   "to_project": "stagetrack"
  },
  {
   "body": "Start only after task \"1/5 Merge extract-ui-theme into hotareas\" is done. Work on branch hotareas in C:\\Users\\moyad\\Documents\\Visual Projects\\Tracking App.\n\nResource rule: before any full test suite run, claim the resource \"cpu:full-suite\" with claim_resource. If it is busy, do another part of this task and retry. Release it with release_resource when the suite finishes, including when it fails.\n\nThe docs contradict the code and each other. Resolve each point against the code and tests (the code is the source of truth unless it is clearly the thing that is wrong; in that case report it, do not change code in this task):\n- Hub item 859023a6: limitations say project format version 1 and that no real file was ever migrated; the code is at version 4 with the full v1→v4 chain tested. The schema doc says 3. The old spec gives a stale test count.\n- Hub item e0c9cae2: limitations and backlog say the default sensor grid covers only the larger arm of an L-shaped room; the spaces spec and a commit of the autonomous session say it is fixed and tested. Find the code and test that decide it.\n- Hub item 184ff7bf: the test-map header total does not match the sum of its sections. Recount from the actual suite (pytest --collect-only) and fix the map.\n- Hub item dad875c2: what remains open of phase F. Determine it from specs, backlog and commits, and list it.\n- Hub item 92b9214a: the backlog still lists things later commits say are resolved (presets, default grid, project migration, others). Mark each resolved entry with the commit that resolved it; leave genuinely open entries open.\n\nDo not stop for confirmation; state findings in the report. Docs only: no code changes. If you change no code, a full suite run is not needed; if you do run one, follow the resource rule.\n\nFor each hub item above: update it with update_item (close it with the evidence, or leave it open with what is still unknown). Commit on hotareas. Do not push.\n\nReport: per item, what was wrong, what the code shows (file and test), what changed in the docs, and the hub item's new status; the commit hash.",
   "created_at": "2026-10-16T09:31:11+00:00",
   "from_project": "user",
   "id": "706147f4",
   "kind": "task",
   "status": "unread",
   "title": "3/5 Reconcile docs and backlog with the code",
   "to_project": "stagetrack"
  },
  {
   "body": "Start only after task \"1/5 Merge extract-ui-theme into hotareas\" is done. Work on branch hotareas in C:\\Users\\moyad\\Documents\\Visual Projects\\Tracking App. StageTrack is a commercial closed-source Windows app shipped as a PyInstaller bundle with an Inno Setup installer (build.ps1). It has no THIRD-PARTY-NOTICES file. PySide6 / Qt are LGPLv3.\n\nResource rule: before any full test suite run, claim the resource \"cpu:full-suite\" with claim_resource. If it is busy, do another part of this task and retry. Release it with release_resource when the suite finishes, including when it fails.\n\nDo not stop for confirmation; state findings in the report. This task produces the notices file only. It does not choose StageTrack's own licence, add a LICENSE file, or change pyproject's licence field.\n\n1. Inventory everything that ends up in dist\\StageTrack: every Python distribution collected by PyInstaller (from the bundle and the runtime dependency tree, not dev/test dependencies), including dannyfm-ui, plus native libraries in _internal that do not belong to a Python distribution (Qt libraries, MSVC runtime, OpenSSL, ICU or others). For each: name, version, licence identifier, and the licence text or the upstream notice it requires.\n2. Write THIRD-PARTY-NOTICES.txt at the repo root: a summary table, then one section per component with its licence text. For PySide6/Qt include the full LGPLv3 text and the GPLv3 text it supplements, and a short statement of how a user can replace the Qt libraries (the bundle loads them as separate DLLs in _internal; say exactly where).\n3. Ship it: the file is copied into dist\\StageTrack and installed by the Inno Setup installer. The build smoke check must still pass.\n4. Add a test that fails on the current code: every runtime Python distribution in the bundle is listed in THIRD-PARTY-NOTICES.txt. Dev-only packages are excluded explicitly.\n5. Flag prominently in the report any component under GPL (not LGPL), AGPL, a non-commercial licence, or an unknown licence. Do not resolve them; Danny decides.\n6. Full suite with xdist (-n auto), under the resource rule: green (planner timing flake: if it is the only failure and passes alone, report it). Commit on hotareas. Run build.ps1 in full and confirm the file is in the installed layout (inspect dist and the Inno script; do not run the installer). Do not push.\n\nReport: component count, the flagged components, where the file lands in the bundle, the test and its failure on the old code, suite result, installer path, commit hash.",
   "created_at": "2026-10-16T09:31:21+00:00",
   "from_project": "user",
   "id": "11eaa50f",
   "kind": "task",
   "status": "unread",
   "title": "4/5 Generate THIRD-PARTY-NOTICES.txt and ship it in the bundle",
   "to_project": "stagetrack"
  },
  {
   "body": "Repo: C:\\Users\\moyad\\Documents\\Visual Projects\\Tracking App. Branch main has not changed since the base version; all later work lives on hotareas.\n\nGATE FIRST: do not start the merge. Set a gate on the phase \"Fusionar extract-ui-theme en hotareas y luego en main\" saying that hotareas is ready to merge into main, listing what hotareas contains beyond main at that moment (one line per phase or major change) and the state of tasks 1/5 to 4/5. Wait for Danny's approval. Start only after he approves, and only after tasks 1/5 to 4/5 are done or Danny says otherwise.\n\nResource rule: before any full test suite run, claim the resource \"cpu:full-suite\" with claim_resource. If it is busy, do something else and retry. Release it with release_resource when the suite finishes, including when it fails.\n\nAfter approval:\n1. Both working trees clean; report the HEADs of main and hotareas.\n2. Merge hotareas into main (fast-forward if possible). If there are conflicts, describe them under the same gate and stop.\n3. Full suite with xdist (-n auto), under the resource rule: green (planner timing flake: if it is the only failure and passes alone, report it). Then run the suite serially as well, since this is a release point.\n4. Run build.ps1 in full; report the installer path and timestamp. Do not run the installer.\n5. Do not push. Do not delete hotareas.\n\nReport: HEADs before and after, suite results (xdist and serial), installer path, and the phase status updated in the hub.",
   "created_at": "2026-10-16T09:31:44+00:00",
   "from_project": "user",
   "id": "5de4fba4",
   "kind": "task",
   "status": "unread",
   "title": "5/5 Merge hotareas into main (gated: wait for Danny)",
   "to_project": "stagetrack"
  },
  {
   "body": "From Danny's project-hub chat, approved by Danny. Feedback on the redesign C implementation in progress (phase 2362a0a7); include it in this phase.\n\nProblem: in the new overview Danny has to scroll to find what needs his action. Gates (actions) are mixed with unread reports (information): project-hub alone shows 5 cards, 4 of them old reports, and StageTrack's gates are below the fold. The old UI listed what needed his action at the very top.\n\nChanges:\n1. Notifications button in the top bar, always visible on every view: a bell with the count of things that need Danny's action across all projects (waiting gates of both types, plus messages addressed to \"user\"). Highlighted (amber) when the count is above zero, neutral when zero. Clicking it opens a panel listing them, grouped by project, most urgent first, each with its action button (Aprobar, Marcar como hecha, open the project) using the confirmation dialog already specified.\n2. Overview: an \"Action needed\" strip at the very top, above the project blocks, with the same list (gates only and messages to \"user\"). Hidden when empty.\n3. Unread reports are information, not actions: they do not count in the bell. In each project block, show them as one collapsed line (\"8 reports sin leer · ver\") that expands in place, plus a \"Marcar todos como leídos\" action for that project. The top-bar unread counter stays separate from the bell.\n4. Keep the click checks passing and add checks for the bell count, the panel actions and \"Marcar todos como leídos\".",
   "created_at": "2026-10-16T09:32:15+00:00",
   "from_project": "user",
   "id": "1a39e30b",
   "kind": "task",
   "status": "done",
   "title": "Rediseño C: centro de notificaciones con lo que requiere acción de Danny",
   "to_project": "project-hub"
  },
  {
   "body": "Estado: extract-ui-theme en 8bf56f1, hotareas en c44751a sin commits nuevos, así que la fusión sería un avance rápido limpio (+9).\nParada en el paso 1: el árbol no está limpio.\n- Test Projects/First_Stage_test/first_stage_test.yaml modificado (+264/-10, sin commit).\n- .claude/loop.md sin seguimiento.\nNo toqué nada. Danny: haz commit, stash o descarta el yaml (y decide si loop.md va al repo o a .gitignore), o di que se puede ignorar. Con eso retomo 1/5. Las tareas 2/5 a 4/5 esperan a la 1/5. La 5/5 sigue con su puerta.",
   "created_at": "2026-10-16T09:32:40+00:00",
   "from_project": "stagetrack",
   "id": "60963ed3",
   "kind": "report",
   "status": "unread",
   "title": "1/5 parada: el árbol de trabajo no está limpio",
   "to_project": "stagetrack"
  },
  {
   "body": "From Danny's project-hub chat, approved by Danny. Danny stopped the session that was implementing proposal C. Change of direction:\n\n0. Save the C work in progress on a branch \"redesign-c\" (commit there, push it) so it stays as reference, and return main to its last pushed state. Do not lose the C code.\n1. Tasks 26006a44 (implement C), ae400381 (gate buttons with confirmation) and 1a39e30b (notification bell) are superseded by this one: their requirements move into D. Mark them done with a one-line note pointing here. Task 89d0b4d6 (activity log and \"Resumen\" button) now starts after phase e8a10b56 \"Rediseño D: implementación\" is done.\n2. Phase 2362a0a7 is now \"Rediseño: mockup D (mezcla con ADN dannyfm-ui)\". Do only that phase: a static HTML mockup, no dashboard code changes. Phase e8a10b56 \"Rediseño D: implementación\" already has a review gate for Danny's approval.\n\nProposal D:\n- Information layout from the previous Console design B (mockups/option-B-*.png and the implemented version before C): dense, tables, everything important visible without scrolling. Danny liked how information was organised there; it needed refining.\n- Keep from C what worked: the one-sentence summary at the top, done phases collapsed, item types written as words, and phase notes that never overflow.\n- Reading rule, everywhere (overview and project view): at the top only what needs Danny's action (waiting gates with their Aprobar / Marcar como hecha buttons and confirmation naming project and phase; messages addressed to \"user\"). Unread reports are information: one collapsed line per project (\"N reports sin leer · ver\") that expands in place, with \"Marcar todos como leídos\". Everything else below. Danny must always know what to read and what to act on.\n- Notifications bell in the top bar on every view, counting only what needs Danny's action, amber when above zero, opening a panel grouped by project with the action buttons.\n- Visual identity from Danny's own package dannyfm-ui (local repo C:\\Users\\moyad\\Documents\\Visual Projects\\dannyfm-ui, GitHub DannyFM-Artist/dannyfm-ui, use the pinned v0.2.0 tag): take its colour tokens, font family and sizes, spacing and component look (buttons, badges, panels, glyphs if usable on the web) and map them to CSS variables, so the hub looks like part of the same family as StageTrack and FrameMorph. Read only; do not modify dannyfm-ui. If the font is not available to a browser, say which fallback you used.\n\nDeliver mockups/redesign-D.html with PNG screenshots of the overview, the framemorph and stagetrack project views and a stress case (20 phases, 30 items), rendered with a copy of the real hub data, plus a short list of which dannyfm-ui tokens you used. Mark phase 2362a0a7 done, post a report, mark this task done and stop at the review gate of phase e8a10b56.",
   "created_at": "2026-10-16T09:35:46+00:00",
   "from_project": "user",
   "id": "4df34cb3",
   "kind": "task",
   "status": "read",
   "title": "Rediseño: parar la C y hacer el mockup D (mezcla con el ADN de dannyfm-ui)",
   "to_project": "project-hub"
  },
  {
   "body": "+ Implementar C, botones de gates y campana: cerradas, sustituidas por la tarea del mockup D (4df34cb3); sus requisitos pasan a D.\n+ Código de la C a medias en la rama redesign-c, subida a origin.",
   "created_at": "2026-10-16T09:39:39+00:00",
   "from_project": "project-hub",
   "id": "6374cbd7",
   "kind": "report",
   "status": "unread",
   "title": "Tareas de la C sustituidas por el mockup D",
   "to_project": "project-hub"
  }
 ],
 "leases": [
  {
   "acquired_at": "2026-10-16T09:39:50+00:00",
   "expires_at": "2026-10-16T10:39:50+00:00",
   "project_id": "project-hub",
   "purpose": "Leer tokens v0.2.0 para el mockup D (solo lectura)",
   "resource": "repo:dannyfm-ui"
  },
  {
   "acquired_at": "2026-10-16T09:39:15+00:00",
   "expires_at": "2026-10-16T11:09:15+00:00",
   "project_id": "project-hub",
   "purpose": "Rediseño: parar la C y hacer el mockup D",
   "resource": "task:4df34cb3"
  },
  {
   "acquired_at": "2026-10-16T09:10:36+00:00",
   "expires_at": "2026-10-16T11:10:36+00:00",
   "project_id": "framemorph",
   "purpose": "Limpieza 0.3.x y cierre de pendientes",
   "resource": "task:68b1f156"
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
