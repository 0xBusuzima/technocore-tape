#!/usr/bin/env python3
"""Render the tape exactly as the page does, so the layout can be judged at
full size instead of through a preview pane."""
import io, json, math, os, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 2320, 920

def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

BG, FLOOR, CYAN, SEP = rgb("0C1430"), rgb("2E3852"), rgb("00B4D8"), rgb("1A2340")


ROWS = 40          # shared sentences that get a row of their own
ROW_TOP = 30


def layout(lines):
    """Rows for the sentences many keys share, one band for everything else.

    Spacing widens toward the top: the heaviest lines carry a mark roughly every
    second and would otherwise fuse into a block, which is exactly the row a
    reader most needs to see as one sentence.
    """
    shared = [i for i, l in enumerate(lines) if l["keys"] > 1][:ROWS]
    rows, y = {}, ROW_TOP
    for n, r in enumerate(shared):
        rows[r] = y
        y += 17.5 - 9.0 * (n / max(len(shared) - 1, 1))   # 17.5px down to 8.5px
    return rows, y + 40


def render(tape, out):
    lines, marks = tape["lines"], tape["marks"]
    rows, band_top = layout(lines)
    widest = max(tape["widest"], 10)
    span = tape["span_seconds"] or 1

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")

    # faint guide for every row, so the eye reads rows before it reads marks
    for r, y in rows.items():
        d.line([(0, y + 2), (W, y + 2)], fill=(35, 42, 62, 120), width=1)
    d.line([(0, band_top - 22), (W, band_top - 22)], fill=SEP + (255,), width=2)

    for t, rank, _ in marks:
        l = lines[rank]
        x = (t / span) * (W - 10) + 5
        if rank in rows:
            y = rows[rank]
            k = min(1.0, math.log10(l["keys"]) / math.log10(widest))
            d.rectangle([x, y, x + 3, y + 4], fill=CYAN + (int((0.45 + k * 0.55) * 255),))
        else:
            h = (rank * 2654435761 + int(t * 1000) * 40503) & 0xFFFF
            y = band_top + (h / 65535.0) * (H - band_top - 8)
            solo = l["keys"] <= 1
            col = FLOOR if solo else (0, 120, 150)
            d.rectangle([x, y, x + 2, y + 2], fill=col + (200 if solo else 230,))

    img.save(out)
    print(f"  {out}  ({os.path.getsize(out):,} bytes)")
    print(f"  rows drawn: {len(rows)}  | band holds {len(lines)-len(rows)} sentences")


if __name__ == "__main__":
    tape = json.load(io.open(os.path.join(HERE, "data", "tape.json"), encoding="utf-8"))
    render(tape, os.path.join(HERE, "preview.png"))
