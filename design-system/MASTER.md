# project-hub design system — "Console"

Source of truth for every project-hub screen. Approved by Danny on 2026-10-16 (mockup option B, `mockups/option-B.html`).
New screens reuse these tokens and patterns; a new visual pattern starts as a mockup Danny approves.

## Character

Dark terminal tool. Monospace everywhere, flat, no rounded corners, no shadows, no gradients.
Structure comes from 1px lines and boxed panes, not from cards or elevation. Amber is the single accent; the other colours carry meaning only (status, type).

## Colour tokens

| Token | Value | Use | Contrast on `--bg` |
|---|---|---|---|
| `--bg` | `#0E1013` | page and pane background | — |
| `--p` | `#13161B` | bars (tab bar, shortcut bar), row hover, report blocks | — |
| `--p2` | `#1A1E25` | raised surface (inputs, popovers) | — |
| `--line` | `#2A2F38` | pane borders, table rules | — |
| `--line2` | `#3A404B` | stronger dividers, hover borders | — |
| `--text` | `#D7DBE2` | primary text | 13.7:1 |
| `--dim` | `#A0A8B5` | secondary text, inactive tabs, read messages | 8.0:1 (7.0 on `--p2`) |
| `--faint` | `#7A8190` | meta text: ids, timestamps, column headers, legend | 4.9:1 on `--bg` (4.3 on `--p2`: keep faint text off `--p2`) |

The mockup's original `#7D8593` / `#555C69` greys were raised in the implementation because `#555C69` was 2.8:1.
| `--amber` | `#FFB547` | the accent: active tab, focus ring, current phase, unread, pane titles, primary actions | 10.8:1 |
| `--green` | `#8BD47C` | status active, phase done, "ok" lines | 10.7:1 |
| `--violet` | `#C29BFF` | status parked, type future_request, kind task | 8.6:1 |
| `--blue` | `#7AB6FF` | status done | 9.0:1 |
| `--cyan` | `#6CD3E8` | type idea, kind message | 11.0:1 |
| `--red` | `#FF7A7A` | type bug, errors, "no" lines | 7.6:1 |

Text on an amber fill uses `--bg` (10.8:1).

Meaning map (always paired with a text label, never colour alone):
- Project status: active `--green`, paused `--amber`, parked `--violet`, done `--blue`, shown as `● active`.
- Item type: bug `B` `--red`, idea `I` `--cyan`, future_request `F` `--violet`.
- Message kind: message `--cyan`, task `--violet` with a `[ ]` prefix, report = framed block with amber left border and an amber label.
- Phase: done `--green`, in_progress amber fill tint + amber border + 3px amber underline, todo `--dim`.

## Typography

- One family: `"Cascadia Mono","Cascadia Code",Consolas,"SF Mono",Menlo,ui-monospace,monospace`. System fonts only; the page runs offline.
- Base 13px / 1.55. Small meta 11.5–12px (only in `--dim` or brighter). Project title 22px bold. Column headers 11.5px uppercase, letter-spacing .06em.
- Weights: 400 body, 700 for names, titles, unread messages. No italics.
- Numbers are tabular by nature (monospace); keep fractions as `n/m`.

## Spacing and layout

- 4px rhythm; common steps 6, 8, 10, 14, 22, 24.
- Page padding 22px top, 24px sides. Gap between panes 22px.
- Fixed top tab bar (34px) and bottom shortcut bar; content scrolls between them.
- Project view: phase strip full width, then a 2fr / 1fr grid (kanban | decisions + inbox). Collapses to one column on narrow windows; tables scroll inside their pane, never the page.

## Patterns

- **Pane**: 1px `--line` box; title sits on the top border in amber (`--bg` background behind it), optional dim count next to it, optional right-side controls on the border.
- **Toggle / filter**: plain words; the active one is wrapped in amber brackets `[all]`.
- **Progress**: block bar (`█` cells) in the status colour, in-progress cell at ~55% mix, empty cells `#262B33`, then `n/m` in `--dim`.
- **Unread badge**: amber fill, `--bg` bold text, no radius.
- **Kanban line**: type letter column + title; id below in meta text; hover/selected = `--p` background + 2px amber left border.
- **Decision log**: date column, decision in `--text`, reason on the next line prefixed `└ because`.
- **Command input**: 1px `--line` box with an amber prompt glyph; transparent input.
- **Keys**: `<kbd>` with `--dim` fill and `--bg` text; every shortcut also has a mouse path.
- **Prompt line**: `user@hub ~ $ command` with a blinking amber caret (animation off under `prefers-reduced-motion`).

## Interaction and accessibility rules

- Focus: `:focus-visible` 1px amber outline, offset 1px. Never remove it without a replacement.
- Interactive elements are real `button` / `a` / `input` / `select`; letter-only controls carry `aria-label`.
- API errors and confirmations go to an `aria-live="polite"` line in the console style; form errors sit next to the form.
- Motion: only the caret blink and ≤200ms colour/opacity transitions; none under reduced motion.
- Read messages switch to `--dim` text (no opacity fades for state).
