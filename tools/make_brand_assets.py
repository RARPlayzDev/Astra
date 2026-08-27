"""Generate the ASTRA brand assets: logo SVG (website) and icon ICO (exe/installer).

The mark: a dark disc (the spectrum), a sweeping beam wedge (the adaptive scan),
and three blips (intercepts). Deliberately simple so it reads at 16 px.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

NAVY = (16, 26, 43, 255)
STEEL = (79, 124, 168, 255)
LIGHT = (214, 230, 244, 255)
AMBER = (207, 164, 83, 255)


def draw_mark(size: int) -> Image.Image:
    s = size
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = s * 0.06                                   # margin

    # rounded-square background
    r = s * 0.22
    d.rounded_rectangle([m, m, s - m, s - m], radius=r, fill=NAVY)

    cx = cy = s / 2
    R = s * 0.34

    # concentric range rings
    for frac, w in ((1.0, max(1, int(s * 0.028))),
                    (0.66, max(1, int(s * 0.02)))):
        rr = R * frac
        bbox = [cx - rr, cy - rr, cx + rr, cy + rr]
        d.ellipse(bbox, outline=STEEL, width=w)

    # cross hairs
    lw = max(1, int(s * 0.018))
    d.line([cx - R, cy, cx + R, cy], fill=(79, 124, 168, 110), width=lw)
    d.line([cx, cy - R, cx, cy + R], fill=(79, 124, 168, 110), width=lw)

    # sweep wedge (adaptive scan): 55-degree sector from centre
    import math
    a0, a1 = -108, -53
    d.pieslice([cx - R, cy - R, cx + R, cy + R], start=a0, end=a1,
               fill=(111, 158, 199, 70))
    edge = math.radians(a1)
    d.line([cx, cy, cx + R * math.cos(edge), cy + R * math.sin(edge)],
           fill=LIGHT, width=max(2, int(s * 0.03)))

    # intercept blips
    blip = max(2, int(s * 0.055))
    for fx, fy, col in ((0.52, -0.52, AMBER), (-0.45, 0.30, LIGHT),
                        (0.18, 0.62, AMBER)):
        bx, by = cx + R * fx, cy + R * fy
        d.ellipse([bx - blip / 2, by - blip / 2, bx + blip / 2, by + blip / 2],
                  fill=col)
    return img


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#16273f"/><stop offset="1" stop-color="#0e1826"/>
    </linearGradient>
    <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#6f9ec7" stop-opacity=".05"/>
      <stop offset="1" stop-color="#9cc3e4" stop-opacity=".38"/>
    </linearGradient>
  </defs>
  <rect x="12" y="12" width="232" height="232" rx="56" fill="url(#bg)"
        stroke="#2b415c" stroke-width="3"/>
  <g transform="translate(128 128)">
    <circle r="86" fill="none" stroke="#4f7ca8" stroke-width="7" opacity=".85"/>
    <circle r="57" fill="none" stroke="#4f7ca8" stroke-width="5" opacity=".55"/>
    <line x1="-86" y1="0" x2="86" y2="0" stroke="#4f7ca8" stroke-width="3" opacity=".4"/>
    <line x1="0" y1="-86" x2="0" y2="86" stroke="#4f7ca8" stroke-width="3" opacity=".4"/>
    <path d="M 0 0 L 86 0 A 86 86 0 0 0 50.5 -69.7 Z" fill="url(#sweep)" opacity=".9"/>
    <line x1="0" y1="0" x2="86" y2="0" stroke="#d6e6f4" stroke-width="8" stroke-linecap="round"/>
    <circle cx="45" cy="-45" r="11" fill="#cfa453"/>
    <circle cx="-39" cy="26" r="9" fill="#d6e6f4" opacity=".9"/>
    <circle cx="15" cy="54" r="9" fill="#cfa453" opacity=".85"/>
  </g>
</svg>
"""


def main() -> None:
    (ASSETS / "astra_logo.svg").write_text(SVG, encoding="utf-8")

    master = draw_mark(512)
    master.save(ASSETS / "astra_mark_512.png")

    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48),
                 (64, 64), (128, 128), (256, 256)]
    master.save(ASSETS / "astra.ico", sizes=ico_sizes)

    print(f"assets written to {ASSETS}")


if __name__ == "__main__":
    main()
