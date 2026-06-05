/* ===========================================================================
   Motif Explorer — interactions
   =========================================================================== */
(function () {
  "use strict";
  const { PIXEL_COLORS, COMMON_MOTIFS, RARE_MOTIFS } = window.MOTIF_DATA;

  /* ---------------------------------------------------------------------- *
   * Web Audio — tiny 8-bit blips (toggleable, off by default)
   * ---------------------------------------------------------------------- */
  let audioOn = false;
  let actx = null;
  function ensureCtx() {
    if (!actx) {
      try { actx = new (window.AudioContext || window.webkitAudioContext)(); }
      catch (e) { actx = null; }
    }
    if (actx && actx.state === "suspended") actx.resume();
    return actx;
  }
  function beep(freq, dur, type, vol) {
    if (!audioOn) return;
    const ctx = ensureCtx();
    if (!ctx) return;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type || "square";
    o.frequency.value = freq;
    g.gain.value = vol == null ? 0.05 : vol;
    o.connect(g); g.connect(ctx.destination);
    const t = ctx.currentTime;
    g.gain.setValueAtTime(g.gain.value, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + (dur || 0.08));
    o.start(t); o.stop(t + (dur || 0.08));
  }
  const sfx = {
    hover: () => beep(660, 0.05, "square", 0.03),
    select: () => { beep(880, 0.06); setTimeout(() => beep(1320, 0.08), 60); },
    fire: () => { beep(1200, 0.05, "square", 0.04); setTimeout(() => beep(400, 0.12, "sawtooth", 0.04), 40); },
    roll: () => beep(220, 0.05, "square", 0.04),
    reveal: () => { [523, 659, 784, 1047].forEach((f, i) => setTimeout(() => beep(f, 0.1), i * 80)); },
    close: () => beep(300, 0.1, "square", 0.04),
    vote: () => { beep(900, 0.05); setTimeout(() => beep(1200, 0.06), 50); },
  };

  const soundToggle = document.getElementById("soundToggle");
  soundToggle.addEventListener("click", () => {
    audioOn = !audioOn;
    if (audioOn) ensureCtx();
    soundToggle.classList.toggle("off", !audioOn);
    soundToggle.textContent = audioOn ? "SND ON" : "SND OFF";
    soundToggle.setAttribute("aria-pressed", String(audioOn));
    if (audioOn) sfx.select();
  });

  /* ---------------------------------------------------------------------- *
   * Pixel-art invader renderer
   * ---------------------------------------------------------------------- */
  function buildInvader(bitmap, px) {
    px = px || 7;
    const rows = bitmap.length;
    const cols = bitmap[0].length;
    const el = document.createElement("div");
    el.className = "invader";
    el.style.gridTemplateColumns = `repeat(${cols}, ${px}px)`;
    el.style.gridTemplateRows = `repeat(${rows}, ${px}px)`;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const ch = bitmap[r][c];
        const cell = document.createElement("i");
        cell.style.width = px + "px";
        cell.style.height = px + "px";
        if (ch !== "." && PIXEL_COLORS[ch]) {
          cell.style.background = PIXEL_COLORS[ch];
          cell.style.boxShadow = `0 0 ${Math.max(2, px - 4)}px ${PIXEL_COLORS[ch]}55`;
        }
        el.appendChild(cell);
      }
    }
    return el;
  }

  // simple generic "march invader" for hero / scanning rows
  const MARCH_BITMAP = [
    "..G.....G..",
    "...G...G...",
    "..GGGGGGG..",
    ".GG.GGG.GG.",
    "GGGGGGGGGGG",
    "G.GGGGGGG.G",
    "G.G.....G.G",
    "...GG.GG...",
  ];

  /* ---------------------------------------------------------------------- *
   * Hero / scanning invader rows
   * ---------------------------------------------------------------------- */
  function fillHero() {
    const host = document.getElementById("heroInvaders");
    const colors = ["G", "P", "C", "Y", "G"];
    colors.forEach((col, i) => {
      const bmp = MARCH_BITMAP.map((row) => row.replace(/G/g, col));
      const inv = buildInvader(bmp, 6);
      inv.classList.add("anim-march");
      inv.style.animationDelay = (i * 0.12) + "s";
      inv.style.color = PIXEL_COLORS[col];
      host.appendChild(inv);
    });
  }

  /* ---------------------------------------------------------------------- *
   * Common motif tiles
   * ---------------------------------------------------------------------- */
  function fireShot(tile) {
    const shot = document.createElement("div");
    shot.className = "shot";
    tile.appendChild(shot);
    setTimeout(() => shot.remove(), 460);
  }

  function buildMotifRow() {
    const row = document.getElementById("motifRow");
    COMMON_MOTIFS.forEach((m, idx) => {
      const tile = document.createElement("button");
      tile.className = "motif-tile bezel p-4 flex flex-col items-center text-center";
      tile.style.color = m.accent;
      tile.setAttribute("aria-label", m.name + ", open reports");

      const wrap = document.createElement("div");
      wrap.className = "anim-bob flex items-end justify-center";
      wrap.style.height = "70px";
      wrap.style.animationDelay = (idx * 0.2) + "s";
      wrap.appendChild(buildInvader(m.bitmap, 7));
      tile.appendChild(wrap);

      const score = document.createElement("div");
      score.className = "font-arcade mt-2";
      score.style.fontSize = "9px";
      score.style.color = m.accent;
      score.textContent = String(m.prevalence).padStart(5, "0");
      tile.appendChild(score);

      const name = document.createElement("div");
      name.className = "mt-1 text-base sm:text-lg leading-tight";
      name.style.color = "#cffbcf";
      name.textContent = m.name;
      tile.appendChild(name);

      const sub = document.createElement("div");
      sub.className = "text-sm mt-1";
      sub.style.color = "var(--green-dim)";
      sub.textContent = "chunks high-sim";
      tile.appendChild(sub);

      tile.addEventListener("mouseenter", sfx.hover);
      tile.addEventListener("click", () => {
        fireShot(tile);
        sfx.fire();
        setTimeout(() => { sfx.select(); openCommon(m); }, 240);
      });
      row.appendChild(tile);
    });
  }

  /* ---------------------------------------------------------------------- *
   * Overlay helpers
   * ---------------------------------------------------------------------- */
  const overlay = document.getElementById("overlay");
  const overlayCard = document.getElementById("overlayCard");

  function showOverlay(html, pink) {
    overlayCard.classList.toggle("bezel-pink", !!pink);
    overlayCard.innerHTML = html;
    overlay.classList.add("show");
    overlayCard.scrollTop = 0;
    overlay.scrollTop = 0;
    document.body.style.overflow = "hidden";
    const closeBtn = overlayCard.querySelector("[data-close]");
    if (closeBtn) closeBtn.focus();
  }
  function hideOverlay() {
    overlay.classList.remove("show");
    document.body.style.overflow = "";
    sfx.close();
  }
  overlay.addEventListener("click", (e) => { if (e.target === overlay) hideOverlay(); });
  overlayCard.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) hideOverlay(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && overlay.classList.contains("show")) hideOverlay(); });

  function esc(s) {
    return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function simDots(score) {
    // map 0.5..1.0 -> 0..5 dots
    const n = Math.max(0, Math.min(5, Math.round((score - 0.5) * 10)));
    let s = '<span class="inline-flex gap-1 align-middle">';
    for (let i = 0; i < 5; i++) s += `<span class="simdot ${i < n ? "on" : ""}"></span>`;
    s += "</span>";
    return s;
  }

  function quoteCard(q, accent) {
    return `
      <div class="quote-card inner-scan p-4">
        <p class="text-lg sm:text-xl leading-snug" style="color:#daffd9">&ldquo;${esc(q.text)}&rdquo;</p>
        <div class="flex items-center justify-between mt-3 flex-wrap gap-2">
          <span class="text-base" style="color:var(--cyan)">▸ NUFORC SIGHTING #${esc(q.id)}</span>
          ${q.sim != null ? `<span class="text-base flex items-center gap-2" style="color:${accent}">SIM ${q.sim.toFixed(2)} ${simDots(q.sim)}</span>` : ""}
        </div>
      </div>`;
  }

  function closeRow(label, accent) {
    return `
      <div class="flex items-center justify-between mb-5">
        <span class="font-arcade glow-green" style="font-size:9px;color:${accent || "var(--green)"}">${label}</span>
        <button data-close class="ghost-btn px-3 py-2" style="font-size:9px" aria-label="Close">✕ CLOSE</button>
      </div>`;
  }

  /* ---------------------------------------------------------------------- *
   * Open a COMMON motif (GAME OVER style detail card)
   * ---------------------------------------------------------------------- */
  function openCommon(m) {
    const quotes = m.quotes.map((q) => quoteCard(q, m.accent)).join("");
    const html = `
      ${closeRow("LEVEL 1 — MOTIF FILE", m.accent)}
      <div class="text-center mb-6">
        <div class="anim-bob inline-block" id="ovInv"></div>
        <h2 class="font-arcade mt-4 leading-[1.3] text-[15px] sm:text-[22px]" style="color:${m.accent};text-shadow:0 0 10px ${m.accent}99">${esc(m.name)}</h2>
        <p class="text-lg mt-3" style="color:var(--green-dim)">${esc(m.blurb)}</p>
      </div>

      <div class="grid grid-cols-2 gap-3 mb-6">
        <div class="bezel p-3 text-center">
          <div class="font-arcade text-[var(--pink)]" style="font-size:20px">${m.prevalence.toLocaleString()}</div>
          <div class="text-base mt-1" style="color:var(--green-dim)">chunks at high similarity</div>
        </div>
        <div class="bezel p-3 text-center">
          <div class="font-arcade glow-green" style="font-size:20px">${m.quotes[0].sim.toFixed(2)}</div>
          <div class="text-base mt-1" style="color:var(--green-dim)">top cosine score</div>
        </div>
      </div>

      <p class="text-base mb-3" style="color:var(--green-dim)">"This many reports feel very close in meaning to the perfect example story of this motif."</p>

      <h3 class="font-arcade glow-green mb-3" style="font-size:10px">SEMANTIC UNITS — TOP MATCHES</h3>
      <div class="space-y-3 mb-6">${quotes}</div>

      <div class="bezel bezel-pink p-4">
        <div class="font-arcade text-[var(--pink)] mb-2" style="font-size:10px">WHY THIS FEELS SEMANTIC</div>
        <p class="text-lg leading-snug" style="color:#daffd9">${esc(m.why)}</p>
      </div>

      <div class="text-center mt-6">
        <button data-close class="ghost-btn px-5 py-3" style="font-size:10px">◀ BACK TO LINEUP</button>
      </div>`;
    showOverlay(html, false);
    const slot = document.getElementById("ovInv");
    if (slot) slot.appendChild(buildInvader(m.bitmap, 9));
  }

  /* ---------------------------------------------------------------------- *
   * ROLL FOR WEIRD — scanning animation then reveal a rare motif
   * ---------------------------------------------------------------------- */
  let lastRare = -1;
  function pickRare() {
    let i = Math.floor(Math.random() * RARE_MOTIFS.length);
    if (RARE_MOTIFS.length > 1) { while (i === lastRare) i = Math.floor(Math.random() * RARE_MOTIFS.length); }
    lastRare = i;
    return RARE_MOTIFS[i];
  }

  function scanningMarkup() {
    return `
      ${closeRow("LEVEL 2 — SCANNING", "var(--pink)")}
      <div class="text-center py-10">
        <div class="scan-row mb-8" id="scanRow"></div>
        <div class="font-arcade text-[var(--pink)] glow-pink blink" style="font-size:13px">SCANNING&nbsp;21,179&nbsp;CHUNKS…</div>
        <div class="mt-4 text-lg" style="color:var(--green-dim)"><span id="scanCount">000000</span> / 021179 vectors searched</div>
        <div class="w-full max-w-md mx-auto mt-5" style="height:14px;border:2px solid var(--pink);background:#1a0712">
          <div id="scanBar" style="height:100%;width:0;background:var(--pink);box-shadow:0 0 10px var(--pink);transition:width .1s linear"></div>
        </div>
      </div>`;
  }

  function buildScanRow() {
    const host = document.getElementById("scanRow");
    if (!host) return;
    const cols = ["P", "G", "C", "Y", "P", "G"];
    cols.forEach((col, i) => {
      const bmp = MARCH_BITMAP.map((r) => r.replace(/G/g, col));
      const inv = buildInvader(bmp, 6);
      inv.classList.add("anim-march");
      inv.style.animationDelay = (i * 0.1) + "s";
      host.appendChild(inv);
    });
  }

  function runScan(done) {
    showOverlay(scanningMarkup(), true);
    buildScanRow();
    const bar = document.getElementById("scanBar");
    const count = document.getElementById("scanCount");
    let p = 0;
    const total = 21179;
    let beepTick = 0;
    const iv = setInterval(() => {
      p += 0.07 + Math.random() * 0.06;
      if (p >= 1) p = 1;
      if (bar) bar.style.width = (p * 100) + "%";
      if (count) count.textContent = String(Math.floor(p * total)).padStart(6, "0");
      if ((beepTick++ % 2) === 0) sfx.roll();
      if (p >= 1) { clearInterval(iv); setTimeout(done, 260); }
    }, 110);
  }

  function openRare(m) {
    sfx.reveal();
    const quotes = m.quotes.map((q) => quoteCard(q, "var(--pink)")).join("");
    const html = `
      ${closeRow("LEVEL 2 — UNCOMMON FIND", "var(--pink)")}
      <div class="text-center mb-5">
        <div class="font-arcade text-[var(--pink)] glow-pink" style="font-size:11px">★ WEIRD / UNCOMMON ★</div>
        <h2 class="font-arcade mt-4 leading-[1.35] text-[14px] sm:text-[20px]" style="color:var(--yellow);text-shadow:0 0 10px var(--yellow)">${esc(m.name)}</h2>
        <div class="inline-block mt-4 px-4 py-2 bezel bezel-pink">
          <span class="text-lg" style="color:#daffd9">CLUSTER SIZE:</span>
          <span class="font-arcade text-[var(--pink)]" style="font-size:14px">${m.size}</span>
          <span class="text-lg" style="color:var(--green-dim)">chunks</span>
        </div>
      </div>

      <div class="bezel p-4 mb-6 text-center">
        <p class="text-lg sm:text-xl" style="color:#daffd9">⚠ This is weird — we haven't seen much of this combination in the literature. Keep that in mind.</p>
      </div>

      <h3 class="font-arcade text-[var(--pink)] mb-3" style="font-size:10px">SEMANTIC UNITS — FROM THE CLUSTER</h3>
      <div class="space-y-3 mb-6">${quotes}</div>

      <div class="bezel p-4 mb-6">
        <div class="font-arcade glow-green mb-2" style="font-size:10px">WHY THIS GROUPING FEELS LIKE A MOTIF</div>
        <p class="text-lg leading-snug" style="color:#daffd9">${esc(m.why)}</p>
      </div>

      <!-- noise vs artifact prompt -->
      <div class="bezel bezel-pink p-5 text-center" id="voteBox">
        <div class="font-arcade text-[var(--pink)] glow-pink mb-4" style="font-size:11px;line-height:1.6">NOISE&nbsp;— OR A TINY ARTIFACT<br/>OF THE EMBEDDING?</div>
        <div class="flex items-center justify-center gap-3 flex-wrap">
          <button class="arcade-btn px-4 py-3" data-vote="up" style="font-size:10px">▲ <span class="lab">INTERESTING</span></button>
          <button class="ghost-btn px-4 py-3" data-vote="down" style="font-size:10px">▼ NOISE</button>
        </div>
      </div>

      <div class="flex items-center justify-center gap-3 mt-7 flex-wrap">
        <button id="rollAgain" class="arcade-btn px-5 py-4" style="font-size:11px">↻ <span class="lab">ROLL&nbsp;AGAIN</span></button>
        <button data-close class="ghost-btn px-5 py-4" style="font-size:11px">✕ DONE</button>
      </div>`;
    showOverlay(html, true);

    const again = document.getElementById("rollAgain");
    if (again) again.addEventListener("click", () => { sfx.fire(); runScan(() => openRare(pickRare())); });

    overlayCard.querySelectorAll("[data-vote]").forEach((b) => {
      b.addEventListener("click", () => {
        sfx.vote();
        const box = document.getElementById("voteBox");
        const up = b.getAttribute("data-vote") === "up";
        box.innerHTML = `<div class="font-arcade ${up ? "glow-green" : "text-[var(--green-dim)]"} py-2" style="font-size:11px;line-height:1.7;color:${up ? "var(--green)" : "var(--green-dim)"}">${up ? "✓ LOGGED — THANKS, EXPLORER!" : "✓ LOGGED AS NOISE — NOTED."}</div><div class="text-base mt-1" style="color:var(--green-dim)">(v1 just says thanks — real voting lands in v2)</div>`;
        console.log("[vote]", up ? "interesting" : "noise", "→", m.name);
      });
    });
  }

  document.getElementById("rollBtn").addEventListener("click", () => {
    sfx.fire();
    runScan(() => openRare(pickRare()));
  });

  /* ---------------------------------------------------------------------- *
   * Toy 2-D semantic space plot
   * ---------------------------------------------------------------------- */
  function drawPlot() {
    const cv = document.getElementById("plot");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    ctx.fillStyle = "#020602";
    ctx.fillRect(0, 0, W, H);

    // grid
    ctx.strokeStyle = "rgba(57,255,20,0.10)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= W; x += 26) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y <= H; y += 26) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

    // seeded rng
    let seed = 1337;
    const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
    const gauss = () => (rnd() + rnd() + rnd() + rnd() - 2) / 2;

    // rare scatter (faint)
    for (let i = 0; i < 90; i++) {
      const x = rnd() * W, y = rnd() * H;
      ctx.fillStyle = "rgba(120,160,120,0.30)";
      ctx.fillRect(x, y, 2, 2);
    }

    // 5 common blobs
    const blobs = [
      { x: 0.22, y: 0.30, c: "#39ff14", n: "Silent Triangle" },
      { x: 0.74, y: 0.24, c: "#ff3ea5", n: "Physical Scars" },
      { x: 0.50, y: 0.55, c: "#22e0ff", n: "Gray Exam" },
      { x: 0.26, y: 0.78, c: "#ffe23d", n: "Telepathy" },
      { x: 0.78, y: 0.72, c: "#39ff14", n: "Beam Lift" },
    ];
    blobs.forEach((b) => {
      const cx = b.x * W, cy = b.y * H;
      for (let i = 0; i < 46; i++) {
        const px = cx + gauss() * 26;
        const py = cy + gauss() * 20;
        ctx.fillStyle = b.c;
        ctx.globalAlpha = 0.55;
        ctx.fillRect(px, py, 3, 3);
      }
      ctx.globalAlpha = 1;
      // halo
      ctx.strokeStyle = b.c;
      ctx.globalAlpha = 0.4;
      ctx.beginPath();
      ctx.ellipse(cx, cy, 40, 32, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // legend
    const leg = document.getElementById("plotLegend");
    leg.innerHTML = blobs.map((b) =>
      `<span class="inline-flex items-center gap-2" style="color:${b.c}"><span style="width:10px;height:10px;background:${b.c};display:inline-block;box-shadow:0 0 6px ${b.c}"></span>${b.n}</span>`
    ).join("") + `<span class="inline-flex items-center gap-2" style="color:#7a9a7a"><span style="width:10px;height:10px;background:#7a9a7a;display:inline-block"></span>rare scatter</span>`;
  }

  /* ---------------------------------------------------------------------- *
   * Starfield
   * ---------------------------------------------------------------------- */
  function starfield() {
    const cv = document.getElementById("starfield");
    const ctx = cv.getContext("2d");
    let stars = [];
    function resize() {
      cv.width = window.innerWidth;
      cv.height = window.innerHeight;
      stars = [];
      const n = Math.floor((cv.width * cv.height) / 9000);
      for (let i = 0; i < n; i++) {
        stars.push({ x: Math.random() * cv.width, y: Math.random() * cv.height, s: Math.random() * 1.6 + 0.4, tw: Math.random() * Math.PI * 2, sp: 0.01 + Math.random() * 0.03 });
      }
    }
    function frame() {
      ctx.clearRect(0, 0, cv.width, cv.height);
      for (const st of stars) {
        st.tw += st.sp;
        const a = 0.35 + Math.abs(Math.sin(st.tw)) * 0.5;
        ctx.fillStyle = `rgba(180,255,180,${a})`;
        ctx.fillRect(st.x, st.y, st.s, st.s);
      }
      requestAnimationFrame(frame);
    }
    window.addEventListener("resize", resize);
    resize();
    frame();
  }

  /* ---------------------------------------------------------------------- *
   * Footer ticker
   * ---------------------------------------------------------------------- */
  function fillTicker() {
    const txt = "  ★  21,179 CHUNKS INDEXED  ★  5 COMMON MOTIFS  ★  30 RARE CLUSTERS  ★  e5-large-v2 EMBEDDINGS  ★  COSINE SIMILARITY  ★  ALL PROVENANCE TRACEABLE  ★  PRESS START  ";
    document.getElementById("tickerA").textContent = txt;
    document.getElementById("tickerB").textContent = txt;
  }

  /* ---------------------------------------------------------------------- *
   * boot
   * ---------------------------------------------------------------------- */
  fillHero();
  buildMotifRow();
  drawPlot();
  starfield();
  fillTicker();
})();
