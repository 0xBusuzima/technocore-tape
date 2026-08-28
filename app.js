// Technocore Tape. Read-only, no dependencies, no build step.
// The unit is the sentence, not the agent.

const ROWS = 40, ROW_TOP = 30;
let TAPE = null, hot = -1, sweep = 0, rows = {}, bandTop = 0;

const cv = document.getElementById('tape');
const cx = cv.getContext('2d');
const gv = document.getElementById('growth');
const gx = gv.getContext('2d');
const tip = document.getElementById('tip');

const fmt = n => n == null ? '?' : n.toLocaleString('en-US');
const esc = s => s.replace(/[<>&]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));

fetch('data/tape.json?v=' + Date.now())
  .then(r => r.json())
  .then(start)
  .catch(() => {
    document.getElementById('cut').textContent = 'could not load data/tape.json';
  });

function start(t) {
  TAPE = t;
  layout();

  document.getElementById('cut').textContent =
    `/r/${t.room} · cut ${t.cut_at} · ${t.span_seconds}s of room time · ` +
    `${fmt(t.skipped)} sequences skipped · seq ${fmt(t.first_seq)}-${fmt(t.last_seq)}`;
  document.getElementById('t1').textContent = t.span_seconds + 's';

  document.getElementById('readout').innerHTML = [
    [fmt(t.messages), 'messages', 0],
    [fmt(t.keys), 'distinct keys', 0],
    [fmt(t.shapes), 'distinct sentences', 0],
    [fmt(t.widest), 'keys on one sentence', 1],
    [t.shared_traffic + '%', 'traffic is shared', 1],
    [fmt(t.rate_per_min), 'messages a minute', 0],
  ].map(([v, l, h]) =>
    `<div class="cell${h ? ' hot' : ''}"><b>${v}</b><span>${l}</span></div>`).join('');

  const shared = t.lines.map((l, i) => [l, i]).filter(([l]) => l.keys > 1).slice(0, ROWS);
  document.getElementById('lines').innerHTML = shared.map(([l, i]) =>
    `<li data-i="${i}"><div class="n">${l.keys}<small>keys</small></div>` +
    `<div class="t">${esc(l.text)}` +
    (l.verbatim > 1 ? `<em>${l.verbatim} of ${l.n} byte-identical</em>` : '') +
    `</div></li>`).join('');

  document.querySelectorAll('#lines li').forEach(li => {
    li.addEventListener('mouseenter', () => { hot = +li.dataset.i; draw(); });
    li.addEventListener('mouseleave', () => { hot = -1; draw(); });
  });

  drawGrowth();

  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { sweep = 1; draw(); return; }
  const t0 = performance.now(), dur = 2400;
  (function step(now) {
    sweep = Math.min(1, (now - t0) / dur);
    draw();
    if (sweep < 1) requestAnimationFrame(step);
  })(t0);
}

// Rows widen toward the top: the heaviest lines carry a mark roughly every
// second and would otherwise fuse into a block, which is the one row a reader
// most needs to read as a single sentence.
function layout() {
  const shared = [];
  for (let i = 0; i < TAPE.lines.length && shared.length < ROWS; i++) {
    if (TAPE.lines[i].keys > 1) shared.push(i);
  }
  rows = {};
  let y = ROW_TOP;
  shared.forEach((r, n) => {
    rows[r] = y;
    y += 17.5 - 9.0 * (n / Math.max(shared.length - 1, 1));
  });
  bandTop = y + 40;
}

