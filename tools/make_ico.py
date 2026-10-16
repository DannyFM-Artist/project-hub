"""Build project_hub/static/icons/app.ico (16/32/48/256) from the brain PNGs. Needs Pillow only."""
from pathlib import Path

from PIL import Image

ICONS = Path(__file__).resolve().parent.parent / "project_hub" / "static" / "icons"
# 256 is downscaled from the 512 PNG; the smaller sizes use the hand-tuned PNGs.
SRC = {16: "icon-16.png", 32: "icon-32.png", 48: "icon-48.png", 256: "icon-512.png"}
imgs = {n: Image.open(ICONS / f).convert("RGBA").resize((n, n), Image.LANCZOS) for n, f in SRC.items()}
imgs[256].save(ICONS / "app.ico", sizes=[(n, n) for n in SRC], append_images=[imgs[n] for n in (16, 32, 48)])
