/**
 * Owngarnization — Formulario Modal de Tareas (Crear / Editar)
 * Gestiona validaciones horarias, selección de periodicidad por días y envíos.
 */

const taskModal = {
  activeOccurrence: null,

  init() {
    document.getElementById("modal-close-btn")?.addEventListener("click", () => this.close());
    document.getElementById("modal-cancel-btn")?.addEventListener("click", () => this.close());

    const modalEl = document.getElementById("task-modal");
    modalEl?.addEventListener("click", (e) => {
      if (e.target === modalEl) this.close();
    });

    document.getElementById("task-form")?.addEventListener("submit", (e) => this.handleSubmit(e));

    // Selector de tipo: alternar entre fecha puntual o selector de días
    const kindSelect = document.getElementById("task-kind");
    kindSelect?.addEventListener("change", (e) => {
      const dateGroup = document.getElementById("date-group");
      const daysGroup = document.getElementById("days-of-week-group");
      const isCommon = e.target.value === "common";
      if (dateGroup) dateGroup.style.display = isCommon ? "none" : "flex";
      if (daysGroup) daysGroup.style.display = isCommon ? "flex" : "none";
    });

    // Chips de selección de días
    document.querySelectorAll("#day-selector-chips .day-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        chip.classList.toggle("active");
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
  },

  open(mode = "create", occ = null) {
    const modalEl = document.getElementById("task-modal");
    const form = document.getElementById("task-form");
    const titleEl = document.getElementById("modal-title");
    const errorBox = document.getElementById("modal-error-box");
    const dateGroup = document.getElementById("date-group");
    const daysGroup = document.getElementById("days-of-week-group");

    if (!modalEl || !form) return;

    form.reset();
    if (errorBox) errorBox.style.display = "none";
    this.activeOccurrence = occ;

    // Resetear chips de días a activos por defecto
    document.querySelectorAll("#day-selector-chips .day-chip").forEach(c => c.classList.add("active"));

    if (mode === "create") {
      titleEl.textContent = "Nueva tarea";
      document.getElementById("task-form-id").value = "";

      const defaultDate = window.appState ? window.appState.getCurrentDateFormatted() : new Date().toISOString().split("T")[0];
      const taskDateInput = document.getElementById("task-date");
      if (taskDateInput) taskDateInput.value = defaultDate;

      if (dateGroup) dateGroup.style.display = "flex";
      if (daysGroup) daysGroup.style.display = "none";
    } else if (mode === "edit" && occ) {
      titleEl.textContent = "Editar tarea";
      const task = occ.task;

      document.getElementById("task-form-id").value = task.id;
      document.getElementById("task-title").value = task.title;
      document.getElementById("task-description").value = task.description || "";
      document.getElementById("task-kind").value = task.kind;
      document.getElementById("task-importance").value = task.importance;
      document.getElementById("task-status").value = occ.status;

      const startTime = occ.start_time || task.start_time;
      const endTime = occ.end_time || task.end_time;
      document.getElementById("task-start-time").value = startTime ? startTime.substring(0, 5) : "";
      document.getElementById("task-end-time").value = endTime ? endTime.substring(0, 5) : "";

      const isCommon = task.kind === "common";
      if (dateGroup) dateGroup.style.display = isCommon ? "none" : "flex";
      if (daysGroup) daysGroup.style.display = isCommon ? "flex" : "none";

      const taskDateInput = document.getElementById("task-date");
      if (taskDateInput) taskDateInput.value = occ.date;

      if (isCommon && task.days_of_week) {
        const allowed = task.days_of_week.split(",").map(x => x.trim());
        document.querySelectorAll("#day-selector-chips .day-chip").forEach(chip => {
          chip.classList.toggle("active", allowed.includes(chip.dataset.day));
        });
      }
    }

    modalEl.style.display = "flex";
    modalEl.setAttribute("aria-hidden", "false");
    document.getElementById("task-title")?.focus();
  },

  close() {
    const modalEl = document.getElementById("task-modal");
    if (modalEl) {
      modalEl.style.display = "none";
      modalEl.setAttribute("aria-hidden", "true");
    }
  },

  async handleSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const submitBtn = document.getElementById("modal-submit-btn");
    const errorBox = document.getElementById("modal-error-box");
    const taskId = document.getElementById("task-form-id").value;
    const isEdit = Boolean(taskId);

    submitBtn.disabled = true;
    errorBox.style.display = "none";

    const payload = {
      title: form.title.value.trim(),
      description: form.description.value.trim() || null,
      kind: form.kind.value,
      importance: form.importance.value,
      start_time: form.start_time.value || null,
      end_time: form.end_time.value || null
    };

    if (payload.kind === "daily") {
      payload.date = form.date.value || null;
      payload.days_of_week = null;
    } else {
      payload.date = null;
      const activeChips = Array.from(document.querySelectorAll("#day-selector-chips .day-chip.active"));
      if (activeChips.length === 0) {
        errorBox.textContent = "Debes seleccionar al menos un día para la tarea común";
        errorBox.style.display = "block";
        submitBtn.disabled = false;
        return;
      }
      if (activeChips.length === 7) {
        payload.days_of_week = null;
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

      this.close();
      if (window.appState) {
        window.appState.reloadCurrentView();
      }
    } catch (err) {
      errorBox.textContent = err.message || "Error al procesar la tarea";
      errorBox.style.display = "block";
    } finally {
      submitBtn.disabled = false;
    }
  }
};

window.taskModal = taskModal;
