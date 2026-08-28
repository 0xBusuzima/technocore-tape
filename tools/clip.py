#!/usr/bin/env python3
"""Render the tape as an animated GIF: the recording plays back in time while
the counters climb with it.

    python tools/clip.py

The point of the motion is the pair of counters. Keys keep arriving at a steady
rate for the whole three minutes; sentences flatten out early. Watching the two
numbers separate says the thing the still image can only imply.
"""
import io, json, math, os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(os.path.dirname(HERE), "technocore-logo", "SpaceMono-Bold.ttf")

W, H = 1200, 675
FRAMES, HOLD, MS = 56, 14, 80
BASE, PANEL, CYAN, ICE, DIM, FLOOR, GREY = (
    (10, 17, 40), (12, 20, 48), (0, 180, 216), (245, 247, 250),
    (161, 167, 174), (46, 56, 82), (92, 102, 112))

TAPE_X, TAPE_Y, TAPE_W, TAPE_H = 46, 216, W - 92, 396
ROWS, ROW_TOP = 34, 14


def font(px):
    return ImageFont.truetype(FONT, px)


def build():
    tape = json.load(io.open(os.path.join(HERE, "data", "tape.json"), encoding="utf-8"))
    lines, marks = tape["lines"], sorted(tape["marks"], key=lambda m: m[0])
    span = tape["span_seconds"] or 1
    widest = max(tape["widest"], 10)

    shared = [i for i, l in enumerate(lines) if l["keys"] > 1][:ROWS]
    rows, y = {}, ROW_TOP
    for n, r in enumerate(shared):
        rows[r] = y
        y += 9.0 - 4.5 * (n / max(len(shared) - 1, 1))
    band_top = y + 22

    # Static background: everything that never changes between frames.
    bg = Image.new("RGB", (W, H), BASE)
    d = ImageDraw.Draw(bg)
    d.text((46, 40), "TECHNOCORE TAPE", font=font(34), fill=ICE)
    d.text((46, 86), "three minutes of /r/lobby, counted by sentence instead of by agent",
           font=font(16), fill=DIM)
    d.rectangle([TAPE_X, TAPE_Y, TAPE_X + TAPE_W, TAPE_Y + TAPE_H], fill=PANEL)
    for r, ry in rows.items():
        d.line([(TAPE_X, TAPE_Y + ry + 2), (TAPE_X + TAPE_W, TAPE_Y + ry + 2)],
               fill=(33, 40, 60), width=1)
    d.line([(TAPE_X, TAPE_Y + band_top - 11), (TAPE_X + TAPE_W, TAPE_Y + band_top - 11)],
           fill=(26, 35, 64), width=2)
    d.text((46, 630), "0xbusuzima.github.io/technocore-tape", font=font(17), fill=CYAN)

    frames = []
    seen_k, seen_s = set(), set()
    drawn = 0
    for f in range(FRAMES):
        cutoff = span * (f + 1) / FRAMES
        img = bg.copy() if f == 0 else frames[-1].copy()
        dd = ImageDraw.Draw(img, "RGBA")

        while drawn < len(marks) and marks[drawn][0] <= cutoff:
            t, rank, ki = marks[drawn]
            drawn += 1
            seen_k.add(ki); seen_s.add(rank)
            l = lines[rank]
            x = TAPE_X + (t / span) * (TAPE_W - 8) + 4
            if rank in rows:
                k = min(1.0, math.log10(l["keys"]) / math.log10(widest))
                dd.rectangle([x, TAPE_Y + rows[rank], x + 2, TAPE_Y + rows[rank] + 3],
                             fill=CYAN + (int((0.5 + k * 0.5) * 255),))
            else:
                hh = ((rank * 2654435761 + int(t * 1000) * 40503) & 0xFFFF) / 65535
                yy = TAPE_Y + band_top + hh * (TAPE_H - band_top - 6)
                solo = l["keys"] <= 1
                dd.rectangle([x, yy, x + 2, yy + 2],
                             fill=(FLOOR if solo else (0, 120, 150)) + (220,))

        # counters, repainted each frame over a clean strip
        dd.rectangle([40, 126, W - 40, 200], fill=BASE)
        for i, (val, lab, col) in enumerate((
                (f"{drawn:,}", "MESSAGES", ICE),
                (f"{len(seen_k):,}", "DISTINCT KEYS", CYAN),
                (f"{len(seen_s):,}", "DISTINCT SENTENCES", GREY))):
            cx = 46 + i * 300
            dd.text((cx, 130), val, font=font(34), fill=col)
            dd.text((cx, 174), lab, font=font(12), fill=DIM)
        frames.append(img)

    frames.extend(frames[-1].copy() for _ in range(HOLD))

    out = os.path.join(HERE, "clip.gif")
    pal = [im.convert("P", palette=Image.ADAPTIVE, colors=32) for im in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=MS,
                loop=0, optimize=True, disposal=1)
    print(f"  {out}  ({os.path.getsize(out):,} bytes, {len(frames)} frames)")
    frames[len(frames) // 2].save(os.path.join(HERE, "clip-mid.png"))


if __name__ == "__main__":
    build()
