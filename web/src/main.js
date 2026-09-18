import "./styles.css";

const familyMeta = {
  blur_noise: { label: "Blur + noise", code: "BN", detail: "PSF × read / shot noise" },
  attenuation_contrast: { label: "Atten. + contrast", code: "AC", detail: "path loss × low ΔT" },
  badpixel_fpn: { label: "Bad pixel + FPN", code: "BF", detail: "partial defect field" },
  clutter_blur: { label: "Clutter + blur", code: "CB", detail: "structured distractors" },
  triple_shift: { label: "Triple shift", code: "TS", detail: "atten. × PSF × noise" },
};

const colours = { confidence_selective: "#57a8d8", shift_selective: "#f3a64a", quality_selective: "#4de0ac" };
const modeOrder = ["confidence_selective", "shift_selective", "quality_selective"];
const state = { data: null, family: "blur_noise", sampleIndex: 0, study: "confirmation", image: null, started: performance.now() };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function familySamples() {
  return state.data.samples.filter((sample) => sample.family === state.family);
}

function currentSample() {
  const samples = familySamples();
  return samples[state.sampleIndex % samples.length];
}

function renderFamilyList() {
  $("#family-list").innerHTML = Object.entries(familyMeta).map(([key, meta], index) => `
    <button class="family-card ${key === state.family ? "active" : ""}" data-family="${key}">
      <span>${String(index + 1).padStart(2, "0")}</span><div><b>${meta.label}</b><small>${meta.detail}</small></div><i>${meta.code}</i>
    </button>`).join("");
  $$(".family-card").forEach((button) => button.addEventListener("click", () => {
    state.family = button.dataset.family; state.sampleIndex = 0; renderAll();
  }));
}

function renderSampleStrip() {
  const samples = familySamples();
  $("#sample-strip").innerHTML = samples.map((sample, index) => `
    <button class="sample-chip ${index === state.sampleIndex ? "active" : ""}" data-index="${index}">
      <span>${sample.error ? "ERR" : "OK"}</span><b>${sample.seed}</b><i class="${sample.accepted ? "release" : "reject"}">${sample.accepted ? "R" : "A"}</i>
    </button>`).join("");
  $$(".sample-chip").forEach((button) => button.addEventListener("click", () => {
    state.sampleIndex = Number(button.dataset.index); renderFrame(); renderSampleStrip();
  }));
}

function seededNoise(index, seed) {
  const value = Math.sin((index + 1) * 12.9898 + seed * 78.233) * 43758.5453;
  return (value - Math.floor(value)) * 2 - 1;
}

function thermalColour(value) {
  const stops = [[3, 17, 17], [8, 52, 43], [22, 94, 69], [73, 139, 91], [198, 156, 72], [244, 219, 150]];
  const x = Math.max(0, Math.min(0.999, value)) * (stops.length - 1);
  const i = Math.floor(x); const t = x - i;
  return stops[i].map((v, channel) => Math.round(v + (stops[i + 1][channel] - v) * t));
}

