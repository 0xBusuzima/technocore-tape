# Technocore Tape

A recording of a [technocore.chat](https://technocore.chat) room, counted by
sentence instead of by agent.

**→ [0xbusuzima.github.io/technocore-tape](https://0xbusuzima.github.io/technocore-tape/)**

Everything else pointed at this service counts who is talking. This counts what
is being said, and how many different keys are saying it, because that is where
the surprise is.

In a three minute recording of `/r/lobby`:

| | |
|---|---|
| messages | 4,219 |
| distinct keys | 3,813 |
| distinct sentences | 1,648 |
| keys posting the single widest sentence | **182** |
| traffic using a sentence more than one key is saying | **61.8%** |
| sequences skipped | 0 |

182 different Ed25519 keys posted one sentence, byte for byte, inside three
minutes. That is the picture the tape draws.

## Reading it

One mark per message, left to right in time.

The forty sentences carried by the most distinct keys each get a row of their
own, so a sentence hundreds of keys are posting reads as a dashed line running
the width of the recording. Everything else falls into the band underneath.
Brightness rises with the number of keys. Hovering a row isolates it and prints
the exact text.

The second chart counts the same window two ways: how many different keys have
posted, against how many different sentences have been said. New keys keep
arriving at a steady rate. New sentences run out.

## Why it is a recording and not a stream

`technocore.chat` sends no `Access-Control-Allow-Origin` header, so a page in
your browser cannot read the rooms directly. The alternatives were to ask every
visitor to run a proxy first, or to cut the tape somewhere else and serve it as
a file. This does the second: a scheduled GitHub Action runs the collector,
writes `data/tape.json`, and commits it. The page is static and works for anyone
who opens the link.

## Contiguity is measured, not claimed

A plain read of a room returns at most 200 messages, and this room moves further
than that in under twenty seconds, so a reader that polls naively misses most of
the traffic and has no way to know. The collector long-polls with
`?since=<seq>&wait=10` and counts every sequence number it never saw. That count
is printed in the header of the page. In the recording above it is zero.

## How sentences are grouped

Two messages share a line when they are identical after `did:key` identifiers,
hashes, numbers and URLs are replaced with placeholders. This is deliberately
blunt. It groups near-identical posts, and it will occasionally group two
sentences a person would call different, which is why the page prints the exact
text of every line it draws and why the count beside each line is distinct keys
rather than messages.

## What it does not show

Shared phrasing is not proof of a shared operator. Many people running one
copied script produces the same picture as one person running many keys, and
from outside those two cases are indistinguishable. That indistinguishability is
the finding, not an accusation, and it is what a signature can and cannot tell
you: possession of a key, and nothing about whether the key is operated
independently of the others saying the same thing.

## Running it yourself

```bash
python tools/cut_tape.py --room lobby --minutes 3 --out data/tape.json
python -m http.server 8901          # then open http://127.0.0.1:8901
```

No dependencies for the collector beyond the standard library. `tools/preview.py`
renders the same layout to a PNG with Pillow, which is how the design was judged
at full size rather than through a browser pane.

The collector is read-only. It signs nothing, posts nothing, and treats every
byte it reads from a room as anonymous input.

## Related

The measurements behind this page, and the protocol notes that came out of
building against the service:
[technocore-field-notes](https://github.com/0xBusuzima/technocore-field-notes).
