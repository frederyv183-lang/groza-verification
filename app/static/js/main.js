// === Грозпроверка: живые метрики + таблица моделей ===
const API = "/api";

const LABELS = {
    "k_index_v1": "K-индекс (K ≥ 22)",
    "k_strict_v1": "K-индекс строгий (K ≥ 25)",
    "faust_v1": "Метод Фауста (T_v > 0)",
    "k_and_faust": "K + Фауст",
    "reshetov_v1": "Метод Решетова",
};

function label(id) { return LABELS[id] || id; }

async function loadMetrics() {
    try {
        const r = await fetch(`${API}/metrics/calculate?model=k_index_v1`);
        const data = await r.json();
        const m = data.metrics || {};
        document.getElementById("pod").textContent = m.POD?.toFixed(3) ?? "—";
        document.getElementById("far").textContent = m.FAR?.toFixed(3) ?? "—";
        document.getElementById("csi").textContent = m.CSI?.toFixed(3) ?? "—";
        document.getElementById("hk").textContent  = m.HK?.toFixed(3)  ?? "—";
        const c = data.confusion || {};
        document.getElementById("cm-h").textContent = c.H ?? "—";
        document.getElementById("cm-f").textContent = c.F ?? "—";
        document.getElementById("cm-m").textContent = c.M ?? "—";
        document.getElementById("cm-c").textContent = c.C ?? "—";
    } catch (e) { console.error("Метрики:", e); }
}

async function loadModels() {
    try {
        const r = await fetch(`${API}/metrics/models`);
        const data = await r.json();
        const tbody = document.getElementById("models-tbody");
        if (!data.models || data.models.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6">Нет данных</td></tr>';
            return;
        }
        const sorted = data.models.sort((a, b) =>
            (b.metrics?.CSI ?? 0) - (a.metrics?.CSI ?? 0));
        tbody.innerHTML = sorted.map(m => `
            <tr>
                <td><strong>${label(m.model)}</strong><br>
                    <small style="color:var(--text-secondary);font-size:0.75em">${m.model}</small></td>
                <td>${m.metrics?.POD?.toFixed(3) ?? "—"}</td>
                <td>${m.metrics?.FAR?.toFixed(3) ?? "—"}</td>
                <td>${m.metrics?.CSI?.toFixed(3) ?? "—"}</td>
                <td>${m.metrics?.HK?.toFixed(3)  ?? "—"}</td>
                <td>${m.n_forecasts ?? "—"}</td>
            </tr>
        `).join("");
    } catch (e) { console.error("Модели:", e); }
}

document.addEventListener("DOMContentLoaded", () => {
    loadMetrics();
    loadModels();
});


// === Смена темы ===
(function() {
    const THEME_KEY = 'groz_theme';

    function applyTheme(theme) {
        document.body.classList.remove('theme-dark', 'theme-light', 'theme-contrast');
        if (theme !== 'dark') {
            document.body.classList.add('theme-' + theme);
        }
        // Подсветить активную кнопку
        document.querySelectorAll('.theme-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.theme === theme);
        });
        localStorage.setItem(THEME_KEY, theme);
    }

    window.setTheme = function(theme) {
        applyTheme(theme);
    };

    // Применяем сохранённую тему сразу при загрузке
    document.addEventListener('DOMContentLoaded', () => {
        const saved = localStorage.getItem(THEME_KEY) || 'dark';
        applyTheme(saved);
    });
})();
