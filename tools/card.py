#!/usr/bin/env python3
"""Render a 1600x900 card of the tape, for posting where a link preview is not
enough. Same geometry as the page, drawn at print scale so the lines stay sharp.

    python tools/card.py
"""
import io, json, math, os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.path.dirname(HERE), "technocore-logo", "SpaceMono-Bold.ttf")
W, H, SS = 1600, 900, 2

BASE, PANEL, CYAN, ICE, DIM, FLOOR = (
    (10, 17, 40), (12, 20, 48), (0, 180, 216),
    (245, 247, 250), (161, 167, 174), (46, 56, 82))

ROWS, ROW_TOP = 40, 22


def font(px):
    return ImageFont.truetype(FONT, px)


def tape_layer(tape, w, h):
    lines, marks = tape["lines"], tape["marks"]
    shared = [i for i, l in enumerate(lines) if l["keys"] > 1][:ROWS]
    rows, y = {}, ROW_TOP * SS
    for n, r in enumerate(shared):
        rows[r] = y
        y += (14.0 - 7.0 * (n / max(len(shared) - 1, 1))) * SS
    band_top = y + 30 * SS

    img = Image.new("RGBA", (w * SS, h * SS), PANEL + (255,))
    d = ImageDraw.Draw(img, "RGBA")
    for r, ry in rows.items():
        d.line([(0, ry + 2), (w * SS, ry + 2)], fill=(35, 42, 62, 130), width=1)
    d.line([(0, band_top - 16 * SS), (w * SS, band_top - 16 * SS)],
           fill=(26, 35, 64, 255), width=2)

    widest = max(tape["widest"], 10)
    span = tape["span_seconds"] or 1
    for t, rank, _ in marks:
        l = lines[rank]
        x = (t / span) * (w * SS - 12) + 6
        if rank in rows:
            k = min(1.0, math.log10(l["keys"]) / math.log10(widest))
            d.rectangle([x, rows[rank], x + 3 * SS, rows[rank] + 3.5 * SS],
                        fill=CYAN + (int((0.5 + k * 0.5) * 255),))
        else:
            hh = ((rank * 2654435761 + int(t * 1000) * 40503) & 0xFFFF) / 65535
            yy = band_top + hh * (h * SS - band_top - 8)
            solo = l["keys"] <= 1
            d.rectangle([x, yy, x + 2 * SS, yy + 2 * SS],
                        fill=(FLOOR if solo else (0, 120, 150)) + (215,))
    return img.resize((w, h), Image.LANCZOS)


def main():
    tape = json.load(io.open(os.path.join(HERE, "data", "tape.json"), encoding="utf-8"))
    img = Image.new("RGB", (W, H), BASE)
    d = ImageDraw.Draw(img)

    d.text((64, 54), "TECHNOCORE TAPE", font=font(44), fill=ICE)
    d.text((64, 116), "three minutes of /r/lobby, counted by sentence instead of by agent",
           font=font(21), fill=DIM)

    stats = [
        (f"{tape['messages']:,}", "MESSAGES", ICE),
        (f"{tape['keys']:,}", "DISTINCT KEYS", ICE),
        (f"{tape['shapes']:,}", "DISTINCT SENTENCES", ICE),
        (f"{tape['widest']}", "KEYS ON ONE SENTENCE", CYAN),
        (f"{tape['shared_traffic']}%", "TRAFFIC IS SHARED", CYAN),
    ]
    x = 64
    for value, label, colour in stats:
        d.text((x, 176), value, font=font(40), fill=colour)
        d.text((x, 226), label, font=font(14), fill=DIM)
        x += 305

    img.paste(tape_layer(tape, W - 128, 520), (64, 274))
    d.text((64, 818), "0xbusuzima.github.io/technocore-tape", font=font(22), fill=CYAN)
    d.text((W - 64 - 380, 822), f"cut {tape['cut_at']}", font=font(16), fill=(92, 102, 112))

    out = os.path.join(HERE, "card.png")
    img.save(out)
    print(f"  {out}  ({os.path.getsize(out):,} bytes)")


if __name__ == "__main__":
    main()
