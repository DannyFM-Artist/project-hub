# project-hub design system — "D" (Signal)

Source of truth for every project-hub screen. Design D replaced the Console look on 2026-10-16 by Danny's choice
(mockup `mockups/redesign-D.html`, screenshots `mockups/redesign-D-*.png`; implementation shots `mockups/impl-D-*.png`).
D is the Console B information layout with the C reading refinements, in the dannyfm-ui v0.2.0 "signal" identity.
D2 (2026-10-16, after Danny validated D with real data; shots `mockups/impl-D2-*.png`): every piece of information in one place only,
and whatever is not for right now is folded. Overview projects are cards, blocks stand further apart.
New screens reuse these tokens and patterns; a new visual pattern starts as a mockup Danny approves.

## Character

Dark desktop-tool surfaces (dannyfm-ui dock panels), flat, 2 px radius, no gradients. Structure comes from panels with a
header strip, column headers and 1 px dividers. Green (`--ACCENT`) marks "current / selected"; red (`--WAITING`) marks "stopped, waits for Danny";
amber (`--WARN`) marks "an agent is working"; every other colour carries a meaning and always sits next to a word.

## Tokens (CSS variables, named after the dannyfm-ui tokens)

| Token | Value | Use |
|---|---|---|
| `--BASE` | `#131313` | page background, `theme-color` |
| `--SURFACE` | `#181818` | every block (panels, cards, the project header), title bar |
| `--RAISED` | `#1F1F1F` | row hover, forms |
| `--OVERLAY` | `#262626` | bell panel, toasts, pressed buttons |
| `--INPUT` | `#0E0E0E` | inputs, selects, report bodies, inline confirmations |
| `--BORDER` / `--BORDER_STRONG` / `--DIVIDER` | `#2A2A2A` / `#444748` / `#1F1F1F` | panel borders / button outlines, "Para ti" border / row dividers |
| `--TEXT` / `--TEXT_DIM` / `--TEXT_MUTED` | `#E5E2E1` / `#A8ABAB` / `#8E9192` | primary / secondary / meta (headers, ages, ids) |
| `--TEXT_ON_ACCENT` | `#0C2000` | text on the filled confirm button |
| `--ACCENT` (+ `_HOVER`, `_PRESSED`, `_SOFT`) | `#88FE00` | active tab, current phase, selection edge, focus, the confirm button |
| `--OK` | `#3FC78B` | done, state ready |
| `--WARN` | `#EA7F2A` | state working, the hot bell, the offline banner |
| `--ERROR` | `#FF2E4D` | errors, type bug |
| `--IDLE` | `#6C7173` | state quiet |
| `--SELECTED` (hub) | `#213012` | selected-row tint: blend(ACCENT_SOFT, SURFACE, .5), keeps WARN and TEXT_DIM ≥ 4.5:1 |
| `--WAITING` (hub) | `#FF5C72` | state "waiting" and gates that wait for Danny: a red that keeps 4.5:1 on SURFACE and on SELECTED (`--ERROR` is 3.8:1 on SELECTED) |
| `--TYPE_IDEA` / `--TYPE_REQUEST` (hub) | `#6CC4DC` / `#B7A1F2` | item types idea / petición (bug uses `--ERROR`) |

Hub-only tokens live in the app (dannyfm-ui rule R3).

## Type and spacing