function renderCanvas(sample) {
  const canvas = $("#sensor-canvas"); const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const source = document.createElement("canvas"); source.width = 64; source.height = 64;
  const sctx = source.getContext("2d", { willReadFrequently: true }); sctx.drawImage(state.image, 0, 0, 64, 64);
  const pixels = sctx.getImageData(0, 0, 64, 64); const data = pixels.data;
  const transmission = Number($("#transmission").value); const noise = Number($("#noise").value);
  const defects = Number($("#defects").value); const clutter = Number($("#clutter").value);
  const thermal = $("#thermal-palette").checked;
  for (let i = 0; i < data.length; i += 4) {
    const p = i / 4; const x = p % 64; const y = Math.floor(p / 64);
    let value = data[i] / 255;
    value = 0.5 + (value - 0.5) * transmission;
    value += noise * seededNoise(p, sample.seed);
    value += clutter * 0.14 * (Math.sin(x * 0.36 + y * 0.09) + Math.sin(y * 0.24 - x * 0.05));
    if ((seededNoise(p * 7, sample.seed + 91) + 1) / 2 < defects) value = seededNoise(p, 9) > 0 ? 1 : 0;
    value = Math.max(0, Math.min(1, value));
    const colour = thermal ? thermalColour(value) : [value * 255, value * 255, value * 255];
    data[i] = colour[0]; data[i + 1] = colour[1]; data[i + 2] = colour[2];
  }
  sctx.putImageData(pixels, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.imageSmoothingEnabled = true; ctx.filter = `blur(${$("#blur").value}px)`; ctx.drawImage(source, -10, -10, canvas.width + 20, canvas.height + 20); ctx.filter = "none";
  if ($("#show-grid").checked) {
    ctx.strokeStyle = "rgba(102, 231, 189, .055)"; ctx.lineWidth = 1;
    for (let i = 0; i <= 64; i += 4) { const pos = i / 64 * canvas.width; ctx.beginPath(); ctx.moveTo(pos, 0); ctx.lineTo(pos, canvas.height); ctx.stroke(); ctx.beginPath(); ctx.moveTo(0, pos); ctx.lineTo(canvas.width, pos); ctx.stroke(); }
  }
  const marker = (point, colour, label, radius) => {
    const x = (point[0] + .5) / 64 * canvas.width; const y = (point[1] + .5) / 64 * canvas.height;
    ctx.strokeStyle = colour; ctx.fillStyle = colour; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - radius - 7, y); ctx.lineTo(x + radius + 7, y); ctx.moveTo(x, y - radius - 7); ctx.lineTo(x, y + radius + 7); ctx.stroke();
    ctx.font = "600 13px 'IBM Plex Mono', monospace"; ctx.fillText(label, x + radius + 10, y - radius - 4);
  };
  if ($("#show-target").checked) marker(sample.target, "#62f0bc", "LATENT", 18);
  if ($("#show-peak").checked) marker(sample.peak, "#f2a955", "PEAK", 11);
}

async function renderFrame() {
  const sample = currentSample(); const meta = familyMeta[sample.family];
  const image = new Image(); image.src = sample.image; await image.decode(); state.image = image;
  renderCanvas(sample);
  $("#active-family-tag").textContent = meta.label.toUpperCase(); $("#active-seed").textContent = sample.seed;
  $("#frame-index").textContent = String(state.data.samples.indexOf(sample) + 1).padStart(2, "0"); $("#frame-total").textContent = state.data.samples.length;
  $("#truth-tag").textContent = sample.target ? "TARGET PRESENT" : "NO TARGET";
  $("#tau-readout").textContent = sample.transmission.toFixed(2); $("#psf-readout").textContent = sample.blurSigma.toFixed(2);
  $("#contrast-readout").textContent = "CONTROLLED"; $("#risk-readout").textContent = sample.qualityRisk.toFixed(3);
  const verdict = $("#frame-verdict"); verdict.textContent = `${sample.error ? "ERROR" : "CORRECT"} / ${sample.accepted ? "RELEASED" : "ABSTAINED"}`;
  verdict.className = `frame-verdict ${sample.error ? "bad" : "good"}`;
}

function curvePath(points) {
  const x = (v) => 54 + v * 636; const y = (v) => 224 - (v - .18) / .56 * 190;
  return points.map(([coverage, risk], i) => `${i ? "L" : "M"}${x(coverage).toFixed(1)},${y(risk).toFixed(1)}`).join(" ");
}

function renderRiskChart() {
  const series = state.data.studies[state.study].risk;
  const yTicks = [.2, .3, .4, .5, .6, .7]; const xTicks = [.2, .4, .6, .8, 1];
  const grid = [...yTicks.map((v) => `<line x1="54" y1="${224 - (v - .18) / .56 * 190}" x2="690" y2="${224 - (v - .18) / .56 * 190}"/><text x="45" y="${228 - (v - .18) / .56 * 190}" text-anchor="end">${v.toFixed(1)}</text>`), ...xTicks.map((v) => `<line x1="${54 + v * 636}" y1="34" x2="${54 + v * 636}" y2="224"/><text x="${54 + v * 636}" y="245" text-anchor="middle">${Math.round(v * 100)}%</text>`)].join("");
  const curves = modeOrder.map((mode, index) => { const values = series[mode]; return `<path class="curve" d="${curvePath(values.curve)}" stroke="${colours[mode]}"/><circle cx="${54 + .8 * 636}" cy="${224 - (values.curve.reduce((best, p) => Math.abs(p[0] - .8) < Math.abs(best[0] - .8) ? p : best)[1] - .18) / .56 * 190}" r="4" fill="${colours[mode]}"/><text class="aurc-label" x="675" y="${50 + index * 19}" text-anchor="end">${mode === "confidence_selective" ? "CONF" : mode === "shift_selective" ? "BLEND" : "QUALITY"} ${values.aurc.toFixed(3)}</text>`; }).join("");
  $("#risk-chart").innerHTML = `<g class="chart-grid">${grid}</g><line class="registered-line" x1="562.8" y1="34" x2="562.8" y2="224"/><text class="registered-label" x="568" y="218">REGISTERED 80%</text>${curves}`;
}

