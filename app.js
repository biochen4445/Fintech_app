/* ================================================================
   FinAnalyzer — Frontend Logic
   ================================================================ */

const API = "/api/analyze";
let priceChartInstance = null;

// --- DOM refs ---
const form       = document.getElementById("searchForm");
const input      = document.getElementById("tickerInput");
const searchBtn  = document.getElementById("searchBtn");
const loading    = document.getElementById("loading");
const errorBox   = document.getElementById("errorBox");
const results    = document.getElementById("results");

// --- Helpers ---
const fmt = (v, dec = 2) => (v == null ? "—" : Number(v).toFixed(dec));
const fmtBig = (v) => {
  if (v == null) return "—";
  if (v >= 1e12) return (v / 1e12).toFixed(2) + "T";
  if (v >= 1e9)  return (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6)  return (v / 1e6).toFixed(2) + "M";
  return v.toLocaleString();
};
const scoreColor = (s) => {
  if (s >= 70) return "var(--accent-green)";
  if (s >= 45) return "var(--accent-amber)";
  return "var(--accent-red)";
};

// --- Quick-ticker buttons ---
document.querySelectorAll(".quick-tick").forEach(btn => {
  btn.addEventListener("click", () => {
    input.value = btn.dataset.ticker;
    doAnalyze(btn.dataset.ticker);
  });
});

// --- Form submit ---
form.addEventListener("submit", (e) => {
  e.preventDefault();
  const ticker = input.value.trim().toUpperCase();
  if (!ticker) return;
  doAnalyze(ticker);
});

async function doAnalyze(ticker) {
  showLoading();
  try {
    const res = await fetch(`${API}/${encodeURIComponent(ticker)}`);
    const data = await res.json();
    if (!data.success) throw new Error(data.error || "Analysis failed");
    render(data);
  } catch (err) {
    showError(err.message);
  }
}

function showLoading() {
  loading.classList.add("active");
  errorBox.classList.remove("active");
  results.classList.remove("active");
  searchBtn.disabled = true;
}
function showError(msg) {
  loading.classList.remove("active");
  errorBox.textContent = "⚠ " + msg;
  errorBox.classList.add("active");
  results.classList.remove("active");
  searchBtn.disabled = false;
}

// --- Render All ---
function render(data) {
  loading.classList.remove("active");
  errorBox.classList.remove("active");
  searchBtn.disabled = false;

  renderHeader(data.stock);
  renderGauge(data.scores);
  renderScoreBars(data.scores);
  renderMetrics(data.stock);
  renderBullBear(data.bulls, data.bears);
  renderChart(data.stock.history);
  renderAgents(data.agents);

  results.classList.add("active");
  results.scrollIntoView({ behavior: "smooth", block: "start" });
}

// --- Stock Header ---
function renderHeader(s) {
  const isUp = s.change >= 0;
  document.getElementById("stockHeader").innerHTML = `
    <div>
      <div class="stock-name">${s.name}</div>
      <div class="stock-ticker">${s.ticker} · ${s.sector} · ${s.exchange}</div>
    </div>
    <div class="stock-price-group">
      <div class="stock-price">${s.currency === "TWD" ? "NT$" : "$"}${fmt(s.price)}</div>
      <div class="stock-change ${isUp ? "up" : "down"}">${isUp ? "▲" : "▼"} ${fmt(Math.abs(s.change))} (${fmt(Math.abs(s.changePct))}%)</div>
    </div>
    <div class="stock-meta">Market Cap: ${fmtBig(s.marketCap)} · Volume: ${fmtBig(s.volume)} · Beta: ${fmt(s.beta)} · Analyst: ${s.analystRating}</div>
  `;
}

// --- Gauge ---
function renderGauge(scores) {
  const s = scores.overall;
  const c = scoreColor(s);
  const circ = 2 * Math.PI * 65;
  const offset = circ - (s / 100) * circ;
  document.getElementById("gaugeContainer").innerHTML = `
    <svg class="gauge-svg" width="160" height="160" viewBox="0 0 160 160">
      <circle class="gauge-bg" cx="80" cy="80" r="65"/>
      <circle class="gauge-fill" cx="80" cy="80" r="65"
        stroke="${c}"
        stroke-dasharray="${circ}"
        stroke-dashoffset="${offset}"/>
    </svg>
    <div class="gauge-text">
      <div class="gauge-score" style="color:${c}">${s}</div>
      <div class="gauge-label">${s >= 70 ? "Bullish" : s >= 45 ? "Neutral" : "Bearish"}</div>
    </div>
  `;
}

