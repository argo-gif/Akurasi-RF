// Demand Planning & Forecast Accuracy Dashboard App logic
const API_BASE = "http://localhost:8050/api";

let trendChartInstance = null;
let allSKUs = [];
let availablePeriods = [];
let availableGBs = [];

function formatRp(val) {
  if (val === null || val === undefined) return "Rp 0";
  if (val >= 1e12) return `Rp ${(val / 1e12).toFixed(2)} Triliun`;
  if (val >= 1e9) return `Rp ${(val / 1e9).toFixed(2)} Miliar`;
  if (val >= 1e6) return `Rp ${(val / 1e6).toFixed(2)} Juta`;
  return `Rp ${val.toLocaleString('id-ID')}`;
}

function formatQty(val) {
  if (val === null || val === undefined) return "0";
  if (Math.abs(val) >= 1e6) return `${(val / 1e6).toFixed(2)}M`;
  if (Math.abs(val) >= 1e3) return `${(val / 1e3).toFixed(1)}K`;
  return val.toLocaleString('id-ID');
}

document.addEventListener("DOMContentLoaded", () => {
  initDashboard();

  document.getElementById("btn-refresh").addEventListener("click", () => {
    initDashboard(true);
  });

  document.getElementById("filter-period-global").addEventListener("change", () => {
    loadSummary();
    loadMatrix();
    filterAndRenderSKUs();
  });

  document.getElementById("filter-gb-global").addEventListener("change", () => {
    loadSummary();
    loadMatrix();
    filterAndRenderSKUs();
  });

  document.getElementById("search-sku").addEventListener("input", filterAndRenderSKUs);
  document.getElementById("filter-quadrant").addEventListener("change", filterAndRenderSKUs);
});

async function initDashboard(forceReprocess = false) {
  const statusElem = document.getElementById("api-status");
  statusElem.innerText = forceReprocess ? "Reprocessing Data..." : "Loading Data...";

  try {
    const url = forceReprocess ? `${API_BASE}/reprocess` : `${API_BASE}/options`;
    const res = await fetch(url);
    const data = await res.json();

    if (data.status === "success" || data.status === "ok") {
      statusElem.innerText = "API Backend Connected";

      if (data.periods) {
        populatePeriodDropdown("filter-period-global", data.periods);
      }
      if (data.gbs) {
        populateDropdown("filter-gb-global", data.gbs, "Semua Group Barang (GB)");
      }

      loadSummary();
      loadMatrix();
      await loadSKUs();
      loadTrend();
    } else {
      statusElem.innerText = "API Response Error";
    }
  } catch (err) {
    console.error("API Connection Failed:", err);
    statusElem.innerText = "Offline / Connection Failed";
  }
}

function populatePeriodDropdown(elemId, periods) {
  const elem = document.getElementById(elemId);
  const currentVal = elem.value;
  elem.innerHTML = "";

  const optAll = document.createElement("option");
  optAll.value = "";
  optAll.innerText = "Semua Periode (2025 & 2026 YTD)";
  elem.appendChild(optAll);

  const yearMap = {};
  periods.forEach(p => {
    const y = p.split("-")[0];
    if (!yearMap[y]) yearMap[y] = [];
    yearMap[y].push(p);
  });

  const sortedYears = Object.keys(yearMap).sort();

  const ogYear = document.createElement("optgroup");
  ogYear.label = "📊 RINGKASAN TAHUNAN";
  sortedYears.forEach(y => {
    const opt = document.createElement("option");
    opt.value = y;
    opt.innerText = `Full Year ${y} (YTD ${y})`;
    ogYear.appendChild(opt);
  });
  elem.appendChild(ogYear);

  sortedYears.forEach(y => {
    const og = document.createElement("optgroup");
    og.label = `📅 PERIODE BULANAN TAHUN ${y}`;
    yearMap[y].forEach(p => {
      const opt = document.createElement("option");
      opt.value = p;
      opt.innerText = p;
      og.appendChild(opt);
    });
    elem.appendChild(og);
  });

  if (currentVal) {
    elem.value = currentVal;
  }
}