- `--scale: 1.1667` (dannyfm-ui's opt-in 7/6 interface scale: 12 px body becomes 14 px in a browser). Every size and space is `calc(n px * var(--scale))`.
- One sans font for content: `"Segoe UI", Inter, system-ui, sans-serif`, state words included. Mono (`"Cascadia Mono", Consolas, "JetBrains Mono", ui-monospace, monospace`) only for numbers, ids, timestamps and paths. The bell panel and Resumen keep their mono state words.
- Sizes: H1 19 (project name), H2 15 (card project name), H3 12, BODY 12, SMALL 11, CAPTION 10 (all × scale). Weights 400 and 600 only.
- Panel titles and column headers: uppercase, letter-spaced; panel titles H3 600 `--TEXT` (one step above the old SMALL), column headers CAPTION `--TEXT_MUTED`.
- Space steps XXS 2, XS 4, SM 8, MD 12, LG 16, XL 24, XXL 32 (× scale). Page padding LG / XL; blocks XL apart (grid columns too), cards LG apart; max width 1680.
- Text contrast 4.5:1 or better on SURFACE, RAISED and SELECTED (muted text turns TEXT_DIM on a selected row or card).

## Layout

- **Title bar** (sticky, every view): wordmark · tabs `Proyectos` (key 1), one tab per project with its amber action count (key 2 = last project), `Resumen` (key 3) · reports counter · bell · poll time. An offline banner (WARN) sits under it when the hub cannot be reached.
- **Proyectos (overview)**: the date line, "Para ti", one card per project (filter tabs by lifecycle status, with their counts), then folded at the bottom: "Reports sin leer · N" (one line per project inside) and "Recursos en uso · N". No summary sentence: "Para ti" already says what waits.
- **Project**: a header block of two lines: (1) name and state, "Detalles ›", "← Proyectos"; (2) phase track, done/total, current phase and its state word, next step. "Detalles" (folded by default) holds lifecycle, id, repo path, description and last update. "Para ti" only when something waits. Then phases | items (7/5), and below, folded with their counts, Decisiones | Bandeja; the Bandeja holds the unread-reports line first, then the messages and the "Publicar mensaje" form. The autonomy line is not shown in the dashboard (it stays in the MCP output). One column under 1100 px. No page h-scroll down to 800 px.
- **Folds** open from their title (chevron + title + count) and survive polling. A project opens with Detalles, Decisiones and Bandeja folded; `m` opens the Bandeja with its form; the route `#p/<id>/m/<message id>` opens the Bandeja (and the reports line) and scrolls to that message.
- **Resumen**: period tabs, one folded box per project with news since its last copy, the rest in one "Sin novedades: A, B" line.

## The reading rule

Danny takes every decision by talking to each project's Claude Desktop chat; the dashboard only informs.
Information is split by what it asks of him:
- **Waits for Danny** ("Para ti", the bell): phases whose gate waits (`gate_state: waiting`) and open messages to "user". Each line says "Resuélvelo en el chat de <project>" and links to the project; there are no action buttons. Only these count in the bell; it is amber above zero and neutral at zero.
- **Information**: unread reports, one collapsed line per project ("N reports sin leer · ver"), expanding in place, with "Marcar todos como leídos". They never count in the bell.
- Lists are ordered most urgent first: projects in state "waiting", then by what waits, then unread reports, then the server order.

## Project state

One state per project (`state: {kind, label, detail}` from the server), the same everywhere: overview rows, project header, Resumen boxes and bell groups. Highest first:
1. **waiting**, `--WAITING` red: "Te espera: <motivo>". The agent is stopped because it needs Danny.
2. **working**, `--WARN` amber: "Trabajando en: <tarea>".
3. **ready**, `--OK` green: "Novedades para copiar".
4. **quiet**, `--IDLE` grey: "Sin novedades".

On overview cards and in the project header the state is the dot and the label. The waiting reason shows only when "Para ti" does not already list that project's waits; otherwise the red label is enough. The full detail is always in the tooltip; Resumen and the bell keep the detail visible. A stopped project shows grey "Parado" with its "ver report «Parado»" link. Red cards sort first.

## Patterns

- **Panel**: SURFACE box over BASE, header strip (uppercase title · count, muted meta, right-side tabs), column header row, rows. A folded panel shows only its header strip.
- **Project card**: SURFACE, 2 px left edge, shows only: state (dot + label), name (H2) with count badges ("N reports", "N ítems"; zero is not shown), phase track + done/total + current phase and state word, next step (3 lines, full text in the tooltip). Clicking anywhere on it opens the project; ↑↓ select (SELECTED tint + ACCENT edge), Enter opens.
- **Badge**: small BORDER_STRONG outline, mono number + word, TEXT_DIM.
- **Row**: grid, 1 px divider, hover RAISED. **Selected row**: `--SELECTED` tint + 2 px `--ACCENT` left border. The border is the row's own left edge, outside its padding, so the marker never overlaps the first cell (checked in `gates_check.py`). The same treatment is used in the overview, phases, items and inbox; a selected row shows its detail (notes, actions) in place.
- **State word**: mono uppercase coloured word, no box (`EN CURSO`, `ESPERA A DANNY`, `bug`, `petición`).
- **Phase track**: one 7×11 cell per phase: OK done, WAITING gate waiting, ACCENT current, BORDER_STRONG to do; then `n/m`.
- **Buttons**: outline; `primary` = stronger outline + 600; `filled` (ACCENT) only for the "Sí, …" of a confirmation; `ghost` for secondary; `small` keeps a 24 px target.
- **Tabs / filters**: words with a mono count; the active one has an ACCENT underline.
- **Done phases** fold into one "✓ N fases hechas · ver" line above the current phase.
- **Resumen box**: folded line = chevron, name, phase, counts (waiting gates highlighted), copy state ("copiado hace X" / "N novedades desde la última copia"), the project state badge (dot + label + one-line detail) and the copy button ("Copiar igualmente" while working). Nothing new: "Nada nuevo desde la última copia", disabled. Polling only updates badges and button texts in place.
- **Inline confirmation** (INPUT background, BORDER_STRONG), naming what it acts on, "Sí, …" filled and "Cancelar" ghost; Cancel changes nothing. Used for force-releasing a resource. Never `alert` / `confirm` / `prompt`.
- **Toasts**: the `aria-live` line, OVERLAY with an OK (or ERROR) left edge.

## Gates (read-only)

- One gate type. A waiting gate shows just the "espera a Danny" tag in its phase row (the reason is in "Para ti", and in the tag's tooltip). A resolved gate shows "Resuelto vía chat: «<words>»", shortened, in the gate column only, with the full words and the time in a tooltip; the selected row does not repeat it.
- There are no gate buttons, gate editors or confirmations, and a phase whose gate waits has no status control: Danny decides in the project's chat.

## Interaction and accessibility

- Every shortcut has a mouse path: 1/2/3 tabs; ↑↓ select (overview rows / items), Enter open; a "Añadir ítem"; m "Publicar mensaje"; ←→ item move buttons; r/d message buttons; x "+cerrados"; space the status selector (not on a phase whose gate waits). Shortcuts are ignored while typing.
- Polling (5 s) never loses focus, typed text, open confirmations, expansions or selection.
- Focus: `:focus-visible` 1 px ACCENT outline (buttons: ACCENT border + ring). Real `button` / `a` / `select`; icon-only controls carry `aria-label`.
- Motion: only the 120 ms chevron turn, off under reduced motion.
