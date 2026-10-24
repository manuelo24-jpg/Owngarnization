/**
 * Owngarnization — Coordinador Principal de Estado y Vistas
 */

class AppState {
  constructor() {
    this.currentDate = new Date();
    this.currentView = "day"; // "day" | "week" | "month"
    this.filters = {
      kind: "",
      status: "",
      importance: "",
      q: ""
    };
    this.searchDebounceTimer = null;
  }

  init() {
    // Inicializar componentes
    if (window.modal) window.modal.init();
    if (window.board) window.board.init();
    if (window.calendarManager) window.calendarManager.init();

    this.bindControls();
    this.updatePeriodLabel();
    this.reloadCurrentView();
  }

  bindControls() {
    // Botón "+ Nueva tarea"
    document.getElementById("btn-new-task")?.addEventListener("click", () => {
      if (window.modal) window.modal.openTaskModal("create");
    });

    // Navegación: Anterior, Hoy, Siguiente
    document.getElementById("btn-prev")?.addEventListener("click", () => this.navigate(-1));
    document.getElementById("btn-next")?.addEventListener("click", () => this.navigate(1));
    document.getElementById("btn-today")?.addEventListener("click", () => {
      this.currentDate = new Date();
      this.onDateChanged();
    });

    // Selector de vistas (Segmented Control)
    document.querySelectorAll(".view-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const view = btn.dataset.view;
        this.switchView(view);
      });
    });

    // Buscador con debounce
    const searchInput = document.getElementById("search-input");
    searchInput?.addEventListener("input", (e) => {
      clearTimeout(this.searchDebounceTimer);
      this.searchDebounceTimer = setTimeout(() => {
        this.filters.q = e.target.value.trim();
        this.checkFiltersActive();
        this.reloadCurrentView();
      }, 250);
    });

    // Chips de filtros
    document.querySelectorAll(".filter-chips").forEach(container => {
      const filterKey = container.dataset.filter;
      container.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
          container.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
          chip.classList.add("active");
          this.filters[filterKey] = chip.dataset.value;
          this.checkFiltersActive();
          this.reloadCurrentView();
        });
      });
    });

    // Botón "Limpiar filtros"
    document.getElementById("btn-reset-filters")?.addEventListener("click", () => {
      this.resetFilters();
    });
  }

  checkFiltersActive() {
    const hasActiveFilters = Boolean(
      this.filters.kind ||
      this.filters.status ||
      this.filters.importance ||
      this.filters.q
    );
    const resetBtn = document.getElementById("btn-reset-filters");
    if (resetBtn) {
      resetBtn.style.display = hasActiveFilters ? "inline-block" : "none";
    }
  }

  resetFilters() {
    this.filters = { kind: "", status: "", importance: "", q: "" };
    
    // Limpiar input de búsqueda
    const searchInput = document.getElementById("search-input");
    if (searchInput) searchInput.value = "";

    // Resetear chips activos
    document.querySelectorAll(".filter-chips").forEach(container => {
      container.querySelectorAll(".chip").forEach(chip => {
        chip.classList.toggle("active", chip.dataset.value === "");
      });
    });

    this.checkFiltersActive();
    this.reloadCurrentView();
  }

  setDate(newDate) {
    this.currentDate = new Date(newDate);
    this.onDateChanged();
  }

  onDateChanged() {
    this.updatePeriodLabel();
    if (window.calendarManager) {
      window.calendarManager.gotoDate(this.currentDate);
    }
    this.reloadCurrentView();
  }

  navigate(step) {
    if (this.currentView === "day") {
      this.currentDate.setDate(this.currentDate.getDate() + step);
    } else if (this.currentView === "week") {
      this.currentDate.setDate(this.currentDate.getDate() + (step * 7));
    } else if (this.currentView === "month") {
      this.currentDate.setMonth(this.currentDate.getMonth() + step);
    }
    this.onDateChanged();
  }

  switchView(newView) {
    this.currentView = newView;

    // Actualizar botones de vista
    document.querySelectorAll(".view-btn").forEach(btn => {
      const isActive = btn.dataset.view === newView;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    // Mostrar sección correspondiente
    const views = {
      day: document.getElementById("view-day"),
      week: document.getElementById("view-week"),
      month: document.getElementById("view-month")
    };

    for (const [key, el] of Object.entries(views)) {
      if (el) {
        el.style.display = key === newView ? "block" : "none";
      }
    }

    this.updatePeriodLabel();

    // Redimensionar calendario al hacerse visible
    if (newView === "month" && window.calendarManager?.calendarMonth) {
      setTimeout(() => window.calendarManager.calendarMonth.updateSize(), 50);
    } else if (newView === "week" && window.calendarManager?.calendarWeek) {
      setTimeout(() => window.calendarManager.calendarWeek.updateSize(), 50);
    }

    this.reloadCurrentView();
  }

  getCurrentDateFormatted() {
    const y = this.currentDate.getFullYear();
    const m = String(this.currentDate.getMonth() + 1).padStart(2, "0");
    const d = String(this.currentDate.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  updatePeriodLabel() {
    const labelEl = document.getElementById("current-period-label");
    if (!labelEl) return;

    if (this.currentView === "day") {
      labelEl.textContent = this.currentDate.toLocaleDateString("es-ES", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric"
      });
    } else if (this.currentView === "week") {
      const { start, end } = this.getWeekRange(this.currentDate);
      const startStr = start.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
      const endStr = end.toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" });
      labelEl.textContent = `${startStr} – ${endStr}`;
    } else if (this.currentView === "month") {
      labelEl.textContent = this.currentDate.toLocaleDateString("es-ES", {
        month: "long",
        year: "numeric"
      });
    }
  }

  getWeekRange(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diffToMonday = (day === 0 ? -6 : 1) - day;
    const monday = new Date(d);
    monday.setDate(d.getDate() + diffToMonday);

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    return { start: monday, end: sunday };
  }

  getMonthRange(date) {
    const y = date.getFullYear();
    const m = date.getMonth();
    const firstDay = new Date(y, m, 1);
    const lastDay = new Date(y, m + 1, 0);

    // Añadir margen de seguridad para cubrir la cuadrícula completa del mes
    const start = new Date(firstDay);
    start.setDate(firstDay.getDate() - 7);

    const end = new Date(lastDay);
    end.setDate(lastDay.getDate() + 7);

    return { start, end };
  }

  async reloadCurrentView() {
    let startStr, endStr;

    if (this.currentView === "day") {
      startStr = this.getCurrentDateFormatted();
      endStr = startStr;
    } else if (this.currentView === "week") {
      const { start, end } = this.getWeekRange(this.currentDate);
      startStr = this.formatDate(start);
      endStr = this.formatDate(end);
    } else if (this.currentView === "month") {
      const { start, end } = this.getMonthRange(this.currentDate);
      startStr = this.formatDate(start);
      endStr = this.formatDate(end);
    }

    const params = {
      start: startStr,
      end: endStr,
      ...this.filters
    };

    try {
      const occurrences = await api.get("/api/occurrences", params);
      if (!occurrences) return;

      if (this.currentView === "day" && window.board) {
        window.board.renderOccurrences(occurrences);
      } else if (this.currentView === "week" && window.calendarManager) {
        window.calendarManager.updateWeekEvents(occurrences);
      } else if (this.currentView === "month" && window.calendarManager) {
        window.calendarManager.updateMonthEvents(occurrences);
      }
    } catch (err) {
      console.error("Error al cargar ocurrencias:", err);
      showToast("Error al cargar las tareas", "error");
    }
  }
}

// Inicializar cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", () => {
  window.appState = new AppState();
  window.appState.init();
});