function populateDropdown(elemId, items, defaultLabel) {
  const elem = document.getElementById(elemId);
  const currentVal = elem.value;
  elem.innerHTML = `<option value="">${defaultLabel}</option>`;
  items.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.innerText = item;
    elem.appendChild(opt);
  });
  elem.value = currentVal;
}

function formatAccuracy(val) {
  if (val === null || val === undefined) return "N/A";
  const num = parseFloat(val);
  if (isNaN(num)) return "N/A";
  if (num > 100 || num < 0) return "0%";
  return `${num.toFixed(2)}%`;
}

function getAccColor(val, defaultLowColor = 'var(--accent-rose)') {
  if (val === null || val === undefined) return 'var(--text-muted)';
  return val > 50 ? 'var(--accent-emerald)' : defaultLowColor;
}

// 1. Load Executive Summary
async function loadSummary() {
  try {
    const selectedPeriod = document.getElementById("filter-period-global").value;
    const selectedGB = document.getElementById("filter-gb-global").value;

    let url = `${API_BASE}/summary?`;
    if (selectedPeriod) url += `periode=${encodeURIComponent(selectedPeriod)}&`;
    if (selectedGB) url += `gb=${encodeURIComponent(selectedGB)}&`;

    const res = await fetch(url);
    const json = await res.json();
    if (json.status === "success") {
      const s = json.data;
      document.getElementById("kpi-wafe").innerText = formatAccuracy(s.wafe_accuracy);
      document.getElementById("kpi-wafe").style.color = getAccColor(s.wafe_accuracy, 'var(--accent-rose)');
      document.getElementById("kpi-mape").innerText = formatAccuracy(s.mape_accuracy);
      document.getElementById("kpi-mape").style.color = getAccColor(s.mape_accuracy, 'var(--accent-cyan)');

      const biasVal = s.total_bias_qty;
      const biasText = formatQty(biasVal);
      document.getElementById("kpi-bias").innerText = `${biasText} Qty`;
      document.getElementById("bias-label").innerText = biasVal > 0 ? "Over-Forecast (Kelebihan Stock)" : "Under-Forecast (Risiko Stockout)";

      document.getElementById("kpi-var").innerText = formatRp(s.value_at_risk_rp);
    }
  } catch (e) {
    console.error("Error loading summary:", e);
  }
}