function renderFamilyMatrix() {
  const families = state.data.studies[state.study].families;
  $("#family-matrix").innerHTML = Object.entries(families).map(([key, values]) => {
    const delta = values.quality_selective.risk80 - values.confidence_selective.risk80;
    const width = Math.min(50, Math.abs(delta) * 200); const good = delta < 0;
    return `<div class="family-row"><div><b>${familyMeta[key].label}</b><small>${familyMeta[key].code}</small></div><div class="delta-track"><i class="zero"></i><span class="${good ? "good" : "bad"}" style="width:${width}%;${good ? "right:50%" : "left:50%"}"></span></div><strong class="${good ? "good" : "bad"}">${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)} pp</strong></div>`;
  }).join("");
}

function renderHypotheses() {
  $("#hypothesis-list").innerHTML = state.data.hypotheses.map((h) => `<div><span>${h.id}</span><p><b>${h.label}</b><small>${h.status === "PASS" ? "supported as registered" : "rejected / not confirmed"}</small></p><i class="${h.status.toLowerCase()}">${h.status}</i></div>`).join("");
}

function renderAll() { renderFamilyList(); renderSampleStrip(); renderFrame(); renderRiskChart(); renderFamilyMatrix(); }

function bindControls() {
  const mappings = [["transmission", "transmission-value", (v) => `${Number(v).toFixed(2)}×`], ["blur", "blur-value", (v) => `${Number(v).toFixed(1)} px`], ["noise", "noise-value", (v) => `${(Number(v) * 100).toFixed(1)}%`], ["defects", "defects-value", (v) => `${(Number(v) * 100).toFixed(2)}%`], ["clutter", "clutter-value", (v) => Number(v).toFixed(2)]];
  mappings.forEach(([inputId, outputId, format]) => $("#" + inputId).addEventListener("input", (event) => { $("#" + outputId).textContent = format(event.target.value); renderCanvas(currentSample()); }));
  ["show-target", "show-peak", "show-grid", "thermal-palette"].forEach((id) => $("#" + id).addEventListener("change", () => renderCanvas(currentSample())));
  $("#reset-controls").addEventListener("click", () => { mappings.forEach(([id, outputId, format]) => { $("#" + id).value = id === "transmission" ? 1 : 0; $("#" + outputId).textContent = format($("#" + id).value); }); renderCanvas(currentSample()); });
  $("#previous-frame").addEventListener("click", () => { const n = familySamples().length; state.sampleIndex = (state.sampleIndex - 1 + n) % n; renderSampleStrip(); renderFrame(); });
  $("#next-frame").addEventListener("click", () => { state.sampleIndex = (state.sampleIndex + 1) % familySamples().length; renderSampleStrip(); renderFrame(); });
  $$("[data-study]").forEach((button) => button.addEventListener("click", () => { state.study = button.dataset.study; $$("[data-study]").forEach((item) => item.classList.toggle("active", item === button)); renderRiskChart(); renderFamilyMatrix(); }));
}

async function init() {
  const response = await fetch(`${import.meta.env.BASE_URL}data/benchmark.json`); if (!response.ok) throw new Error("benchmark payload unavailable"); state.data = await response.json();
  state.data.samples.forEach((sample) => { sample.image = `${import.meta.env.BASE_URL}${sample.image.replace(/^\//, "")}`; });
  bindControls(); renderHypotheses(); renderAll();
  setInterval(() => { const elapsed = performance.now() - state.started; const seconds = Math.floor(elapsed / 1000); const ms = Math.floor(elapsed % 1000); $("#clock").textContent = `T+00:${String(seconds).padStart(2, "0")}.${String(ms).padStart(3, "0")}`; }, 73);
}

init().catch((error) => { document.body.innerHTML = `<pre class="fatal">IRForge audit lab failed to load\n${error.message}</pre>`; });
