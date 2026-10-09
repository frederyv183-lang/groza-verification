// === Аналитика: гистограммы + матрицы по годам ===
const API = "/api/analytics";

const LABELS = {
    "k_index_v1": "K-индекс (K ≥ 22)",
    "k_strict_v1": "K-индекс строгий (K ≥ 25)",
    "faust_v1": "Метод Фауста (T_v > 0)",
    "k_and_faust": "K + Фауст",
    "reshetov_v1": "Решетов (v1)",
    "reshetov_v2": "Решетов (v2, мягкий)",
    "fateev_v1": "Фатеев (A ≥ 5)",
    "lebedev_v1": "Лебедева",
    "bailey_v1": "Бейли",
    "yagudin_v1": "Ягудин",
    "ki_index_v2": "K-индекс v2",
};

const COLORS = {
    "k_index_v1": "#c4b5fd",
    "k_strict_v1": "#34d399",
    "faust_v1": "#f87171",
    "k_and_faust": "#60a5fa",
    "reshetov_v1": "#fbbf24",
    "reshetov_v2": "#f59e0b",
    "fateev_v1": "#c084fc",
    "lebedev_v1": "#22d3ee",
    "bailey_v1": "#a3a3a3",
    "yagudin_v1": "#fb7185",
    "ki_index_v2": "#4ade80",
};

const SYMBOLS = {
    "k_index_v1": "circle",
    "k_strict_v1": "square",
    "faust_v1": "triangle-up",
    "k_and_faust": "diamond",
    "reshetov_v1": "cross",
    "reshetov_v2": "x",
    "fateev_v1": "star",
    "lebedev_v1": "pentagon",
    "bailey_v1": "hexagon",
};

let DATA = null;
let CURRENT_MODEL = null;

function label(id) { return LABELS[id] || id; }
function color(id) { return COLORS[id] || "#a78bfa"; }