function draw() {
  const W = cv.width, H = cv.height;
  cx.fillStyle = '#0C1430';
  cx.fillRect(0, 0, W, H);
  if (!TAPE) return;

  cx.fillStyle = 'rgba(35,42,62,.55)';
  for (const r in rows) cx.fillRect(0, rows[r] + 2, W, 1);
  cx.fillStyle = '#1A2340';
  cx.fillRect(0, bandTop - 22, W, 2);

  const span = TAPE.span_seconds || 1;
  const cut = sweep * W;
  const widest = Math.max(TAPE.widest, 10);

  for (const [t, rank, ki] of TAPE.marks) {
    const x = (t / span) * (W - 10) + 5;
    if (x > cut) continue;
    const l = TAPE.lines[rank];
    const inRow = rows.hasOwnProperty(rank);
    let y, w, h, col, a;

    if (inRow) {
      y = rows[rank];
      w = 3; h = 4;
      const k = Math.min(1, Math.log10(l.keys) / Math.log10(widest));
      col = '0,180,216'; a = 0.45 + k * 0.55;
    } else {
      const hh = ((rank * 2654435761 + ((t * 1000) | 0) * 40503) & 0xFFFF) / 65535;
      y = bandTop + hh * (H - bandTop - 8);
      w = 2; h = 2;
      col = l.keys <= 1 ? '46,56,82' : '0,120,150';
      a = l.keys <= 1 ? 0.78 : 0.9;
    }

    if (hot >= 0) {
      if (rank === hot) { col = '245,247,250'; a = 1; w = 4; h = 5; }
      else a *= 0.12;
    }
    cx.fillStyle = `rgba(${col},${a})`;
    cx.fillRect(x, y, w, h);
  }
}

// Two curves over the same window: how many different keys have been seen, and
// how many different sentences. The gap between them is the whole point.
function drawGrowth() {
  const W = gv.width, H = gv.height, pad = 26;
  gx.fillStyle = '#0C1430';
  gx.fillRect(0, 0, W, H);

  const span = TAPE.span_seconds || 1;
  const seenK = new Set(), seenS = new Set();
  const kPts = [], sPts = [];
  const sorted = TAPE.marks.slice().sort((a, b) => a[0] - b[0]);
  for (const [t, rank, ki] of sorted) {
    seenK.add(ki); seenS.add(rank);
    kPts.push([t, seenK.size]);
    sPts.push([t, seenS.size]);
  }
  const maxY = Math.max(seenK.size, seenS.size) || 1;
  const X = t => pad + (t / span) * (W - pad * 2);
  const Y = v => H - pad - (v / maxY) * (H - pad * 2);

  gx.strokeStyle = 'rgba(35,42,62,.9)';
  gx.lineWidth = 1;
  gx.beginPath(); gx.moveTo(pad, Y(0)); gx.lineTo(W - pad, Y(0)); gx.stroke();

  const line = (pts, colour, width) => {
    gx.strokeStyle = colour; gx.lineWidth = width;
    gx.beginPath();
    pts.forEach(([t, v], i) => i ? gx.lineTo(X(t), Y(v)) : gx.moveTo(X(t), Y(v)));
    gx.stroke();
  };
  line(sPts, '#5C6670', 3);
  line(kPts, '#00B4D8', 3);

  gx.font = '600 22px "Space Mono", monospace';
  gx.fillStyle = '#00B4D8';
  gx.fillText(`${fmt(seenK.size)} keys`, X(span) - 210, Y(seenK.size) - 14);
  gx.fillStyle = '#A1A7AE';
  gx.fillText(`${fmt(seenS.size)} sentences`, X(span) - 260, Y(seenS.size) + 34);
}

cv.addEventListener('mousemove', e => {
  if (!TAPE) return;
  const r = cv.getBoundingClientRect();
  const y = (e.clientY - r.top) / r.height * cv.height;
  let best = -1, bd = 1e9;
  for (const k in rows) {
    const d = Math.abs(rows[k] - y);
    if (d < bd) { bd = d; best = +k; }
  }
  if (bd > 9 || best < 0) {
    tip.style.opacity = 0;
    if (hot !== -1) { hot = -1; draw(); }
    return;
  }
  if (best !== hot) { hot = best; draw(); }
  const l = TAPE.lines[best];
  tip.innerHTML = `<b>${l.keys} distinct keys · ${l.n} messages</b>${esc(l.text)}`;
  tip.style.opacity = 1;
  tip.style.left = Math.min(e.clientX - r.left + 14, r.width - 430) + 'px';
  tip.style.top = Math.max(6, (e.clientY - r.top) - 10) + 'px';
});

cv.addEventListener('mouseleave', () => {
  tip.style.opacity = 0; hot = -1; draw();
});