// 2. Load Matrix 4-Kuadran atau 2-Kartu Nasional (Pareto Per GB atau Nasional)
async function loadMatrix() {
  try {
    const selectedPeriod = document.getElementById("filter-period-global").value;
    const selectedGB = document.getElementById("filter-gb-global").value;
    let url = `${API_BASE}/matrix?`;
    if (selectedPeriod) url += `periode=${encodeURIComponent(selectedPeriod)}&`;
    if (selectedGB) url += `gb=${encodeURIComponent(selectedGB)}&`;

    const res = await fetch(url);
    const json = await res.json();
    if (json.status === "success") {
      const m = json.data;
      const container = document.getElementById("matrix-container");
      container.innerHTML = "";

      const isNational = !selectedGB;
      updateQuadrantDropdown(isNational);

      const quadConfigs = [
        { key: "MTM - Pareto", title: "MTM - Pareto", class: "quad-mtm-pareto", badgeClass: "badge-cyan", desc: "Top 80% Value (Make-to-Order Kontributor Utama)" },
        { key: "MTM - Non-Pareto", title: "MTM - Non-Pareto", class: "quad-mtm-non-pareto", badgeClass: "badge-blue", desc: "Bottom 20% Value (Make-to-Order Long Tail)" },
        { key: "Non-MTM - Pareto", title: "Non-MTM - Pareto", class: "quad-non-mtm-pareto", badgeClass: "badge-amber", desc: "Top 80% Value (Reguler High Volume)" },
        { key: "Non-MTM - Non-Pareto", title: "Non-MTM - Non-Pareto", class: "quad-non-mtm-non-pareto", badgeClass: "badge-gray", desc: "Bottom 20% Value (Reguler Slow Moving)" }
      ];

      quadConfigs.forEach(conf => {
        const item = m[conf.key] || { sku_count: 0, actual_qty: 0, rf_qty: 0, rf_val_rp: 0, error_val_rp: 0, wafe_accuracy: null, mape_accuracy: null };
        const formattedWafe = formatAccuracy(item.wafe_accuracy);
        const formattedMape = formatAccuracy(item.mape_accuracy);
        const wafeColor = getAccColor(item.wafe_accuracy, 'var(--accent-rose)');
        const mapeColor = getAccColor(item.mape_accuracy, 'var(--accent-cyan)');
        const cardHtml = `
          <div class="quad-card ${conf.class}" style="cursor: pointer;" onclick="filterByTotalCard('${conf.key}')" title="Klik untuk filter tabel SKU">
            <div class="quad-header">
              <div>
                <div class="quad-title">${conf.title}</div>
                <div style="font-size:0.78rem; color: var(--text-muted);">${conf.desc}</div>
              </div>
              <span class="quad-badge ${conf.badgeClass}">${item.sku_count} SKUs</span>
            </div>
            <div class="quad-metrics">
              <div class="metric-item">
                <div class="metric-label">WAFE ACCURACY (MARGIN RP)</div>
                <div class="metric-val" style="color: ${wafeColor};">${formattedWafe}</div>
              </div>
              <div class="metric-item">
                <div class="metric-label">MAPE ACCURACY (VOLUME)</div>
                <div class="metric-val" style="color: ${mapeColor};">${formattedMape}</div>
              </div>
            </div>
          </div>
        `;
        container.insertAdjacentHTML("beforeend", cardHtml);
      });

      // Render totals summary grid
      const totalsContainer = document.getElementById("totals-container");
      if (totalsContainer && json.totals) {
        totalsContainer.innerHTML = "";
        const totalsConfig = [
          { key: "Total MTM", title: "TOTAL MTM", desc: "Akurasi Seluruh SKU Make-to-Order", icon: "fa-boxes-stacked", colorClass: "icon-blue" },
          { key: "Total NON-MTM", title: "TOTAL NON-MTM", desc: "Akurasi Seluruh SKU Reguler / Non MTM", icon: "fa-boxes-packing", colorClass: "icon-purple" },
          { key: "Total Pareto", title: "TOTAL PARETO", desc: "Akurasi Seluruh Top 80% Value", icon: "fa-trophy", colorClass: "icon-amber" },
          { key: "Total Non-Pareto", title: "TOTAL NON-PARETO", desc: "Akurasi Seluruh Bottom 20% Value", icon: "fa-chart-pie", colorClass: "icon-rose" }
        ];

        totalsConfig.forEach(conf => {
          const tItem = json.totals[conf.key] || { sku_count: 0, wafe_accuracy: null, mape_accuracy: null };
          const formattedWafe = formatAccuracy(tItem.wafe_accuracy);
          const formattedMape = formatAccuracy(tItem.mape_accuracy);
          const wafeColor = getAccColor(tItem.wafe_accuracy, 'var(--accent-rose)');
          const mapeColor = getAccColor(tItem.mape_accuracy, 'var(--accent-cyan)');
          const cardHtml = `
            <div class="kpi-card" style="cursor: pointer;" onclick="filterByTotalCard('${conf.key}')" title="Klik untuk filter tabel SKU">
              <div class="kpi-header">
                <span>${conf.title}</span>
                <div class="kpi-icon ${conf.colorClass}"><i class="fa-solid ${conf.icon}"></i></div>
              </div>
              <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                <span class="quad-badge badge-gray" style="font-size:0.8rem;">${tItem.sku_count} SKUs</span>
              </div>
              <div class="quad-metrics" style="margin-top: 10px;">
                <div class="metric-item">
                  <div class="metric-label">WAFE ACCURACY</div>
                  <div class="metric-val" style="font-size:1.15rem; color: ${wafeColor};">${formattedWafe}</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">MAPE ACCURACY</div>
                  <div class="metric-val" style="font-size:1.15rem; color: ${mapeColor};">${formattedMape}</div>
                </div>
              </div>
              <div class="kpi-subtitle" style="margin-top: 8px;">${conf.desc}</div>
            </div>
          `;
          totalsContainer.insertAdjacentHTML("beforeend", cardHtml);
        });
      }
    }
  } catch (e) {
    console.error("Error loading matrix:", e);
  }
}

