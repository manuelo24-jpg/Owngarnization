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
        container.innerHTML = `<p style="font-size: 0.85rem; color: var(--ink-soft);">No hay miembros registrados.</p>`;
        return;
      }

      container.innerHTML = data.members.map(m => {
        const capacity = m.weekly_hours || 40;
        const percent = Math.min(100, Math.round((m.planned_hours / capacity) * 100));
        const isOverloaded = m.planned_hours > capacity;
        return `
          <div class="workload-member-row">
            <div style="display: flex; align-items: center; gap: 0.5rem; width: 180px;">
              <span class="avatar-circle" style="width: 24px; height: 24px; font-size: 0.7rem;">${m.username.slice(0,2)}</span>
              <strong>${m.username}</strong>
            </div>
            <div style="flex-grow: 1; margin: 0 1rem;">
              <div class="project-progress-bar" style="height: 6px;">
                <div class="project-progress-fill" style="width: ${percent}%; background-color: ${isOverloaded ? 'var(--danger)' : 'var(--accent-strong)'};"></div>
              </div>
            </div>
            <div style="font-size: 0.82rem; font-weight: 500; min-width: 110px; text-align: right;">
              ${m.planned_hours}h / ${m.weekly_hours ? m.weekly_hours + 'h' : '—'}
              ${isOverloaded ? '<span style="color: var(--danger); margin-left: 4px;">⚠️</span>' : ''}
            </div>
          </div>
        `;
      }).join("");
    } catch (e) {
      console.warn("Error cargando carga horaria:", e);
    }
  }

  async function loadSchedule() {
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
      if (dateLabel) dateLabel.textContent = currentDate.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
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
      showToast("Error al cargar horario del proyecto", "error");
    }
  }

  function renderTimeline(data) {
    const hoursBody = document.getElementById("timeline-hours-body");
    if (!hoursBody) return;

    // Renderizar horas 07:00 a 22:00
    let html = "";
    for (let h = 7; h <= 22; h++) {
      const timeStr = `${String(h).padStart(2, "0")}:00`;
      
      // Filtrar tareas que caigan en esta hora
      const tasksInHour = (data.tasks || []).filter(item => {
        const t = item.task;
        if (!t.start_time) return false;
        const taskHour = parseInt(t.start_time.split(":")[0], 10);
        return taskHour === h;
      });

      const tasksHtml = tasksInHour.map(item => {
        const t = item.task;
        const hasOverlap = item.overlaps && item.overlaps.length > 0;
        const startShort = t.start_time ? t.start_time.slice(0,5) : "";
        const endShort = t.end_time ? t.end_time.slice(0,5) : "";
        return `
          <div class="timeline-task-block ${hasOverlap ? 'task-overlap-alert' : ''}" 
               data-task-id="${t.id}"
               style="background: #fdfbf7; border: 1px solid var(--line); border-left: 4px solid var(--accent-strong); border-radius: var(--radius-sm); padding: 0.4rem 0.6rem; margin-bottom: 4px; cursor: pointer;">
            <div style="font-size: 0.82rem; font-weight: 600; color: var(--ink);">
              ${startShort}${endShort ? '–' + endShort : ''} · ${t.title}
              ${hasOverlap ? '<span style="color: var(--danger); font-size: 0.8rem; margin-left: 4px;" title="Conflicto horario">⚠️ Solape</span>' : ''}
            </div>
            <div style="font-size: 0.72rem; color: var(--ink-soft); display: flex; gap: 0.5rem; margin-top: 2px;">
              ${t.role_name ? `<span class="role-tag" style="padding: 1px 4px; font-size: 0.68rem;">${t.role_name}</span>` : ''}
              <span>${t.assignees.map(a => a.username).join(", ") || 'Sin asignar'}</span>
            </div>
          </div>
        `;
      }).join("");

      html += `
        <div class="timeline-hour-row">
          <div class="timeline-hour-label">${timeStr}</div>
          <div class="timeline-hour-content" data-hour="${h}">
            ${tasksHtml}
          </div>
        </div>
      `;
    }

    hoursBody.innerHTML = html;

    // Delegar clic para abrir drawer
    hoursBody.querySelectorAll(".timeline-task-block").forEach(block => {
      block.addEventListener("click", () => {
        const taskId = block.dataset.taskId;
        if (taskId) projectDrawer.open(parseInt(taskId, 10));
      });
    });
  }

  function init() {
    if (!projectId) return;

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
        document.querySelectorAll(".view-selector-group .btn-view-toggle").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentMode = btn.dataset.mode;
        loadSchedule();
      });
    });
  }

  return { init, loadSchedule, loadWorkload };
})();

document.addEventListener("DOMContentLoaded", () => {
  projectSchedule.init();
});

