"""Render the project-hub app icons (PNG) and mockups/icon-preview.png from the SVG sources.

Sources in project_hub/static/icons/: favicon.svg (simplified, for 16 and 32 px) and icon.svg
(detailed, for 48 px and up). Edit those, then run with any Python that has Playwright (not a
package dependency) on a machine with Google Chrome installed:

    python tools/make_icons.py
"""

import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "project_hub" / "static" / "icons"
FAV, ICON = ICONS / "favicon.svg", ICONS / "icon.svg"
BASE = "#131313"

# (file, source, size, art scale). Scale None keeps the rounded tile with transparent corners;
# a number puts the art on a full-bleed BASE square at that scale.
TARGETS = [
    ("icon-16.png", FAV, 16, None),
    ("icon-32.png", FAV, 32, None),
    ("icon-48.png", ICON, 48, None),
    ("icon-192.png", ICON, 192, None),
    ("icon-512.png", ICON, 512, None),
    ("apple-touch-icon.png", ICON, 180, 0.86),  # iOS rounds the corners itself
    ("icon-512-maskable.png", ICON, 512, 0.72),  # brain stays inside the 80% safe circle
]


def data_url(path: Path) -> str:
    mime = "image/svg+xml" if path.suffix == ".svg" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def render(page, html: str, out: Path):
    page.set_content(f'<body style="margin:0;background:transparent">{html}</body>')
    page.locator("#shot").screenshot(path=str(out), omit_background=True)


def preview_html() -> str:
    png = {n: data_url(ICONS / n) for n in ("icon-16.png", "icon-32.png", "icon-512.png")}

    def tab(strip, bg, fg):
        return (f'<div style="background:{strip};padding:8px 8px 0;width:260px">'
                f'<div style="background:{bg};color:{fg};border-radius:8px 8px 0 0;height:34px;display:flex;'
                f'align-items:center;gap:8px;padding:0 12px;font:12px Segoe UI,sans-serif">'
                f'<img src="{png["icon-16.png"]}" width="16" height="16">project-hub'
                f'<span style="margin-left:auto;opacity:.6">&#x2715;</span></div></div>')

    label = 'style="color:#E5E2E1;font:12px Consolas,monospace;margin-top:8px"'
    cell = 'style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end"'
    return f"""<div id="shot" style="background:#181818;padding:32px;display:flex;gap:40px;align-items:flex-end">
      <div {cell}><img src="{png['icon-16.png']}" width="16" height="16"><div {label}>16</div></div>
      <div {cell}><img src="{png['icon-32.png']}" width="32" height="32"><div {label}>32</div></div>
      <div {cell}><img src="{png['icon-512.png']}" width="512" height="512"><div {label}>512</div></div>
      <div style="display:flex;flex-direction:column;gap:24px">
        {tab('#202124', '#35363a', '#E8EAED')}
        {tab('#dee1e6', '#ffffff', '#202124')}
        <div {cell}><div style="display:flex;gap:24px;align-items:flex-end">
          <img src="{png['icon-16.png']}" width="128" height="128" style="image-rendering:pixelated">
          <img src="{png['icon-32.png']}" width="128" height="128" style="image-rendering:pixelated"></div>
          <div {label}>16 and 32 px PNGs, zoomed</div></div>
      </div></div>"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")  # installed Google Chrome, no browser download
        page = browser.new_page(device_scale_factor=1, viewport={"width": 1200, "height": 800})
        for name, src, size, scale in TARGETS:
            art = size if scale is None else size * scale
            bg = "transparent" if scale is None else BASE
            render(page, f'<div id="shot" style="width:{size}px;height:{size}px;background:{bg};display:grid;'
                         f'place-items:center"><img src="{data_url(src)}" style="width:{art}px;height:{art}px">'
                         f'</div>', ICONS / name)
        render(page, preview_html(), ROOT / "mockups" / "icon-preview.png")
    for name, _, size, _ in TARGETS:  # self-check: every PNG exists at its size
        assert (ICONS / name).read_bytes()[16:24] == size.to_bytes(4, "big") * 2, name


if __name__ == "__main__":
    main()
