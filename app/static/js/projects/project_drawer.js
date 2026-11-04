/**
 * Owngarnization — Task Drawer de Proyectos
 */

const projectDrawer = (() => {
  const drawer = document.getElementById("project-task-drawer");
  const overlay = document.getElementById("drawer-overlay");
  const form = document.getElementById("project-task-form");
  const closeBtn = document.getElementById("project-drawer-close");
  const deleteBtn = document.getElementById("btn-delete-drawer-task");
  const overlapAlert = document.getElementById("drawer-overlap-alert");
  const overlapMsg = document.getElementById("drawer-overlap-msg");

  const layoutEl = document.querySelector(".project-layout");
  const projectId = layoutEl?.dataset.projectId;

  let currentTaskId = null;

  function close() {
    drawer.style.display = "none";
    overlay.style.display = "none";
    currentTaskId = null;
    form.reset();
    overlapAlert.style.display = "none";
  }

  function renderOverlapWarnings(warnings) {
    if (!warnings || warnings.length === 0) {
      overlapAlert.style.display = "none";
      return;
    }
    overlapAlert.style.display = "block";
    overlapMsg.innerHTML = warnings.map(w => 
      `<div>• ${w.username} ya tiene programada "<strong>${w.conflicting_title}</strong>" de ${w.start_time.slice(0,5)} a ${w.end_time.slice(0,5)}.</div>`
    ).join("");
  }

  async function open(taskId = null, defaultColId = null) {
    currentTaskId = taskId;
    form.reset();
    overlapAlert.style.display = "none";

    // Marcar checks de asignados en false
    document.querySelectorAll(".assignee-checkbox").forEach(cb => cb.checked = false);

    if (taskId) {
      deleteBtn.style.display = "inline-block";
      document.getElementById("btn-save-drawer-task").textContent = "Guardar cambios";
      try {
        const task = await api.get(`/api/projects/${projectId}/tasks/${taskId}`);
        document.getElementById("pdrawer-task-id").value = task.id;
        document.getElementById("pdrawer-title").value = task.title;
        document.getElementById("pdrawer-desc").value = task.description || "";
        document.getElementById("pdrawer-column").value = task.column_id;
        document.getElementById("pdrawer-priority").value = task.priority;
        document.getElementById("pdrawer-role").value = task.role_id || "";
        document.getElementById("pdrawer-date").value = task.date || "";
        document.getElementById("pdrawer-start").value = task.start_time ? task.start_time.slice(0,5) : "";
        document.getElementById("pdrawer-end").value = task.end_time ? task.end_time.slice(0,5) : "";
        document.getElementById("pdrawer-due").value = task.due_date || "";
        document.getElementById("pdrawer-minutes").value = task.estimated_minutes || "";

        // Marcar asignados
        if (task.assignee_ids) {
          task.assignee_ids.forEach(uid => {
            const cb = document.querySelector(`.assignee-checkbox[value="${uid}"]`);
            if (cb) cb.checked = true;
          });
        }

        renderOverlapWarnings(task.overlap_warnings);
      } catch (err) {
        showToast("Error al cargar detalle de tarea", "error");
        return;
      }
    } else {
      deleteBtn.style.display = "none";
      document.getElementById("btn-save-drawer-task").textContent = "Crear tarea";
      document.getElementById("pdrawer-task-id").value = "";
      if (defaultColId) {
        document.getElementById("pdrawer-column").value = defaultColId;
      }
    }

    drawer.style.display = "flex";
    overlay.style.display = "block";
    document.getElementById("pdrawer-title").focus();
  }

  // Event Listeners
  closeBtn?.addEventListener("click", close);
  overlay?.addEventListener("click", close);

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && drawer.style.display !== "none") {
      close();
    }
  });

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("pdrawer-title").value.trim();
    if (!title) return;

    const selectedAssignees = Array.from(document.querySelectorAll(".assignee-checkbox:checked"))
      .map(cb => parseInt(cb.value, 10));

    const roleVal = document.getElementById("pdrawer-role").value;
    const minutesVal = document.getElementById("pdrawer-minutes").value;

    const payload = {
      title,
      description: document.getElementById("pdrawer-desc").value.trim() || null,
      column_id: parseInt(document.getElementById("pdrawer-column").value, 10),
      priority: document.getElementById("pdrawer-priority").value,
      role_id: roleVal ? parseInt(roleVal, 10) : null,
      date: document.getElementById("pdrawer-date").value || null,
      start_time: document.getElementById("pdrawer-start").value ? `${document.getElementById("pdrawer-start").value}:00` : null,
      end_time: document.getElementById("pdrawer-end").value ? `${document.getElementById("pdrawer-end").value}:00` : null,
      due_date: document.getElementById("pdrawer-due").value || null,
      estimated_minutes: minutesVal ? parseInt(minutesVal, 10) : null,
      assignee_ids: selectedAssignees
    };

    try {
      let savedTask;
      if (currentTaskId) {
        savedTask = await api.patch(`/api/projects/${projectId}/tasks/${currentTaskId}`, payload);
        showToast("Tarea actualizada", "success");
        window.dispatchEvent(new CustomEvent("project:task-updated", { detail: savedTask }));
      } else {
        savedTask = await api.post(`/api/projects/${projectId}/tasks`, payload);
        showToast("Tarea creada", "success");
        window.dispatchEvent(new CustomEvent("project:task-created", { detail: savedTask }));
      }

      if (savedTask.overlap_warnings && savedTask.overlap_warnings.length > 0) {
        renderOverlapWarnings(savedTask.overlap_warnings);
        showToast("Atención: Hay solapes horarios en la tarea", "info");
      } else {
        close();
      }
    } catch (err) {
      showToast(err.message || "Error al guardar tarea", "error");
    }
  });

  deleteBtn?.addEventListener("click", async () => {
    if (!currentTaskId) return;
    if (!confirm("¿Eliminar esta tarea del proyecto?")) return;

    try {
      await api.delete(`/api/projects/${projectId}/tasks/${currentTaskId}`);
      showToast("Tarea eliminada", "info");
      window.dispatchEvent(new CustomEvent("project:task-deleted", { detail: { taskId: currentTaskId } }));
      close();
    } catch (err) {
      showToast(err.message || "Error al eliminar tarea", "error");
    }
  });

  return { open, close };
})();