// --- Score Bars ---
function renderScoreBars(scores) {
  const cats = [
    ["Valuation", scores.valuation],
    ["Growth", scores.growth],
    ["Profitability", scores.profitability],
    ["Health", scores.health],
    ["Technicals", scores.technicals],
    ["Dividends", scores.dividends],
  ];
  document.getElementById("scoreBars").innerHTML = cats.map(([label, val]) => `
    <div class="score-bar-item">
      <span class="score-bar-label">${label}</span>
      <div class="score-bar-track">
        <div class="score-bar-fill" style="width:${val}%;background:${scoreColor(val)}"></div>
      </div>
      <span class="score-bar-val">${val}</span>
    </div>
  `).join("");
}

// --- Metrics ---
function renderMetrics(s) {
  const items = [
    ["P/E Ratio", fmt(s.pe, 1), s.forwardPe ? `Fwd: ${fmt(s.forwardPe, 1)}` : ""],
    ["EPS", fmt(s.eps), s.forwardEps ? `Fwd: ${fmt(s.forwardEps)}` : ""],
    ["ROE", s.roe != null ? s.roe.toFixed(1) + "%" : "—", "Return on Equity"],
    ["Profit Margin", s.profitMargin != null ? s.profitMargin.toFixed(1) + "%" : "—", "Net margin"],
    ["Debt/Equity", fmt(s.debtToEquity, 0), "Leverage ratio"],
    ["Div Yield", s.dividendYield != null ? s.dividendYield.toFixed(1) + "%" : "—", "Annual yield"],
  ];
  document.getElementById("metricsGrid").innerHTML = items.map(([title, val, sub]) => `
    <div class="card">
      <div class="card-title">${title}</div>
      <div class="metric-val">${val}</div>
      <div class="metric-sub">${sub}</div>
    </div>
  `).join("");
}

// --- Bull / Bear ---
function renderBullBear(bulls, bears) {
  document.getElementById("bullBear").innerHTML = `
    <div class="card bull-card">
      <div class="bb-header bull">▲ Bullish Factors</div>
      <ul class="bb-list">${bulls.map(b => `<li>${b.text}</li>`).join("") || "<li>No strong bullish signals detected</li>"}</ul>
    </div>
    <div class="card bear-card">
      <div class="bb-header bear">▼ Bearish Factors</div>
      <ul class="bb-list">${bears.map(b => `<li>${b.text}</li>`).join("") || "<li>No major bearish signals detected</li>"}</ul>
    </div>
  `;
}

// --- Price Chart ---
function renderChart(history) {
  if (priceChartInstance) priceChartInstance.destroy();
  const ctx = document.getElementById("priceChart").getContext("2d");
  const labels = history.map(h => h.date);
  const data = history.map(h => h.close);
  const isUp = data.length > 1 && data[data.length - 1] >= data[0];
  const lineColor = isUp ? "#2ECC71" : "#E74C5F";
  const fillColor = isUp ? "rgba(46,204,113,0.08)" : "rgba(231,76,95,0.08)";

  priceChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        data,
        borderColor: lineColor,
        backgroundColor: fillColor,
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHitRadius: 10,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: {
        backgroundColor: "#151C25",
        titleColor: "#E6EDF5",
        bodyColor: "#8899AA",
        borderColor: "#1E2A3A",
        borderWidth: 1,
        titleFont: { family: "'JetBrains Mono'" },
        bodyFont: { family: "'JetBrains Mono'" },
      }},
      scales: {
        x: { grid: { color: "rgba(30,42,58,0.5)" }, ticks: { color: "#5A6B7C", maxTicksLimit: 12, font: { family: "'JetBrains Mono'", size: 10 } } },
        y: { grid: { color: "rgba(30,42,58,0.5)" }, ticks: { color: "#5A6B7C", font: { family: "'JetBrains Mono'", size: 10 } } },
      },
    },
  });
}

// --- Agents ---
function renderAgents(agents) {
  document.getElementById("agentsGrid").innerHTML = agents.map(a => `
    <div class="card agent-card">
      <div class="agent-header">
        <span class="agent-emoji">${a.emoji}</span>
        <div>
          <div class="agent-name">${a.name}</div>
          <div class="agent-style">${a.style}</div>
        </div>
      </div>
      <div class="agent-verdict verdict-${a.verdict}">${a.verdict}</div>
      <div class="agent-summary">${a.summary}</div>
      <div class="agent-points">
        ${a.pros.map(p => `<div class="agent-point pro">${p}</div>`).join("")}
        ${a.cons.map(c => `<div class="agent-point con">${c}</div>`).join("")}
      </div>
    </div>
  `).join("");
}
