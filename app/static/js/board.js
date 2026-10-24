/**
 * Owngarnization — Lógica del Tablero de Post-its (Vista Día)
 */

const board = {
  sortableCommon: null,
  sortableDaily: null,

  init() {
    this.initSortable();
    this.bindEvents();
  },

  bindEvents() {
    // Botón de añadir rápido en el estado vacío del día
    document.querySelector(".btn-quick-add")?.addEventListener("click", () => {
      if (window.modal) window.modal.openTaskModal("create");
    });
  },

  initSortable() {
    const listCommon = document.getElementById("list-common");
    const listDaily = document.getElementById("list-daily");

    if (listCommon && !this.sortableCommon && window.Sortable) {
      this.sortableCommon = new Sortable(listCommon, {
        animation: 180,
        ghostClass: "sortable-ghost",
        chosenClass: "sortable-chosen",
        dragClass: "sortable-drag",
        onEnd: (evt) => this.handleReorder(listCommon)
      });
    }

    if (listDaily && !this.sortableDaily && window.Sortable) {
      this.sortableDaily = new Sortable(listDaily, {
        animation: 180,
        ghostClass: "sortable-ghost",
        chosenClass: "sortable-chosen",
        dragClass: "sortable-drag",
        onEnd: (evt) => this.handleReorder(listDaily)
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

  renderOccurrences(occurrences) {
    const listCommon = document.getElementById("list-common");
    const listDaily = document.getElementById("list-daily");
    const badgeCommon = document.getElementById("badge-common");
    const badgeDaily = document.getElementById("badge-daily");
    const emptyCommon = document.getElementById("empty-common");
    const emptyDaily = document.getElementById("empty-daily");

    if (!listCommon || !listDaily) return;

    listCommon.innerHTML = "";
    listDaily.innerHTML = "";

    const commons = occurrences.filter(o => o.task.kind === "common");
    const dailies = occurrences.filter(o => o.task.kind === "daily");

    // Actualizar badges numéricos
    if (badgeCommon) badgeCommon.textContent = commons.length;
    if (badgeDaily) badgeDaily.textContent = dailies.length;

    // Renderizar comunes
    if (commons.length === 0) {
      if (emptyCommon) emptyCommon.style.display = "flex";
    } else {
      if (emptyCommon) emptyCommon.style.display = "none";
      commons.forEach(occ => {
        listCommon.appendChild(this.createPostitElement(occ));
      });
    }

    // Renderizar del día
    if (dailies.length === 0) {
      if (emptyDaily) emptyDaily.style.display = "flex";
    } else {
      if (emptyDaily) emptyDaily.style.display = "none";
      dailies.forEach(occ => {
        listDaily.appendChild(this.createPostitElement(occ));
      });
    }
  },

  createPostitElement(occ) {
    const task = occ.task;
    const card = document.createElement("div");
    card.className = `postit-card importance-${task.importance} status-${occ.status}`;
    card.dataset.occId = occ.id;
    card.dataset.taskId = task.id;

    // Icono según estado
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

    // Horario
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

    // Descripción previa
    let descHtml = "";
    if (task.description && task.description.trim()) {
      descHtml = `<p class="postit-desc-preview">${this.escapeHtml(task.description)}</p>`;
    }

    card.innerHTML = `
      <div class="postit-header">
        <button class="postit-status-btn" title="${statusTitles[occ.status] || ''}" aria-label="Cambiar estado">
          ${statusIcons[occ.status] || "○"}
        </button>
        <span class="postit-kind-badge">${task.kind === "common" ? "🔁 Común" : "📌 Día"}</span>
      </div>
      <h4 class="postit-title">${this.escapeHtml(task.title)}</h4>
      ${descHtml}
      <div class="postit-footer">
        ${timeHtml}
        <span class="postit-importance-tag">${task.importance}</span>
      </div>
    `;

    // Clic en la tarjeta abre el detalle
    card.addEventListener("click", (e) => {
      // Si el clic fue en el botón de estado, no abrir drawer
      if (e.target.closest(".postit-status-btn")) return;
      if (window.modal) window.modal.openDetailDrawer(occ);
    });

    // Clic en el botón de estado: cambiar cíclicamente (not_started -> in_progress -> done -> not_started)
    const statusBtn = card.querySelector(".postit-status-btn");
    statusBtn?.addEventListener("click", async (e) => {
      e.stopPropagation();
      const cycle = {
        not_started: "in_progress",
        in_progress: "done",
        done: "not_started"
      };
      const nextStatus = cycle[occ.status] || "not_started";
      
      try {
        const updated = await api.patch(`/api/occurrences/${occ.id}`, { status: nextStatus });
        occ.status = updated.status;
        
        // Actualizar visualmente la tarjeta de inmediato
        card.className = `postit-card importance-${task.importance} status-${occ.status}`;
        statusBtn.textContent = statusIcons[occ.status];
        statusBtn.title = statusTitles[occ.status];

        showToast(`Estado: ${occ.status === "done" ? "Finalizada ✓" : occ.status === "in_progress" ? "En proceso ◐" : "Sin empezar ○"}`, "info", 1500);
      } catch (err) {
        showToast("Error al cambiar estado", "error");
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
