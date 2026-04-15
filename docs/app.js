"use strict";

const SOURCE_CLASSES = {
  Amazon: "amazon",
  eBay: "ebay",
  AliExpress: "aliexpress",
  "Google Trends": "google-trends",
  Reddit: "reddit",
};

const SOURCE_COLORS = {
  Amazon: "#ff9900",
  eBay: "#86b817",
  AliExpress: "#e43226",
  "Google Trends": "#4285f4",
  Reddit: "#ff4500",
};

let allProducts = [];
let catChartInst = null;
let srcChartInst = null;

// ── Helpers ──────────────────────────────────────────────────────────────────

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString("en-GB", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit", timeZoneName: "short",
    });
  } catch {
    return iso;
  }
}

function srcClass(src) {
  return SOURCE_CLASSES[src] ?? "default";
}

function priceNum(p) {
  const m = String(p).match(/[\d,.]+/);
  return m ? parseFloat(m[0].replace(/,/g, "")) : 0;
}

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadData() {
  try {
    const res = await fetch(`./data.json?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    init(data);
  } catch (err) {
    document.getElementById("grid").innerHTML = `
      <div class="state-msg">
        Could not load product data.<br>
        <small style="color:#8b949e">${esc(err.message)}</small><br><br>
        <small>The GitHub Action may not have run yet. Go to your repo → Actions tab → run it manually.</small>
      </div>`;
  }
}

// ── Initialise ───────────────────────────────────────────────────────────────

function init(data) {
  // Header meta
  document.getElementById("last-updated").textContent = fmtDate(data.last_updated);

  const statusEl = document.getElementById("source-statuses");
  statusEl.innerHTML = Object.entries(data.sources ?? {})
    .map(([name, info]) => {
      const ok = info.status === "success";
      return `<span class="src-pill ${ok ? "ok" : "err"}" title="${esc(name)}: ${info.count ?? 0} products">
        ${esc(name.replace("_", " "))} ${ok ? "✓" : "✗"}
      </span>`;
    })
    .join("");

  allProducts = data.products ?? [];

  // Stats
  document.getElementById("stat-total").textContent = allProducts.length;

  const activeSrc = Object.values(data.sources ?? {}).filter(s => s.status === "success").length;
  document.getElementById("stat-sources").textContent = activeSrc;

  const multi = allProducts.filter(p => (p.sources ?? []).length > 1).length;
  document.getElementById("stat-multi").textContent = multi;

  const catCount = {};
  allProducts.forEach(p => { catCount[p.category] = (catCount[p.category] ?? 0) + 1; });
  const topCat = Object.entries(catCount).sort((a, b) => b[1] - a[1])[0];
  document.getElementById("stat-top-cat").textContent = topCat ? topCat[0] : "—";

  // Category filter options
  const catSel = document.getElementById("fCat");
  [...new Set(allProducts.map(p => p.category))].sort().forEach(cat => {
    const o = document.createElement("option");
    o.value = cat;
    o.textContent = cat;
    catSel.appendChild(o);
  });

  buildCharts(allProducts);
  applyFilters();
}

// ── Charts ───────────────────────────────────────────────────────────────────

const CHART_DEFAULTS = {
  plugins: { legend: { display: false } },
  animation: { duration: 600 },
};

const GRID_STYLE = {
  color: "rgba(48,54,61,1)",
};

function buildCharts(products) {
  // Category bar chart
  const catCount = {};
  products.forEach(p => { catCount[p.category] = (catCount[p.category] ?? 0) + 1; });
  const sortedCats = Object.entries(catCount).sort((a, b) => b[1] - a[1]).slice(0, 12);

  if (catChartInst) catChartInst.destroy();
  catChartInst = new Chart(document.getElementById("catChart").getContext("2d"), {
    type: "bar",
    data: {
      labels: sortedCats.map(([k]) => k),
      datasets: [{
        data: sortedCats.map(([, v]) => v),
        backgroundColor: "rgba(247,129,102,.75)",
        borderColor: "#f78166",
        borderWidth: 1,
        borderRadius: 5,
      }],
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        x: { ticks: { color: "#8b949e", font: { size: 10 } }, grid: GRID_STYLE },
        y: { ticks: { color: "#8b949e" }, grid: GRID_STYLE },
      },
    },
  });

  // Source doughnut chart
  const srcCount = {};
  products.forEach(p => {
    (p.sources ?? [p.source]).forEach(s => {
      srcCount[s] = (srcCount[s] ?? 0) + 1;
    });
  });

  if (srcChartInst) srcChartInst.destroy();
  srcChartInst = new Chart(document.getElementById("srcChart").getContext("2d"), {
    type: "doughnut",
    data: {
      labels: Object.keys(srcCount),
      datasets: [{
        data: Object.values(srcCount),
        backgroundColor: Object.keys(srcCount).map(s => SOURCE_COLORS[s] ?? "#666"),
        borderColor: "#1c2128",
        borderWidth: 2,
        hoverOffset: 8,
      }],
    },
    options: {
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: { color: "#8b949e", padding: 10, font: { size: 11 }, boxWidth: 12 },
        },
      },
      animation: { duration: 600 },
    },
  });
}

// ── Filtering & sorting ───────────────────────────────────────────────────────

function applyFilters() {
  const q    = document.getElementById("q").value.toLowerCase().trim();
  const cat  = document.getElementById("fCat").value;
  const src  = document.getElementById("fSrc").value;
  const sort = document.getElementById("fSort").value;

  let list = allProducts.filter(p => {
    if (q   && !p.name.toLowerCase().includes(q)) return false;
    if (cat && p.category !== cat)                return false;
    if (src && !(p.sources ?? [p.source]).includes(src)) return false;
    return true;
  });

  if (sort === "sources")    list.sort((a, b) => (b.sources?.length ?? 0) - (a.sources?.length ?? 0));
  else if (sort === "price_asc")  list.sort((a, b) => priceNum(a.price) - priceNum(b.price));
  else if (sort === "price_desc") list.sort((a, b) => priceNum(b.price) - priceNum(a.price));
  else                            list.sort((a, b) => b.score - a.score);

  document.getElementById("result-count").textContent = list.length;
  renderGrid(list);
}

// ── Rendering ────────────────────────────────────────────────────────────────

function renderGrid(products) {
  const grid = document.getElementById("grid");

  if (!products.length) {
    grid.innerHTML = '<div class="state-msg">No products match your filters.</div>';
    return;
  }

  const maxScore = Math.max(...products.map(p => p.score), 1);

  grid.innerHTML = products.map((p, i) => {
    const sources   = p.sources ?? [p.source];
    const pct       = Math.min(100, (p.score / maxScore) * 100).toFixed(0);
    const isTop3    = (p.rank ?? i + 1) <= 3;
    const rankLabel = p.rank ?? i + 1;

    const imgTag = p.image
      ? `<img class="product-img" src="${esc(p.image)}" alt="${esc(p.name)}" loading="lazy"
             onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">`
      : "";

    const phStyle = p.image ? 'style="display:none"' : "";

    const badges = sources
      .map(s => `<span class="src-badge ${srcClass(s)}">${esc(s)}</span>`)
      .join("");

    const rankChange = p.rank_change
      ? `<div class="rank-change">${esc(p.rank_change)}</div>`
      : "";

    return `
      <div class="product-card" onclick="open('${esc(p.url)}')">
        <span class="rank-badge ${isTop3 ? "gold" : ""}">#${rankLabel}</span>
        <div class="product-img-wrap">
          ${imgTag}
          <div class="product-img-ph" ${phStyle}>📦</div>
        </div>
        <div class="product-info">
          <div class="product-name" title="${esc(p.name)}">${esc(p.name)}</div>
          <div class="product-meta">
            <div class="product-price">${esc(p.price)}</div>
            <div class="score-wrap">
              <div class="score-bar"><div class="score-fill" style="width:${pct}%"></div></div>
              <span>${Math.round(p.score)}</span>
            </div>
          </div>
          <div class="sources">${badges}</div>
          ${rankChange}
          <div class="product-cat">${esc(p.category)}</div>
        </div>
      </div>`;
  }).join("");
}

// ── Event listeners ───────────────────────────────────────────────────────────

document.getElementById("q").addEventListener("input", applyFilters);
document.getElementById("fCat").addEventListener("change", applyFilters);
document.getElementById("fSrc").addEventListener("change", applyFilters);
document.getElementById("fSort").addEventListener("change", applyFilters);

// ── Bootstrap ────────────────────────────────────────────────────────────────

loadData();
