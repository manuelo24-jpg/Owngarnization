/**
 * Owngarnization — Lógica del Tablero de Post-its (Vista Día)
 */

const board = {
  sortableCommon: null,
  sortableDaily: null,
  mobileActiveTab: "daily",

  isMobileMode() {
    return Boolean(document.querySelector('[data-app-mode="mobile"]'));
  },

  init() {
    this.initSortable();
    this.bindEvents();
  },

  setMobileActiveTab(tabName) {
    this.mobileActiveTab = tabName;
    document.querySelectorAll(".mobile-day-tab").forEach(t => {
      const active = t.dataset.dayTab === this.mobileActiveTab;
      t.classList.toggle("active", active);
      t.setAttribute("aria-selected", active ? "true" : "false");
    });
  },

  bindEvents() {
    document.querySelector(".btn-quick-add")?.addEventListener("click", () => {
      if (window.modal) window.modal.openTaskModal("create");
    });

    // Pestañas segmentadas en la versión móvil (/m)
    document.querySelectorAll(".mobile-day-tab").forEach(tab => {
      tab.addEventListener("click", () => {
        const targetTab = tab.dataset.dayTab;
        this.setMobileActiveTab(targetTab);

        if (window.appState && window.appState.filters.kind && window.appState.filters.kind !== targetTab) {
          window.appState.filters.kind = "";
          const kindContainer = document.querySelector('.filter-chips[data-filter="kind"]');
          kindContainer?.querySelectorAll(".chip").forEach(c => {
            c.classList.toggle("active", c.dataset.value === "");
          });
          window.appState.checkFiltersActive();
          window.appState.reloadCurrentView();
          return;
        }

        this.updateColumnVisibility();
      });
    });
  },

  updateColumnVisibility() {
    const colCommon = document.getElementById("column-common");
    const colDaily = document.getElementById("column-daily");
    if (!colCommon || !colDaily) return;

    const currentKindFilter = window.appState ? window.appState.filters.kind : "";
    if (currentKindFilter === "daily") {
      colCommon.style.display = "none";
      colDaily.style.display = "";
      if (this.isMobileMode()) this.setMobileActiveTab("daily");
    } else if (currentKindFilter === "common") {
      colCommon.style.display = "";
      colDaily.style.display = "none";
      if (this.isMobileMode()) this.setMobileActiveTab("common");
    } else if (this.isMobileMode()) {
      colCommon.style.display = this.mobileActiveTab === "common" ? "" : "none";
      colDaily.style.display = this.mobileActiveTab === "daily" ? "" : "none";
    } else {
      colCommon.style.display = "";
      colDaily.style.display = "";
    }
  },

  initSortable() {
    const listCommon = document.getElementById("list-common");
    const listDaily = document.getElementById("list-daily");

    if (listCommon && !this.sortableCommon && window.Sortable) {
      this.sortableCommon = new Sortable(listCommon, {
        animation: 180,
        delay: 200,
        delayOnTouchOnly: true,
        ghostClass: "sortable-ghost",
        chosenClass: "sortable-chosen",
        dragClass: "sortable-drag",
        onEnd: () => this.handleReorder(listCommon)
      });
    }

    if (listDaily && !this.sortableDaily && window.Sortable) {
      this.sortableDaily = new Sortable(listDaily, {
        animation: 180,
        delay: 200,
        delayOnTouchOnly: true,
        ghostClass: "sortable-ghost",
        chosenClass: "sortable-chosen",
        dragClass: "sortable-drag",
        onEnd: () => this.handleReorder(listDaily)
      });
    }
  },

  async handleReorder(container) {
    const cards = container.querySelectorAll(".postit-card");
    const orderedIds = Array.from(cards).map(c => parseInt(c.dataset.occId, 10)).filter(Boolean);
    const currentDate = window.appState ? window.appState.getCurrentDateFormatted() : new Date().toISOString().split("T")[0];

    try {
      await api.post("/api/occurrences/reorder", {
        date: currentDate,
        ordered_ids: orderedIds
      });
    } catch (err) {
      console.error("Error al reordenar post-its:", err);
      showToast("No se pudo guardar el nuevo orden", "error");
    }
  },

  createSkeletonCardHtml(titleWidth = "80%", showDesc = true) {
    return `
      <div class="postit-skeleton-card" aria-hidden="true">
        <div class="postit-skeleton-header">
          <div class="skeleton-block postit-skeleton-circle"></div>
          <div class="skeleton-block postit-skeleton-badge"></div>
        </div>
        <div class="skeleton-block postit-skeleton-title" style="width: ${titleWidth};"></div>
        ${showDesc ? '<div class="skeleton-block postit-skeleton-desc"></div>' : ""}
        <div class="postit-skeleton-footer">
          <div class="skeleton-block postit-skeleton-time"></div>
          <div class="skeleton-block postit-skeleton-tag"></div>
        </div>
      </div>
    `;
  },

  showSkeletons() {
    const listCommon = document.getElementById("list-common");
    const listDaily = document.getElementById("list-daily");
    const emptyCommon = document.getElementById("empty-common");
    const emptyDaily = document.getElementById("empty-daily");

    if (!listCommon || !listDaily) return;

    this.updateColumnVisibility();

    if (emptyCommon) emptyCommon.style.display = "none";
    if (emptyDaily) emptyDaily.style.display = "none";

    const skeletonHtml =
      this.createSkeletonCardHtml("82%", true) +
      this.createSkeletonCardHtml("68%", false);

    listCommon.setAttribute("aria-busy", "true");
    listDaily.setAttribute("aria-busy", "true");
    listCommon.innerHTML = skeletonHtml;
    listDaily.innerHTML = skeletonHtml;
  },

  renderOccurrences(occurrences) {
    const listCommon = document.getElementById("list-common");
    const listDaily = document.getElementById("list-daily");
    const badgeCommon = document.getElementById("badge-common");
    const badgeDaily = document.getElementById("badge-daily");
    const mobileCountCommon = document.getElementById("mobile-count-common");
    const mobileCountDaily = document.getElementById("mobile-count-daily");
    const emptyCommon = document.getElementById("empty-common");
    const emptyDaily = document.getElementById("empty-daily");

    if (!listCommon || !listDaily) return;

    const commons = occurrences.filter(o => o.task.kind === "common");
    const dailies = occurrences.filter(o => o.task.kind === "daily");

    if (this.isMobileMode() && window.appState) {
      const f = window.appState.filters;
      const hasSearchOrFilter = Boolean(f.status || f.importance || f.q);
      if (hasSearchOrFilter && !f.kind) {
        if (this.mobileActiveTab === "daily" && dailies.length === 0 && commons.length > 0) {
          this.setMobileActiveTab("common");
        } else if (this.mobileActiveTab === "common" && commons.length === 0 && dailies.length > 0) {
          this.setMobileActiveTab("daily");
        }
      }
    }

    this.updateColumnVisibility();

    listCommon.setAttribute("aria-busy", "false");
    listDaily.setAttribute("aria-busy", "false");
    listCommon.innerHTML = "";
    listDaily.innerHTML = "";

    if (badgeCommon) badgeCommon.textContent = commons.length;
    if (badgeDaily) badgeDaily.textContent = dailies.length;
    if (mobileCountCommon) mobileCountCommon.textContent = commons.length;
    if (mobileCountDaily) mobileCountDaily.textContent = dailies.length;

    if (commons.length === 0) {
      if (emptyCommon) emptyCommon.style.display = "flex";
    } else {
      if (emptyCommon) emptyCommon.style.display = "none";
      const fragCommon = document.createDocumentFragment();
      commons.forEach((occ, idx) => {
        fragCommon.appendChild(this.createPostitElement(occ, idx));
      });
      listCommon.appendChild(fragCommon);
    }

    if (dailies.length === 0) {
      if (emptyDaily) emptyDaily.style.display = "flex";
    } else {
      if (emptyDaily) emptyDaily.style.display = "none";
      const fragDaily = document.createDocumentFragment();
      dailies.forEach((occ, idx) => {
        fragDaily.appendChild(this.createPostitElement(occ, idx));
      });
      listDaily.appendChild(fragDaily);
    }
  },

  createPostitElement(occ, idx = 0) {
    const task = occ.task;
    const card = document.createElement("div");
    card.className = `postit-card importance-${task.importance} status-${occ.status} postit-enter`;
    card.style.setProperty("--card-idx", String(Math.min(idx, 8)));
    card.dataset.occId = occ.id;
    card.dataset.taskId = task.id;

    const statusIcons = {
      not_started: "○",
      in_progress: "◐",
      done: "✓"
    };
    const statusTitles = {
      not_started: "Sin empezar (clic para avanzar)",
      in_progress: "En proceso (clic para finalizar)",
      done: "Finalizada (clic para reiniciar)"
    };

    let timeHtml = "";
    const startTime = occ.start_time || task.start_time;
    const endTime = occ.end_time || task.end_time;
    if (startTime || endTime) {
      const startStr = startTime ? startTime.substring(0, 5) : "";
      const endStr = endTime ? endTime.substring(0, 5) : "";
      timeHtml = `
        <span class="postit-time" title="Horario programado">
          ⏱️ ${startStr}${endStr ? " - " + endStr : ""}
        </span>
      `;
    }

    let descHtml = "";
    if (task.description && task.description.trim()) {
      descHtml = `<p class="postit-desc-preview">${this.escapeHtml(task.description)}</p>`;
    }

    let kindBadgeText = "📌 Día";
    if (task.kind === "common") {
      if (task.days_of_week) {
        const dayNames = { "1": "L", "2": "M", "3": "X", "4": "J", "5": "V", "6": "S", "7": "D" };
        const dArr = task.days_of_week.split(",").map(d => dayNames[d.trim()] || d);
        kindBadgeText = `🔁 ${dArr.join(",")}`;
      } else {
        kindBadgeText = "🔁 Todos los días";
      }
    }

    card.innerHTML = `
      <div class="postit-header">
        <button class="postit-status-btn" title="${statusTitles[occ.status] || ''}" aria-label="Cambiar estado">
          ${statusIcons[occ.status] || "○"}
        </button>
        <span class="postit-kind-badge">${kindBadgeText}</span>
      </div>
      <h4 class="postit-title">${this.escapeHtml(task.title)}</h4>
      ${descHtml}
      <div class="postit-footer">
        ${timeHtml}
        <span class="postit-importance-tag">${task.importance}</span>
      </div>
    `;

    card.addEventListener("click", (e) => {
      if (e.target.closest(".postit-status-btn")) return;
      if (window.modal) window.modal.openDetailDrawer(occ);
    });

    const statusBtn = card.querySelector(".postit-status-btn");
    statusBtn?.addEventListener("click", async (e) => {
      e.stopPropagation();
      const cycle = {
        not_started: "in_progress",
        in_progress: "done",
        done: "not_started"
      };
      const nextStatus = cycle[occ.status] || "not_started";
      statusBtn.classList.add("is-updating");

      try {
        const updated = await api.patch(`/api/occurrences/${occ.id}`, { status: nextStatus });
        occ.status = updated.status;

        card.className = `postit-card importance-${task.importance} status-${occ.status}`;
        statusBtn.textContent = statusIcons[occ.status];
        statusBtn.title = statusTitles[occ.status];

        showToast(`Estado: ${occ.status === "done" ? "Finalizada ✓" : occ.status === "in_progress" ? "En proceso ◐" : "Sin empezar ○"}`, "info", 1500);
      } catch (err) {
        showToast("Error al cambiar estado", "error");
      } finally {
        statusBtn.classList.remove("is-updating");
      }
    });

    return card;
  },

  escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
};

window.board = board;