function filterByTotalCard(key) {
  const quadElem = document.getElementById("filter-quadrant");
  if (quadElem) {
    quadElem.value = key;
    filterAndRenderSKUs();
    const tableElem = document.querySelector(".table-section");
    if (tableElem) {
      tableElem.scrollIntoView({ behavior: "smooth" });
    }
  }
}

function updateQuadrantDropdown(isNational) {
  const quadElem = document.getElementById("filter-quadrant");
  if (!quadElem) return;
  const current = quadElem.value;
  quadElem.innerHTML = `
    <option value="">Semua Kuadran / Totals</option>
    <option value="MTM - Pareto">MTM - Pareto</option>
    <option value="MTM - Non-Pareto">MTM - Non-Pareto</option>
    <option value="Non-MTM - Pareto">Non-MTM - Pareto</option>
    <option value="Non-MTM - Non-Pareto">Non-MTM - Non-Pareto</option>
    <option value="Total MTM">Total MTM (Semua MTM)</option>
    <option value="Total NON-MTM">Total NON-MTM (Semua Non-MTM)</option>
    <option value="Total Pareto">Total Pareto (Semua Pareto)</option>
    <option value="Total Non-Pareto">Total Non-Pareto (Semua Non-Pareto)</option>
  `;
  quadElem.value = current;
}

// 3. Load Trend & Render Chart.js
async function loadTrend() {
  try {
    const res = await fetch(`${API_BASE}/trend`);
    const json = await res.json();
    if (json.status === "success") {
      // Filter hanya periode yang memiliki data Rolling Forecast (rf_val_rp > 0)
      const trendData = json.data.filter(t => t.rf_val_rp > 0);
      const labels = trendData.map(t => t.periode || "Periode");
      const wafeAccs = trendData.map(t => t.wafe_accuracy);
      const mapeAccs = trendData.map(t => t.mape_accuracy);

      const chartDataLabelsPlugin = {
        id: 'customDatalabels',
        afterDatasetsDraw(chart) {
          const { ctx } = chart;
          chart.data.datasets.forEach((dataset, datasetIndex) => {
            const meta = chart.getDatasetMeta(datasetIndex);
            if (!meta.hidden) {
              meta.data.forEach((element, index) => {
                const val = dataset.data[index];
                if (val !== null && val !== undefined) {
                  const text = `${val.toFixed(2)}%`;
                  ctx.save();
                  ctx.fillStyle = dataset.borderColor;
                  ctx.font = '600 11px Outfit, sans-serif';
                  ctx.textAlign = 'center';
                  ctx.textBaseline = datasetIndex === 0 ? 'bottom' : 'top';
                  const yOffset = datasetIndex === 0 ? -8 : 8;
                  ctx.fillText(text, element.x, element.y + yOffset);
                  ctx.restore();
                }
              });
            }
          });
        }
      };

      const ctx = document.getElementById("trendChart").getContext("2d");
      if (trendChartInstance) {
        trendChartInstance.destroy();
      }

      trendChartInstance = new Chart(ctx, {
        type: 'line',
        plugins: [chartDataLabelsPlugin],
        data: {
          labels: labels,
          datasets: [
            {
              label: 'WAFE Accuracy (Margin Rp %)',
              data: wafeAccs,
              borderColor: '#00f2fe',
              backgroundColor: 'rgba(0, 242, 254, 0.1)',
              fill: false,
              tension: 0.3,
              borderWidth: 3,
              pointBackgroundColor: '#00f2fe',
              pointRadius: 5
            },
            {
              label: 'MAPE Accuracy (Volume Qty %)',
              data: mapeAccs,
              borderColor: '#a855f7',
              backgroundColor: 'rgba(168, 85, 247, 0.1)',
              fill: false,
              tension: 0.3,
              borderWidth: 3,
              pointBackgroundColor: '#a855f7',
              pointRadius: 5
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              labels: { color: '#94a3b8', font: { family: 'Outfit', size: 13 } }
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
                }
              }
            }
          },
          scales: {
            x: {
              ticks: { color: '#94a3b8' },
              grid: { color: 'rgba(255,255,255,0.05)' }
            },
            y: {
              min: 0,
              max: 100,
              ticks: {
                color: '#94a3b8',
                callback: function(value) { return value + '%'; }
              },
              grid: { color: 'rgba(255,255,255,0.05)' }
            }
          }
        }
      });
    }
  } catch (e) {
    console.error("Error loading trend:", e);
  }
}

