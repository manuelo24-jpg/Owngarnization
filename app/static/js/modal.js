/**
 * Owngarnization — Gestión de Modales y Panel Deslizante (Drawer)
 */

const modal = {
  activeOccurrence: null,
  activeTask: null,

  init() {
    this.bindEvents();
  },

  bindEvents() {
    // Cerrar modal de tarea
    document.getElementById("modal-close-btn")?.addEventListener("click", () => this.closeTaskModal());
    document.getElementById("modal-cancel-btn")?.addEventListener("click", () => this.closeTaskModal());

    // Clic fuera del modal para cerrar
    const taskModal = document.getElementById("task-modal");
    taskModal?.addEventListener("click", (e) => {
      if (e.target === taskModal) this.closeTaskModal();
    });

    // Envío del formulario de tarea
    document.getElementById("task-form")?.addEventListener("submit", (e) => this.handleTaskSubmit(e));

    // Cambio dinámico en el selector de Tipo (mostrar/ocultar fecha o selector de días)
    const kindSelect = document.getElementById("task-kind");
    kindSelect?.addEventListener("change", (e) => {
      const dateGroup = document.getElementById("date-group");
      const daysGroup = document.getElementById("days-of-week-group");
      const isCommon = e.target.value === "common";
      if (dateGroup) dateGroup.style.display = isCommon ? "none" : "flex";
      if (daysGroup) daysGroup.style.display = isCommon ? "flex" : "none";
    });

    // Clic en chips de días de la semana
    document.querySelectorAll("#day-selector-chips .day-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        chip.classList.toggle("active");
        // Asegurar que al menos uno quede activo
        const activeCount = document.querySelectorAll("#day-selector-chips .day-chip.active").length;
        if (activeCount === 0) {
          chip.classList.add("active");
        }
      });
    });

    // Botones rápidos de selección de días
    document.querySelectorAll(".quick-days-btns button").forEach(btn => {
      btn.addEventListener("click", () => {
        const type = btn.dataset.days;
        const chips = document.querySelectorAll("#day-selector-chips .day-chip");
        chips.forEach(chip => {
          const day = parseInt(chip.dataset.day, 10);
          if (type === "all") {
            chip.classList.add("active");
          } else if (type === "weekdays") {
            chip.classList.toggle("active", day >= 1 && day <= 5);
          } else if (type === "weekend") {
            chip.classList.toggle("active", day === 6 || day === 7);
          }
        });
      });
    });

    // Cerrar panel lateral (Drawer)
    document.getElementById("drawer-close-btn")?.addEventListener("click", () => this.closeDetailDrawer());

    // Botones de cambio de estado rápido en el Drawer
    document.querySelectorAll(".status-opt").forEach(btn => {
      btn.addEventListener("click", () => {
        const newStatus = btn.dataset.status;
        this.updateOccurrenceStatus(newStatus);
      });
    });

    // Botón de Editar en el Drawer
    document.getElementById("drawer-edit-btn")?.addEventListener("click", () => {
      if (this.activeOccurrence) {
        this.closeDetailDrawer();
        this.openTaskModal("edit", this.activeOccurrence);
      }
    });

    // Botón de Eliminar en el Drawer
    document.getElementById("drawer-delete-btn")?.addEventListener("click", () => {
      if (this.activeOccurrence) {
        this.deleteTask(this.activeOccurrence.task.id);
      }
    });

    // Atajos de teclado globales
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closeTaskModal();
        this.closeDetailDrawer();
      } else if ((e.key === "n" || e.key === "N") && !this.isTypingInInput(e)) {
        e.preventDefault();
        this.openTaskModal("create");
      }
    });
  },

  isTypingInInput(e) {
    const tag = e.target.tagName.toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select";
  },

  // --- MODAL DE TAREA (CREAR / EDITAR) ---

  openTaskModal(mode = "create", occ = null) {
    const taskModal = document.getElementById("task-modal");
    const form = document.getElementById("task-form");
    const titleEl = document.getElementById("modal-title");
    const errorBox = document.getElementById("modal-error-box");
    const dateGroup = document.getElementById("date-group");
    const daysGroup = document.getElementById("days-of-week-group");

    if (!taskModal || !form) return;

    form.reset();
    errorBox.style.display = "none";
    this.activeOccurrence = occ;

    // Obtener la fecha seleccionada en el tablero (o hoy)
    const selectedDate = window.appState ? window.appState.getCurrentDateFormatted() : new Date().toISOString().split("T")[0];

    // Resetear chips de días a todos activos por defecto
    document.querySelectorAll("#day-selector-chips .day-chip").forEach(c => c.classList.add("active"));

    if (mode === "create") {
      titleEl.textContent = "Nueva tarea";
      document.getElementById("task-form-id").value = "";
      document.getElementById("task-kind").value = "daily";
      document.getElementById("task-date").value = selectedDate;
      document.getElementById("task-importance").value = "medium";
      document.getElementById("task-status").value = "not_started";
      if (dateGroup) dateGroup.style.display = "flex";
      if (daysGroup) daysGroup.style.display = "none";
    } else if (mode === "edit" && occ) {
      titleEl.textContent = "Editar tarea";
      const task = occ.task;
      document.getElementById("task-form-id").value = task.id;
      document.getElementById("task-title").value = task.title;
      document.getElementById("task-description").value = task.description || "";
      document.getElementById("task-kind").value = task.kind;
      document.getElementById("task-date").value = task.date || selectedDate;
      document.getElementById("task-importance").value = task.importance;
      document.getElementById("task-status").value = occ.status;
      document.getElementById("task-start-time").value = occ.start_time || task.start_time || "";
      document.getElementById("task-end-time").value = occ.end_time || task.end_time || "";

      const isCommon = task.kind === "common";
      if (dateGroup) dateGroup.style.display = isCommon ? "none" : "flex";
      if (daysGroup) {
        daysGroup.style.display = isCommon ? "flex" : "none";
        // Marcar los chips de días correspondientes
        if (task.days_of_week) {
          const allowed = task.days_of_week.split(",").map(s => s.trim());
          document.querySelectorAll("#day-selector-chips .day-chip").forEach(chip => {
            chip.classList.toggle("active", allowed.includes(chip.dataset.day));
          });
        } else {
          document.querySelectorAll("#day-selector-chips .day-chip").forEach(chip => chip.classList.add("active"));
        }
      }
    }

    taskModal.style.display = "flex";
    taskModal.setAttribute("aria-hidden", "false");
    document.getElementById("task-title")?.focus();
  },


  closeTaskModal() {
    const taskModal = document.getElementById("task-modal");
    if (taskModal) {
      taskModal.style.display = "none";
      taskModal.setAttribute("aria-hidden", "true");
    }
  },

  async handleTaskSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const errorBox = document.getElementById("modal-error-box");
    const submitBtn = document.getElementById("modal-submit-btn");

    errorBox.style.display = "none";
    submitBtn.disabled = true;

    const taskId = document.getElementById("task-form-id").value;
    const isEdit = Boolean(taskId);

    const kind = form.kind.value;
    const payload = {
      title: form.title.value.trim(),
      description: form.description.value.trim() || null,
      kind: kind,
      importance: form.importance.value,
      date: kind === "daily" ? (form.date.value || null) : null,
      start_time: form.start_time.value || null,
      end_time: form.end_time.value || null,
      days_of_week: null,
    };

    if (kind === "common") {
      const activeChips = Array.from(document.querySelectorAll("#day-selector-chips .day-chip.active"));
      if (activeChips.length === 0) {
        errorBox.textContent = "Debes seleccionar al menos un día para la tarea común";
        errorBox.style.display = "block";
        submitBtn.disabled = false;
        return;
      }
      if (activeChips.length === 7) {
        payload.days_of_week = null; // Todos los días
      } else {
        payload.days_of_week = activeChips.map(c => c.dataset.day).sort((a, b) => Number(a) - Number(b)).join(",");
      }
    }

    if (!isEdit) {
      payload.initial_status = form.initial_status.value;
    }

    // Validación horaria en cliente
    if (payload.start_time && payload.end_time && payload.end_time <= payload.start_time) {
      errorBox.textContent = "La hora de fin debe ser posterior a la de inicio";
      errorBox.style.display = "block";
      submitBtn.disabled = false;
      return;
    }

    try {
      if (isEdit) {
        await api.patch(`/api/tasks/${taskId}`, payload);
        // Si además cambió el estado, actualizar la ocurrencia activa
        if (this.activeOccurrence && form.initial_status.value !== this.activeOccurrence.status) {
          await api.patch(`/api/occurrences/${this.activeOccurrence.id}`, {
            status: form.initial_status.value,
            start_time: payload.start_time,
            end_time: payload.end_time
          });
        }
        showToast("Tarea actualizada correctamente", "success");
      } else {
        await api.post("/api/tasks", payload);
        showToast("Tarea creada correctamente", "success");
      }

      this.closeTaskModal();
      // Recargar datos en la vista activa
      if (window.appState) {
        window.appState.reloadCurrentView();
      }
    } catch (err) {
      errorBox.textContent = err.message || "Error al procesar la tarea";
      errorBox.style.display = "block";
    } finally {
      submitBtn.disabled = false;
    }
  },

  // --- PANEL LATERAL DESLIZANTE (DETAIL DRAWER) ---

  openDetailDrawer(occ) {
    this.activeOccurrence = occ;
    const drawer = document.getElementById("detail-drawer");
    if (!drawer) return;

    const task = occ.task;

    // Título y badges
    document.getElementById("drawer-title").textContent = task.title;

    const kindBadge = document.getElementById("drawer-kind-badge");
    const dayNames = { "1": "L", "2": "M", "3": "X", "4": "J", "5": "V", "6": "S", "7": "D" };
    if (task.kind === "common") {
      let daysText = "Todos los días";
      if (task.days_of_week) {
        const daysArr = task.days_of_week.split(",").map(d => dayNames[d.trim()] || d);
        daysText = daysArr.join(", ");
      }
      kindBadge.textContent = `🔁 Común (${daysText})`;
    } else {
      kindBadge.textContent = "📌 Del día";
    }


    const impBadge = document.getElementById("drawer-importance-badge");
    const impLabels = { low: "Baja", medium: "Media", high: "Alta", urgent: "Urgente" };
    impBadge.textContent = `Importancia: ${impLabels[task.importance] || task.importance}`;
    impBadge.className = `badge pi-${task.importance}`;

    // Fecha
    const dateLabel = document.getElementById("drawer-date-label");
    const [year, month, day] = occ.date.split("-");
    const dateObj = new Date(year, month - 1, day);
    dateLabel.textContent = dateObj.toLocaleDateString("es-ES", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric"
    });

    // Horario
    const scheduleBlock = document.getElementById("drawer-schedule-block");
    const startTime = occ.start_time || task.start_time;
    const endTime = occ.end_time || task.end_time;
    if (startTime || endTime) {
      scheduleBlock.style.display = "flex";
      const startStr = startTime ? startTime.substring(0, 5) : "";
      const endStr = endTime ? endTime.substring(0, 5) : "";
      document.getElementById("drawer-time-label").textContent = `${startStr} - ${endStr}`;
    } else {
      scheduleBlock.style.display = "none";
    }

    // Descripción
    const descEl = document.getElementById("drawer-description");
    if (task.description && task.description.trim()) {
      descEl.textContent = task.description;
      descEl.style.fontStyle = "normal";
    } else {
      descEl.textContent = "Sin descripción adicional.";
      descEl.style.fontStyle = "italic";
    }

    // Botones de estado activo
    document.querySelectorAll(".status-opt").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.status === occ.status);
    });

    drawer.style.display = "flex";
    drawer.setAttribute("aria-hidden", "false");
  },

  closeDetailDrawer() {
    const drawer = document.getElementById("detail-drawer");
    if (drawer) {
      drawer.style.display = "none";
      drawer.setAttribute("aria-hidden", "true");
    }
  },

  async updateOccurrenceStatus(newStatus) {
    if (!this.activeOccurrence) return;

    try {
      const updated = await api.patch(`/api/occurrences/${this.activeOccurrence.id}`, {
        status: newStatus
      });
      this.activeOccurrence.status = updated.status;

      // Actualizar botones en el drawer
      document.querySelectorAll(".status-opt").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.status === newStatus);
      });

      showToast("Estado actualizado", "info");

      // Refrescar tablero o calendario
      if (window.appState) {
        window.appState.reloadCurrentView();
      }
    } catch (err) {
      showToast(err.message || "Error al cambiar estado", "error");
    }
  },

  async deleteTask(taskId) {
    if (!confirm("¿Seguro que deseas eliminar esta tarea?")) return;

    try {
      await api.delete(`/api/tasks/${taskId}`);
      showToast("Tarea eliminada", "info");
      this.closeDetailDrawer();

      if (window.appState) {
        window.appState.reloadCurrentView();
      }
    } catch (err) {
      showToast(err.message || "Error al eliminar tarea", "error");
    }
  }
};

// Exponer globalmente
window.modal = modal;
