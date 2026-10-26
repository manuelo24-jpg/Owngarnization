/**
 * Owngarnization — Panel Deslizante de Detalle (Detail Drawer)
 * Controla la visualización de detalles, cambios rápidos de estado y eliminación.
 */

const drawer = {
  activeOccurrence: null,

  init() {
    document.getElementById("drawer-close-btn")?.addEventListener("click", () => this.close());

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
        const occ = this.activeOccurrence;
        this.close();
        if (window.taskModal) {
          window.taskModal.open("edit", occ);
        } else if (window.modal) {
          window.modal.openTaskModal("edit", occ);
        }
      }
    });

    // Botón de Eliminar en el Drawer
    document.getElementById("drawer-delete-btn")?.addEventListener("click", () => {
      if (this.activeOccurrence) {
        this.deleteTask(this.activeOccurrence.task.id);
      }
    });
  },

  open(occ) {
    this.activeOccurrence = occ;
    const el = document.getElementById("detail-drawer");
    if (!el) return;

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

    el.style.display = "flex";
    el.setAttribute("aria-hidden", "false");
  },

  close() {
    const el = document.getElementById("detail-drawer");
    if (el) {
      el.style.display = "none";
      el.setAttribute("aria-hidden", "true");
    }
  },

  async updateOccurrenceStatus(newStatus) {
    if (!this.activeOccurrence) return;

    try {
      const updated = await api.patch(`/api/occurrences/${this.activeOccurrence.id}`, {
        status: newStatus
      });
      this.activeOccurrence.status = updated.status;

      document.querySelectorAll(".status-opt").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.status === newStatus);
      });

      showToast("Estado actualizado", "info");

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
      this.close();

      if (window.appState) {
        window.appState.reloadCurrentView();
      }
    } catch (err) {
      showToast(err.message || "Error al eliminar tarea", "error");
    }
  }
};

window.drawer = drawer;
