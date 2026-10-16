## project-hub
This repo's project id in project-hub is `project-hub`.
- Update this project in project-hub as you go, not only at the end: after each completed phase or significant step, update phase status, items, decisions and next_step right away.
- Mark an inbox message "done" only when the work it asks for is actually finished; "read" means seen, not done.
- At the end of the session, post a report message summarizing what changed.
- Before using a shared resource (GPU-heavy runs, physical sensors, shared repos such as dannyfm-ui, files outside this repo), claim it in project-hub with claim_resource; release it as soon as you are done. If it is busy, do not use it: work on something else and retry later. Tests must bind to free ports chosen by the OS, never to fixed ports.
- Keep hub text short and readable at a glance: no commit hashes, file:line citations or logs in descriptions, notes or titles; details belong in the repo.
- Before starting a phase, check its gate in project-hub. If it waits for Danny, do not start it: post a report message saying what he must do, and stop.
- If the next phase needs Danny (a review, real hardware, a decision, an action only he can do), add a gate with set_gate and a reason that says exactly what he must do.
- Never resolve gates.
