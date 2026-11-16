/**
 * =========================================================
 * Owngarnization — Analytics, Summaries & History Module
 * =========================================================
 */

(() => {
  let modal = null;
  let currentDailyDate = "";
  let currentWeekRefDate = "";
  let historyLimit = 15;
  let historyOffset = 0;
  let historySearchTimeout = null;
  let currentHistoryData = null;

  function formatISODate(d) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function getTodayISO() {
    return formatISODate(new Date());
  }

  function showToast(message, type = "info") {
    if (window.showToast) {
      window.showToast(message, type);
    } else {
      console.log(`[${type.toUpperCase()}] ${message}`);
    }
  }

  // --- Inicialización ---
  document.addEventListener("DOMContentLoaded", () => {
    modal = document.getElementById("analytics-modal");
    if (!modal) return;

    currentDailyDate = getTodayISO();
    currentWeekRefDate = getTodayISO();

    // Botones de apertura en cabeceras
    const openBtns = document.querySelectorAll("#btn-analytics, .btn-open-analytics");
    openBtns.forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openAnalyticsModal();
      });
    });

    // Botón de cierre
    const closeBtn = document.getElementById("analytics-close-btn");
    closeBtn?.addEventListener("click", closeAnalyticsModal);

    // Cerrar al hacer clic en el backdrop
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeAnalyticsModal();
    });

    // Pestañas
    const tabBtns = modal.querySelectorAll(".analytics-tab-btn");
    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetTab = btn.getAttribute("data-tab");
        switchTab(targetTab);
      });
    });

    // Controles Día
    document.getElementById("btn-daily-prev")?.addEventListener("click", () => {
      shiftDailyDate(-1);
    });
    document.getElementById("btn-daily-next")?.addEventListener("click", () => {
      shiftDailyDate(1);
    });
    document.getElementById("btn-daily-today")?.addEventListener("click", () => {
      currentDailyDate = getTodayISO();
      loadDailySummary();
    });
    document.getElementById("analytics-daily-date-input")?.addEventListener("change", (e) => {
      if (e.target.value) {
        currentDailyDate = e.target.value;
        loadDailySummary();
      }
    });

    // Acción Carry-over (Posponer pendientes a mañana)
    document.getElementById("btn-daily-carry-over")?.addEventListener("click", handleDailyCarryOver);

    // Controles Semana
    document.getElementById("btn-weekly-prev")?.addEventListener("click", () => {
      shiftWeeklyDate(-7);
    });
    document.getElementById("btn-weekly-next")?.addEventListener("click", () => {
      shiftWeeklyDate(7);
    });
    document.getElementById("btn-weekly-curr")?.addEventListener("click", () => {
      currentWeekRefDate = getTodayISO();
      loadWeeklySummary();
    });

    // Controles Historial
    const searchInput = document.getElementById("history-search-input");
    searchInput?.addEventListener("input", () => {
      clearTimeout(historySearchTimeout);
      historySearchTimeout = setTimeout(() => {
        historyOffset = 0;
        loadHistory();
      }, 350);
    });

    document.getElementById("history-start-date")?.addEventListener("change", () => {
      historyOffset = 0;
      loadHistory();
    });
    document.getElementById("history-end-date")?.addEventListener("change", () => {
      historyOffset = 0;
      loadHistory();
    });

    document.getElementById("btn-history-prev")?.addEventListener("click", () => {
      if (historyOffset >= historyLimit) {
        historyOffset -= historyLimit;
        loadHistory();
      }
    });

    document.getElementById("btn-history-next")?.addEventListener("click", () => {
      historyOffset += historyLimit;
      loadHistory();
    });

    document.getElementById("btn-copy-history-md")?.addEventListener("click", copyHistoryMarkdown);

    // Atajo Esc para cerrar
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && modal && modal.style.display !== "none") {
        closeAnalyticsModal();
      }
    });
  });

  function openAnalyticsModal() {
    if (!modal) return;
    modal.style.display = "flex";
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";

    // Cargar datos de la pestaña activa
    const activeTab = modal.querySelector(".analytics-tab-btn.active")?.getAttribute("data-tab") || "daily";
    switchTab(activeTab);
  }

  function closeAnalyticsModal() {
    if (!modal) return;
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  function switchTab(tabKey) {
    if (!modal) return;

    // Actualizar botones
    modal.querySelectorAll(".analytics-tab-btn").forEach((btn) => {
      const isTarget = btn.getAttribute("data-tab") === tabKey;
      btn.classList.toggle("active", isTarget);
      btn.setAttribute("aria-selected", isTarget ? "true" : "false");
    });

    // Actualizar paneles
    modal.querySelectorAll(".analytics-panel").forEach((panel) => {
      panel.style.display = "none";
      panel.classList.remove("active");
    });

    const targetPanel = document.getElementById(`panel-analytics-${tabKey}`);
    if (targetPanel) {
      targetPanel.style.display = "flex";
      targetPanel.classList.add("active");
    }

    if (tabKey === "daily") {
      loadDailySummary();
    } else if (tabKey === "weekly") {
      loadWeeklySummary();
    } else if (tabKey === "history") {
      loadHistory();
    }
  }

  // =========================================================
  // 1. Cierre del Día
  // =========================================================

  function shiftDailyDate(days) {
    const d = new Date(currentDailyDate + "T00:00:00");
    d.setDate(d.getDate() + days);
    currentDailyDate = formatISODate(d);
    loadDailySummary();
  }

  async function loadDailySummary() {
    const label = document.getElementById("analytics-daily-date-label");
    const dateInput = document.getElementById("analytics-daily-date-input");
    const today = getTodayISO();

    if (dateInput) dateInput.value = currentDailyDate;
    if (label) {
      if (currentDailyDate === today) {
        label.textContent = "Hoy (" + formatDateNice(currentDailyDate) + ")";
      } else {
        label.textContent = formatDateNice(currentDailyDate);
      }
    }

    try {
      const res = await fetch(`/api/reports/daily?date=${currentDailyDate}`);
      if (!res.ok) throw new Error("Error al cargar informe diario");
      const data = await res.json();
      renderDailySummary(data);
    } catch (err) {
      console.error(err);
      showToast("No se pudo cargar el resumen diario", "error");
    }
  }

  function renderDailySummary(data) {
    document.getElementById("daily-rate-percent").textContent = `${data.completion_rate}%`;
    document.getElementById("daily-motivational-msg").textContent = data.motivational_message;
    document.getElementById("daily-streak-badge").textContent = `🔥 ${data.current_streak} día(s) en racha`;

    document.getElementById("daily-kpi-completed").textContent = `${data.completed_tasks} / ${data.total_tasks}`;
    document.getElementById("daily-kpi-time").textContent = `${data.estimated_minutes_completed} min`;

    const urgentCompleted = data.by_importance?.urgent?.completed || 0;
    const urgentTotal = data.by_importance?.urgent?.total || 0;
    document.getElementById("daily-kpi-urgent").textContent = `${urgentCompleted} / ${urgentTotal}`;

    const commonCompleted = data.by_kind?.common?.completed || 0;
    const commonTotal = data.by_kind?.common?.total || 0;
    document.getElementById("daily-kpi-common").textContent = `${commonCompleted} / ${commonTotal}`;

    // Posponer pendientes
    const carryBox = document.getElementById("daily-carry-over-box");
    const pendingCount = data.total_tasks - data.completed_tasks;
    if (carryBox) {
      if (pendingCount > 0) {
        carryBox.style.display = "flex";
        document.getElementById("daily-carry-over-text").textContent =
          `Tienes ${pendingCount} tarea(s) pendiente(s) en este día.`;
      } else {
        carryBox.style.display = "none";
      }
    }

    // Lista de tareas
    const listEl = document.getElementById("daily-tasks-list");
    const countPill = document.getElementById("daily-task-count-pill");
    if (countPill) countPill.textContent = data.tasks.length;

    if (!listEl) return;
    if (!data.tasks || data.tasks.length === 0) {
      listEl.innerHTML = `<p class="analytics-empty-state">No hay tareas programadas para esta fecha.</p>`;
      return;
    }

    listEl.innerHTML = data.tasks
      .map((t) => {
        const isDone = t.status === "done";
        const icon = isDone ? "✓" : t.status === "in_progress" ? "◐" : "○";
        const timeStr = t.start_time ? ` · 🕒 ${t.start_time.slice(0, 5)}` : "";
        const kindLabel = t.kind === "common" ? "Rutina" : "Día";

        return `
          <div class="analytics-task-row ${isDone ? "is-done" : ""}">
            <div class="analytics-task-left">
              <span class="analytics-task-status-icon">${icon}</span>
              <span class="analytics-task-title" title="${escapeHtml(t.title)}">${escapeHtml(t.title)}</span>
            </div>
            <div class="analytics-task-meta">
              <span class="analytics-tag analytics-tag-${t.importance}">${t.importance}</span>
              <span class="history-date-badge">${kindLabel}${timeStr}</span>
            </div>
          </div>
        `;
      })
      .join("");
  }

  async function handleDailyCarryOver() {
    const btn = document.getElementById("btn-daily-carry-over");
    if (btn) btn.disabled = true;

    try {
      const res = await fetch(`/api/reports/daily/carry-over?date=${currentDailyDate}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Fallo al posponer tareas");
      const data = await res.json();
      showToast(data.message, "success");

      // Recargar resumen diario
      await loadDailySummary();

      // Si existe el tablero en pantalla, actualizarlo
      if (window.app && typeof window.app.loadTasksForCurrentDate === "function") {
        window.app.loadTasksForCurrentDate();
      }
    } catch (err) {
      console.error(err);
      showToast("No se pudieron posponer las tareas", "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // =========================================================
  // 2. Rendimiento Semanal
  // =========================================================

  function shiftWeeklyDate(days) {
    const d = new Date(currentWeekRefDate + "T00:00:00");
    d.setDate(d.getDate() + days);
    currentWeekRefDate = formatISODate(d);
    loadWeeklySummary();
  }

  async function loadWeeklySummary() {
    try {
      const res = await fetch(`/api/reports/weekly?week=${currentWeekRefDate}`);
      if (!res.ok) throw new Error("Error al cargar resumen semanal");
      const data = await res.json();
      renderWeeklySummary(data);
    } catch (err) {
      console.error(err);
      showToast("No se pudo cargar el rendimiento semanal", "error");
    }
  }

  function renderWeeklySummary(data) {
    const rangeLabel = document.getElementById("analytics-weekly-range-label");
    if (rangeLabel) {
      rangeLabel.textContent = `Semana del ${formatDateNice(data.week_start)} al ${formatDateNice(data.week_end)}`;
    }

    document.getElementById("weekly-kpi-rate").textContent = `${data.completion_rate}%`;
    document.getElementById("weekly-kpi-completed").textContent = `${data.completed_tasks} / ${data.total_tasks}`;
    document.getElementById("weekly-kpi-best-day").textContent = data.best_day || "—";
    document.getElementById("weekly-kpi-streak").textContent = `${data.current_streak} día(s)`;

    const barsContainer = document.getElementById("weekly-bars-container");
    if (!barsContainer) return;

    barsContainer.innerHTML = data.days
      .map((d) => {
        const heightPercent = d.completion_rate;
        const fillStyle = heightPercent > 0 ? `height: ${Math.max(6, heightPercent)}%;` : `height: 0;`;

        return `
          <div class="weekly-bar-col ${d.is_today ? "is-today" : ""}">
            <span class="weekly-bar-rate">${d.completion_rate}%</span>
            <div class="weekly-bar-track" title="${d.day_name} (${d.date}): ${d.completed_tasks} de ${d.total_tasks} completadas">
              <div class="weekly-bar-fill" style="${fillStyle}"></div>
            </div>
            <span class="weekly-bar-day ${d.is_today ? "is-today-pill" : ""}">${d.day_name}</span>
            <span class="weekly-bar-count">${d.completed_tasks}/${d.total_tasks}</span>
          </div>
        `;
      })
      .join("");
  }

  // =========================================================
  // 3. Historial de Tareas
  // =========================================================

  async function loadHistory() {
    const q = document.getElementById("history-search-input")?.value?.trim() || "";
    const startDate = document.getElementById("history-start-date")?.value || "";
    const endDate = document.getElementById("history-end-date")?.value || "";

    const params = new URLSearchParams({
      limit: historyLimit.toString(),
      offset: historyOffset.toString(),
    });
    if (q) params.set("q", q);
    if (startDate) params.set("start", startDate);
    if (endDate) params.set("end", endDate);

    try {
      const res = await fetch(`/api/history?${params.toString()}`);
      if (!res.ok) throw new Error("Error al obtener historial");
      const data = await res.json();
      currentHistoryData = data;
      renderHistory(data);
    } catch (err) {
      console.error(err);
      showToast("No se pudo cargar el historial", "error");
    }
  }

  function renderHistory(data) {
    const container = document.getElementById("history-list-container");
    const prevBtn = document.getElementById("btn-history-prev");
    const nextBtn = document.getElementById("btn-history-next");
    const pageInfo = document.getElementById("history-page-info");

    if (prevBtn) prevBtn.disabled = data.offset <= 0;
    if (nextBtn) nextBtn.disabled = data.offset + data.limit >= data.total;

    const currentPage = Math.floor(data.offset / data.limit) + 1;
    const totalPages = Math.max(1, Math.ceil(data.total / data.limit));
    if (pageInfo) {
      pageInfo.textContent = `Página ${currentPage} de ${totalPages} (${data.total} tareas)`;
    }

    if (!container) return;
    if (!data.items || data.items.length === 0) {
      container.innerHTML = `<p class="analytics-empty-state">No hay tareas completadas que coincidan con los filtros.</p>`;
      return;
    }

    container.innerHTML = data.items
      .map((item) => {
        const isProject = item.kind === "project";
        const projBadge = isProject
          ? `<span class="history-project-badge">📁 ${escapeHtml(item.project_name || "Proyecto")}</span>`
          : "";
        const descHtml = item.description
          ? `<span class="history-item-desc">${escapeHtml(item.description)}</span>`
          : "";

        return `
          <div class="history-item-row">
            <div class="history-item-info">
              <span class="history-item-title">${escapeHtml(item.title)}</span>
              ${descHtml}
              <div class="history-item-badges">
                <span class="history-date-badge">📅 ${formatDateNice(item.date)}</span>
                <span class="analytics-tag analytics-tag-${item.importance}">${item.importance}</span>
                ${projBadge}
              </div>
            </div>
            <span class="kpi-icon" style="color: #2E7D32; font-weight: 800;">✓</span>
          </div>
        `;
      })
      .join("");
  }

  function copyHistoryMarkdown() {
    if (!currentHistoryData || !currentHistoryData.items || currentHistoryData.items.length === 0) {
      showToast("No hay tareas en el historial para copiar", "warning");
      return;
    }

    const lines = ["# Historial de Tareas Completadas — Owngarnization\n"];
    currentHistoryData.items.forEach((item) => {
      const proj = item.project_name ? ` [Proyecto: ${item.project_name}]` : "";
      lines.push(`- [x] **${item.title}** (${item.date}) · Importancia: ${item.importance}${proj}`);
    });

    const markdownText = lines.join("\n");
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(markdownText).then(
        () => showToast("Historial copiado al portapapeles en Markdown 📋", "success"),
        () => fallbackCopyText(markdownText)
      );
    } else {
      fallbackCopyText(markdownText);
    }
  }

  function fallbackCopyText(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    showToast("Historial copiado al portapapeles 📋", "success");
  }

  function formatDateNice(isoStr) {
    if (!isoStr) return "";
    try {
      const parts = isoStr.split("-");
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
    } catch {
      // fallback
    }
    return isoStr;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Exportar para acceso global
  window.analyticsManager = {
    open: openAnalyticsModal,
    close: closeAnalyticsModal,
    reloadDaily: loadDailySummary,
  };
})();

