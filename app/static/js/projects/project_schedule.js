/**
 * Owngarnization — Horario y Planificación por Horas de Proyecto
 */

const projectSchedule = (() => {
  const layoutEl = document.querySelector(".project-layout");
  const projectId = layoutEl?.dataset.projectId;

  let currentMode = "day"; // "day" | "week" | "person"
  let currentDate = new Date();

  function formatDateIso(d) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function getMonday(d) {
    const date = new Date(d);
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(date.setDate(diff));
  }

  async function loadWorkload() {
    if (!projectId) return;
    const monday = getMonday(currentDate);
    const mondayStr = formatDateIso(monday);
    const sunday = new Date(monday);
    sunday.setDate(sunday.getDate() + 6);

    const rangeLabel = document.getElementById("workload-week-range");
    if (rangeLabel) {
      rangeLabel.textContent = `${monday.toLocaleDateString("es-ES", { day: "numeric", month: "short" })} – ${sunday.toLocaleDateString("es-ES", { day: "numeric", month: "short" })}`;
    }

    try {
      const data = await api.get(`/api/projects/${projectId}/workload`, { week: mondayStr });
      const container = document.getElementById("workload-members-list");
      if (!container || !data || !data.members) return;

      if (data.members.length === 0) {
        container.innerHTML = `
          <div class="workload-empty-state">
            <span class="workload-empty-icon">👥</span>
            <span>No hay miembros con horas estimadas en esta semana.</span>
          </div>
        `;
        return;
      }

      container.innerHTML = data.members.map(m => {
        const capacity = m.weekly_hours || 40;
        const percent = Math.min(100, Math.round((m.planned_hours / capacity) * 100));
        const isOverloaded = m.planned_hours > capacity;
        return `
          <div class="workload-member-row">
            <div class="workload-member-info">
              <span class="avatar-circle">${m.username.slice(0, 2).toUpperCase()}</span>
              <strong class="workload-member-name">${m.username}</strong>
            </div>
            <div class="workload-bar-wrapper">
              <div class="project-progress-bar">
                <div class="project-progress-fill ${isOverloaded ? 'is-overloaded' : ''}" style="width: ${percent}%;"></div>
              </div>
            </div>
            <div class="workload-hours-badge ${isOverloaded ? 'badge-danger' : ''}">
              ${m.planned_hours}h / ${m.weekly_hours ? m.weekly_hours + 'h' : '40h'}
              ${isOverloaded ? '<span class="overload-warning-icon" title="Sobrecarga">⚠️</span>' : ''}
            </div>
          </div>
        `;
      }).join("");
    } catch (e) {
      console.warn("Error cargando carga horaria:", e);
      const container = document.getElementById("workload-members-list");
      if (container) {
        container.innerHTML = `
          <div class="workload-empty-state">
            <span>No se pudo cargar la carga horaria semanal.</span>
          </div>
        `;
      }
    }
  }

  async function loadSchedule() {
    if (!projectId) return;
    let startStr, endStr;
    const datePicker = document.getElementById("sched-date-picker");
    const dateLabel = document.getElementById("sched-date-label");

    if (currentMode === "week") {
      const monday = getMonday(currentDate);
      const sunday = new Date(monday);
      sunday.setDate(sunday.getDate() + 6);
      startStr = formatDateIso(monday);
      endStr = formatDateIso(sunday);
      if (dateLabel) dateLabel.textContent = `Semana del ${monday.toLocaleDateString("es-ES", { day: "numeric", month: "long" })}`;
    } else {
      startStr = formatDateIso(currentDate);
      endStr = startStr;
      if (dateLabel) {
        const text = currentDate.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
        dateLabel.textContent = text.charAt(0).toUpperCase() + text.slice(1);
      }
    }

    if (datePicker) datePicker.value = formatDateIso(currentDate);

    try {
      const data = await api.get(`/api/projects/${projectId}/schedule`, {
        start: startStr,
        end: endStr,
        by: currentMode === "person" ? "person" : null
      });

      renderTimeline(data);
    } catch (err) {
      console.warn("Error cargando horario:", err);
      showToast("Error al cargar horario del proyecto", "error");
    }
  }

  function renderTimeline(data) {
    const hoursBody = document.getElementById("timeline-hours-body");
    if (!hoursBody) return;

    // Procesar tareas sin hora
    const untimedBar = document.getElementById("sched-untimed-bar");
    const untimedList = document.getElementById("sched-untimed-tasks");
    const untimedTasks = (data?.tasks || []).filter(item => !item.task.start_time);

    if (untimedTasks.length > 0 && untimedBar && untimedList) {
      untimedBar.style.display = "block";
      untimedList.innerHTML = untimedTasks.map(item => {
        const t = item.task;
        return `
          <div class="untimed-task-chip" data-task-id="${t.id}">
            <span class="untimed-task-dot">📌</span>
            <span class="untimed-task-title">${t.title}</span>
            ${t.role_name ? `<span class="role-tag" style="background-color: ${t.role_color || 'var(--line)'};">${t.role_name}</span>` : ''}
          </div>
        `;
      }).join("");

      untimedList.querySelectorAll(".untimed-task-chip").forEach(chip => {
        chip.addEventListener("click", () => {
          const taskId = chip.dataset.taskId;
          if (taskId && window.projectDrawer) window.projectDrawer.open(parseInt(taskId, 10));
        });
      });
    } else if (untimedBar) {
      untimedBar.style.display = "none";
    }

    // Renderizar horas 07:00 a 22:00
    let html = "";
    for (let h = 7; h <= 22; h++) {
      const timeStr = `${String(h).padStart(2, "0")}:00`;

      // Filtrar tareas que caigan en esta hora
      const tasksInHour = (data?.tasks || []).filter(item => {
        const t = item.task;
        if (!t.start_time) return false;
        const taskHour = parseInt(t.start_time.split(":")[0], 10);
        return taskHour === h;
      });

      const tasksHtml = tasksInHour.map(item => {
        const t = item.task;
        const hasOverlap = item.overlaps && item.overlaps.length > 0;
        const startShort = t.start_time ? t.start_time.slice(0, 5) : "";
        const endShort = t.end_time ? t.end_time.slice(0, 5) : "";
        return `
          <div class="timeline-task-block ${hasOverlap ? 'task-overlap-alert' : ''}" 
               data-task-id="${t.id}">
            <div class="timeline-task-header">
              <span class="timeline-task-time">${startShort}${endShort ? ' – ' + endShort : ''}</span>
              <span class="timeline-task-title">${t.title}</span>
              ${hasOverlap ? '<span class="timeline-task-overlap-badge" title="Conflicto horario">⚠️ Solape</span>' : ''}
            </div>
            <div class="timeline-task-meta">
              ${t.role_name ? `<span class="role-tag" style="background-color: ${t.role_color || 'var(--line)'};">${t.role_name}</span>` : ''}
              <span class="timeline-task-assignees">${(t.assignees || []).map(a => a.username).join(", ") || 'Sin asignar'}</span>
            </div>
          </div>
        `;
      }).join("");

      const emptySlotHtml = tasksInHour.length === 0 ? `
        <div class="timeline-empty-slot" data-hour="${h}">
          <span class="timeline-empty-slot-hint">＋ Añadir a las ${timeStr}</span>
        </div>
      ` : '';

      html += `
        <div class="timeline-hour-row" data-hour="${h}">
          <div class="timeline-hour-label">${timeStr}</div>
          <div class="timeline-hour-content" data-hour="${h}">
            ${tasksHtml}
            ${emptySlotHtml}
          </div>
        </div>
      `;
    }

    hoursBody.innerHTML = html;

    // Delegar clic para abrir drawer de tarea existente
    hoursBody.querySelectorAll(".timeline-task-block").forEach(block => {
      block.addEventListener("click", (e) => {
        e.stopPropagation();
        const taskId = block.dataset.taskId;
        if (taskId && window.projectDrawer) window.projectDrawer.open(parseInt(taskId, 10));
      });
    });

    // Delegar clic para crear tarea en esa hora
    hoursBody.querySelectorAll(".timeline-empty-slot").forEach(slot => {
      slot.addEventListener("click", (e) => {
        e.stopPropagation();
        const hour = slot.dataset.hour;
        const timeStr = `${String(hour).padStart(2, "0")}:00`;
        if (window.projectDrawer) {
          window.projectDrawer.open(null, null, {
            date: formatDateIso(currentDate),
            start_time: timeStr
          });
        }
      });
    });
  }

  function init() {
    if (!projectId) return;

    // Cargar datos inmediatamente
    loadSchedule();
    loadWorkload();

    document.getElementById("sched-btn-today")?.addEventListener("click", () => {
      currentDate = new Date();
      loadSchedule();
      loadWorkload();
    });

    document.getElementById("sched-btn-prev")?.addEventListener("click", () => {
      const step = currentMode === "week" ? 7 : 1;
      currentDate.setDate(currentDate.getDate() - step);
      loadSchedule();
      loadWorkload();
    });

    document.getElementById("sched-btn-next")?.addEventListener("click", () => {
      const step = currentMode === "week" ? 7 : 1;
      currentDate.setDate(currentDate.getDate() + step);
      loadSchedule();
      loadWorkload();
    });

    document.getElementById("sched-date-picker")?.addEventListener("change", (e) => {
      if (e.target.value) {
        currentDate = new Date(e.target.value + "T00:00:00");
        loadSchedule();
        loadWorkload();
      }
    });

    // Modos
    document.querySelectorAll(".view-selector-group .btn-view-toggle").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".view-selector-group .btn-view-toggle").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");
        currentMode = btn.dataset.mode;
        loadSchedule();
      });
    });
  }

  return { init, loadSchedule, loadWorkload };
})();

// Exportar globalmente
window.projectSchedule = projectSchedule;

document.addEventListener("DOMContentLoaded", () => {
  projectSchedule.init();
});
