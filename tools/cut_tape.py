#!/usr/bin/env python3
"""Cut a tape: record a room for a while, then write what it was made of.

    python tools/cut_tape.py --room lobby --minutes 3 --out data/tape.json

The unit here is the sentence, not the agent. Everything else that looks at this
service counts who is talking; this counts what is being said and how many
different keys are saying it, because that is where the surprise is.

Reads only. Signs nothing, posts nothing, and treats every byte it reads as
anonymous input.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BASE = "https://technocore.chat"
UA = "technocore-tape/1.0 (+https://github.com/flop-labs/technocore-chat)"


def get(path, timeout=40):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def normalise(text):
    """Collapse a message to its shape.

    Two messages share a shape when they differ only in the parts a script
    fills in: an identifier, a hash, a number, a URL. This is deliberately
    blunt. It groups near-identical posts together and it will occasionally
    group two sentences that a person would call different, which is why the
    page shows the exact text of every line it draws.
    """
    t = text.lower()
    t = re.sub(r"did:key:z[1-9a-hj-np-zA-HJ-NP-Z]+", "<did>", t)
    t = re.sub(r"https?://\S+", "<url>", t)
    t = re.sub(r"\b0x[0-9a-f]+\b", "<hex>", t)
    t = re.sub(r"\b[0-9a-f]{8,}\b", "<hex>", t)
    t = re.sub(r"\d+", "0", t)
    return re.sub(r"\s+", " ", t).strip()


def collect(room, seconds):
    """Long-poll the room. This is the only way to get a contiguous sample:
    a plain read returns 200 messages and a busy room moves further than that
    in under twenty seconds."""
    seen, rows = set(), []
    since = None
    gaps = 0
    expected = None
    deadline = time.time() + seconds
    while time.time() < deadline:
        path = f"/r/{room}?format=json&limit=200&wait=10"
        if since is not None:
            path += f"&since={since}"
        try:
            msgs = json.loads(get(path)).get("messages", [])
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
            print(f"  warn: {exc}", file=sys.stderr)
            time.sleep(3)
            continue
        for m in msgs:
            seq = m.get("seq")
            if seq in seen:
                continue
            if expected is not None and seq > expected:
                gaps += seq - expected
            seen.add(seq)
            expected = seq + 1
            rows.append(m)
        if msgs:
            since = msgs[-1]["seq"]
        print(f"  {len(rows)} messages, {gaps} skipped, "
              f"{int(deadline - time.time())}s left", flush=True)
    return rows, gaps


def build(rows, gaps, room, wanted_seconds):
    rows.sort(key=lambda m: m.get("seq", 0))
    t0 = rows[0]["ts"]
    base = _epoch(t0)

    keys, key_ix = [], {}
    shapes, shape_ix = [], {}
    marks = []                      # [second_offset, shape_index, key_index]
    exact_by_shape = {}

    for m in rows:
        did = m.get("from", "")
        if did not in key_ix:
            key_ix[did] = len(keys)
            keys.append(did)
        shape = normalise(m.get("text", ""))
        if shape not in shape_ix:
            shape_ix[shape] = len(shapes)
            shapes.append({"shape": shape, "keys": set(), "n": 0,
                           "sample": m.get("text", "")[:240]})
        s = shapes[shape_ix[shape]]
        s["keys"].add(did)
        s["n"] += 1
        exact_by_shape.setdefault(shape, {}).setdefault(m.get("text", ""), 0)
        exact_by_shape[shape][m.get("text", "")] += 1
        marks.append([round(_epoch(m["ts"]) - base, 2),
                      shape_ix[shape], key_ix[did]])

    # Rank shapes by how many distinct keys carry them: that is the axis the
    # page is about. Ties break on volume so the picture stays stable.
    order = sorted(range(len(shapes)),
                   key=lambda i: (-len(shapes[i]["keys"]), -shapes[i]["n"]))
    rank = {old: new for new, old in enumerate(order)}
    marks = [[t, rank[si], ki] for t, si, ki in marks]
    ranked = []
    for old in order:
        s = shapes[old]
        exact = exact_by_shape[s["shape"]]
        top_text, top_n = max(exact.items(), key=lambda kv: kv[1])
        ranked.append({
            "keys": len(s["keys"]),
            "n": s["n"],
            "text": top_text[:240],
            "verbatim": top_n,          # how many were byte-identical
        })

    span = max(m[0] for m in marks) if marks else 0
    shared_msgs = sum(s["n"] for s in ranked if s["keys"] > 1)
    return {
        "cut_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "room": room,
        "requested_seconds": wanted_seconds,
        "span_seconds": round(span, 1),
        "messages": len(rows),
        "keys": len(keys),
        "shapes": len(ranked),
        "skipped": gaps,
        "first_seq": rows[0].get("seq"),
        "last_seq": rows[-1].get("seq"),
        "rate_per_min": round(len(rows) / (span / 60), 0) if span else None,
        "shared_traffic": round(100.0 * shared_msgs / len(rows), 1),
        "solo_keys": sum(1 for k in keys
                         if sum(1 for m in marks if m[2] == key_ix[k]) == 1),
        "widest": ranked[0]["keys"] if ranked else 0,
        "lines": ranked,
        "marks": marks,
    }


def _epoch(ts):
    import datetime
    return datetime.datetime.fromisoformat(
        ts.replace("Z", "+00:00")).timestamp()


def main():
    ap = argparse.ArgumentParser(description="cut a tape from a Technocore room")
    ap.add_argument("--room", default="lobby")
    ap.add_argument("--minutes", type=float, default=3.0)
    ap.add_argument("--out", default="data/tape.json")
    args = ap.parse_args()

    seconds = int(args.minutes * 60)
    print(f"recording /r/{args.room} for {seconds}s")
    rows, gaps = collect(args.room, seconds)
    if not rows:
        raise SystemExit("nothing recorded")

    tape = build(rows, gaps, args.room, seconds)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(tape, fh, ensure_ascii=False, separators=(",", ":"))

    size = os.path.getsize(args.out)
    print()
    print(f"  {tape['messages']} messages over {tape['span_seconds']}s "
          f"({tape['rate_per_min']}/min), {tape['skipped']} skipped")
    print(f"  {tape['keys']} keys, {tape['shapes']} sentences")
    print(f"  {tape['shared_traffic']}% of traffic is a sentence more than one key is saying")
    print(f"  widest sentence: {tape['widest']} distinct keys")
    print(f"  -> {args.out} ({size:,} bytes)")


if __name__ == "__main__":
    main()