async function loadByYear() {
    try {
        const r = await fetch(`${API}/by-year`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        DATA = await r.json();

        // Скрываем загрузку
        document.getElementById("loading").style.display = "none";
        document.getElementById("content").style.display = "block";

        // Первая модель = лучшая
        CURRENT_MODEL = DATA.models[0];

        renderCharts();
        renderSummary();
        renderModelSelector();
        await loadMatrices(CURRENT_MODEL);
    } catch (e) {
        document.getElementById("loading").innerHTML =
            `<p style="color:#f87171">Ошибка загрузки: ${e.message}</p>`;
    }
}

function renderCharts() {
    const years = DATA.years;
    const models = DATA.models;

    const charts = {
        pod: { metric: "POD", yRange: [0, 1] },
        far: { metric: "FAR", yRange: [0, 1] },
        csi: { metric: "CSI", yRange: [0, 0.6] },
        hk:  { metric: "HK",  yRange: [0, 1] },
    };

    for (const [key, cfg] of Object.entries(charts)) {
        const traces = models.map(model => {
            const perYear = DATA.data[model] || {};
            const y = years.map(yr => {
                const d = perYear[String(yr)];
                return d ? d[cfg.metric] : null;
            });
            return {
                x: years, y: y,
                type: "scatter", mode: "lines+markers",
                name: label(model),
                line: { color: color(model), width: 2.5 },
                marker: { size: 10, symbol: SYMBOLS[model] || "circle",
                          color: color(model),
                          line: { color: "#1a1130", width: 2 } },
                connectgaps: false,
                hovertemplate: "<b>%{fullData.name}</b><br>%{x}: %{y:.3f}<extra></extra>",
            };
        });

        const layout = {
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(15, 10, 30, 0.4)",
            font: { color: "#f0ecff", family: "Inter, sans-serif", size: 12 },
            xaxis: {
                title: { text: "Год", font: { size: 12, color: "#a89bc4" } },
                gridcolor: "rgba(139, 92, 246, 0.1)",
                tickmode: "array", tickvals: years,
                tickfont: { size: 12, color: "#a89bc4" },
            },
            yaxis: {
                title: { text: cfg.metric, font: { size: 12, color: "#a89bc4" } },
                gridcolor: "rgba(139, 92, 246, 0.1)",
                range: cfg.yRange,
                tickfont: { color: "#a89bc4" },
            },
            legend: {
                orientation: "h", y: -0.25,
                font: { color: "#f0ecff", size: 11 },
                bgcolor: "rgba(26, 17, 48, 0.8)",
                bordercolor: "rgba(139, 92, 246, 0.3)",
                borderwidth: 1,
            },
            margin: { l: 55, r: 25, t: 25, b: 90 },
            height: 340,
            hovermode: "x unified",
        };

        Plotly.newPlot(`chart-${key}`, traces, layout, { displayModeBar: false });
    }
}

function renderSummary() {
    const years = DATA.years;
    const models = DATA.models;
    const tbody = document.getElementById("summary-tbody");

    const yearBest = {}, yearWorst = {};
    for (const yr of years) {
        let best = -Infinity, worst = Infinity;
        for (const m of models) {
            const d = DATA.data[m]?.[String(yr)];
            if (!d) continue;
            best = Math.max(best, d.CSI);
            worst = Math.min(worst, d.CSI);
        }
        yearBest[yr] = best;
        yearWorst[yr] = worst;
    }

    tbody.innerHTML = models.map(m => {
        const perYear = DATA.data[m] || {};
        let sum = 0, count = 0;
        const cells = years.map(yr => {
            const d = perYear[String(yr)];
            if (!d) return "<td>—</td>";
            sum += d.CSI; count += 1;
            let cls = "";
            if (Math.abs(d.CSI - yearBest[yr]) < 0.001) cls = "cell-best";
            else if (Math.abs(d.CSI - yearWorst[yr]) < 0.001) cls = "cell-worst";
            return `<td class="${cls}">${d.CSI.toFixed(3)}</td>`;
        }).join("");
        const avg = count ? (sum / count).toFixed(3) : "—";
        return `<tr>
            <td><strong style="color:${color(m)}">${label(m)}</strong><br>
                <small style="color:var(--text-muted);font-size:0.7em">${m}</small></td>
            ${cells}
            <td><strong>${avg}</strong></td>
        </tr>`;
    }).join("");
}

function renderModelSelector() {
    const selector = document.getElementById("model-selector");
    selector.innerHTML = DATA.models.map(m => `
        <button class="model-btn ${m === CURRENT_MODEL ? "active" : ""}"
                data-model="${m}">${label(m)}</button>
    `).join("");

    selector.querySelectorAll(".model-btn").forEach(btn => {
        btn.addEventListener("click", () => selectModel(btn.dataset.model));
    });
}

function selectModel(model) {
    CURRENT_MODEL = model;
    document.querySelectorAll(".model-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.model === model);
    });
    loadMatrices(model);
}

async function loadMatrices(model) {
    const grid = document.getElementById("matrices-grid");
    grid.innerHTML = "<p style='color:var(--text-muted)'>Загрузка матриц...</p>";
    try {
        const r = await fetch(`${API}/matrices?model=${model}`);
        const data = await r.json();
        if (!data.years || data.years.length === 0) {
            grid.innerHTML = "<p>Нет данных</p>";
            return;
        }
        grid.innerHTML = data.years.map(y => `
            <div class="matrix-card">
                <h4>${y.year} год</h4>
                <div class="matrix-metrics">
                    <span class="mm-item"><span class="mm-key">POD</span> ${y.POD.toFixed(2)}</span>
                    <span class="mm-item"><span class="mm-key">FAR</span> ${y.FAR.toFixed(2)}</span>
                    <span class="mm-item"><span class="mm-key">CSI</span> ${y.CSI.toFixed(2)}</span>
                </div>
                <table class="confusion">
                    <thead>
                        <tr><th></th><th>Факт: гроза</th><th>Факт: нет</th></tr>
                    </thead>
                    <tbody>
                        <tr><th>Прогноз: гроза</th>
                            <td class="cell-hit">${y.hits}</td>
                            <td class="cell-fa">${y.false_alarms}</td></tr>
                        <tr><th>Прогноз: нет</th>
                            <td class="cell-miss">${y.misses}</td>
                            <td class="cell-cn">${y.correct_negatives}</td></tr>
                    </tbody>
                </table>
                <p class="matrix-note">Всего сроков: ${y.n}</p>
            </div>
        `).join("");
    } catch (e) {
        grid.innerHTML = `<p style="color:var(--far-color)">Ошибка: ${e.message}</p>`;
    }
}

document.addEventListener("DOMContentLoaded", loadByYear);