// 4. Load & Filter SKUs Table
async function loadSKUs() {
  try {
    const res = await fetch(`${API_BASE}/skus`);
    const json = await res.json();
    if (json.status === "success") {
      allSKUs = json.data;
      filterAndRenderSKUs();
    }
  } catch (e) {
    console.error("Error loading SKUs:", e);
  }
}

function filterAndRenderSKUs() {
  const query = document.getElementById("search-sku").value.toLowerCase().trim();
  const quadFilter = document.getElementById("filter-quadrant").value;
  const gbFilter = document.getElementById("filter-gb-global").value;
  const selectedPeriod = document.getElementById("filter-period-global").value;
  let filtered = allSKUs;

  if (selectedPeriod) {
    filtered = filtered.filter(s => s.periods && s.periods[selectedPeriod] && (s.periods[selectedPeriod].rf_qty || 0) > 0);
  } else {
    filtered = filtered.filter(s => (s.total_rf_qty || 0) > 0);
  }

  if (quadFilter) {
    filtered = filtered.filter(s => (s.quadrant || "").toLowerCase() === quadFilter.toLowerCase());
  }

  if (gbFilter) {
    filtered = filtered.filter(s => (s.gb || "").toLowerCase() === gbFilter.toLowerCase());
  }

  if (query) {
    filtered = filtered.filter(s => 
      (s.product_code || "").toLowerCase().includes(query) ||
      (s.product_name || "").toLowerCase().includes(query) ||
      (s.old_code || "").toLowerCase().includes(query)
    );
  }

  const tbody = document.getElementById("sku-table-body");
  tbody.innerHTML = "";

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color: var(--text-muted);">Tidak ada SKU yang cocok.</td></tr>`;
    return;
  }

  filtered.slice(0, 100).forEach(sku => {
    let actQty = sku.total_actual_qty;
    let rfQty = sku.total_rf_qty;
    let errQty = sku.total_error_qty;
    let errVal = sku.total_error_val;
    let mapeVal = sku.overall_mape;

    if (selectedPeriod && sku.periods && sku.periods[selectedPeriod]) {
      const p = sku.periods[selectedPeriod];
      actQty = p.act_qty;
      rfQty = p.rf_qty;
      errQty = p.error_qty;
      errVal = p.error_val;
      mapeVal = p.mape;
    }

    const mapeText = mapeVal !== null && mapeVal !== undefined ? `${mapeVal}%` : '-';
    let mapeAccText = '-';
    let accStyle = '';
    if (mapeVal !== null && mapeVal !== undefined) {
      let rawAcc = 100.0 - mapeVal;
      let acc = (rawAcc > 100 || rawAcc < 0) ? 0 : rawAcc;
      mapeAccText = `${acc.toFixed(2)}%`;
      if (acc >= 75) accStyle = 'color: var(--accent-cyan); font-weight: 600;';
      else if (acc < 50) accStyle = 'color: var(--accent-rose); font-weight: 600;';
      else accStyle = 'font-weight: 600;';
    }

    const tr = `
      <tr>
        <td class="sku-code">${sku.product_code}</td>
        <td>${sku.product_name}</td>
        <td><span class="quad-badge badge-gray">${sku.gb}</span></td>
        <td><span class="quad-badge badge-blue">${sku.quadrant || 'N/A'}</span></td>
        <td class="text-right">${formatQty(actQty)}</td>
        <td class="text-right">${formatQty(rfQty)}</td>
        <td class="text-right">${formatQty(errQty)}</td>
        <td class="text-right" style="color: var(--accent-rose);">${formatRp(errVal)}</td>
        <td class="text-right">${mapeText}</td>
        <td class="text-right" style="${accStyle}">${mapeAccText}</td>
      </tr>
    `;
    tbody.insertAdjacentHTML("beforeend", tr);
  });
}
