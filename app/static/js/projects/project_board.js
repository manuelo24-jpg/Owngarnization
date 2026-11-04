/**
 * Owngarnization — Tablero Kanban de Proyectos (SortableJS + Filtros)
 */

document.addEventListener("DOMContentLoaded", () => {
  const layoutEl = document.querySelector(".project-layout");
  const projectId = layoutEl?.dataset.projectId;
  if (!projectId) return;

  const currentUserId = window.currentUserId; // opcionalmente inyectado o deducido

  // Inicializar SortableJS en cada columna
  const columns = document.querySelectorAll(".sortable-column");
  columns.forEach(colEl => {
    new Sortable(colEl, {
      group: "kanban",
      animation: 150,
      ghostClass: "sortable-ghost",
      dragClass: "sortable-drag",
      delay: 150,
      delayOnTouchOnly: true,
      onEnd: async (evt) => {
        const itemEl = evt.item;
        const taskId = parseInt(itemEl.dataset.taskId, 10);
        const targetColId = parseInt(evt.to.dataset.columnId, 10);
        const newPos = evt.newIndex;

        try {
          await api.post(`/api/projects/${projectId}/tasks/move`, {
            task_id: taskId,
            column_id: targetColId,
            position: newPos
          });
          updateColumnCounts();
        } catch (err) {
          showToast(err.message || "Error al mover tarea", "error");
        }
      }
    });
  });

  function updateColumnCounts() {
    document.querySelectorAll(".kanban-column").forEach(col => {
      const countEl = col.querySelector(".kanban-column-count");
      const tasksContainer = col.querySelector(".kanban-column-tasks");
      const tasks = col.querySelectorAll(".kanban-task-card");
      if (countEl) countEl.textContent = tasks.length;

      let emptyEl = col.querySelector(".kanban-column-empty");
      if (tasks.length === 0) {
        if (!emptyEl && tasksContainer) {
          emptyEl = document.createElement("div");
          emptyEl.className = "kanban-column-empty";
          emptyEl.innerHTML = '<span class="empty-drop-text">Arrastra o añade una tarea aquí</span>';
          tasksContainer.appendChild(emptyEl);
        } else if (emptyEl) {
          emptyEl.style.display = "flex";
        }
      } else if (emptyEl) {
        emptyEl.style.display = "none";
      }
    });
  }

  // Clic en tarjetas para abrir el drawer
  document.getElementById("kanban-board")?.addEventListener("click", (e) => {
    const card = e.target.closest(".kanban-task-card");
    if (card) {
      const taskId = parseInt(card.dataset.taskId, 10);
      if (taskId) projectDrawer.open(taskId);
      return;
    }

    const addBtn = e.target.closest(".kanban-add-task-btn");
    if (addBtn) {
      const colId = parseInt(addBtn.dataset.columnId, 10);
      projectDrawer.open(null, colId);
      return;
    }

    const delColBtn = e.target.closest(".btn-delete-col");
    if (delColBtn) {
      const colId = delColBtn.dataset.columnId;
      if (confirm("¿Eliminar esta columna y reasignar sus tareas?")) {
        api.delete(`/api/projects/${projectId}/columns/${colId}`)
          .then(() => {
            showToast("Columna eliminada", "info");
            window.location.reload();
          })
          .catch(err => showToast(err.message, "error"));
      }
    }
  });

  // Modal para Añadir Columna
  const addColBtn = document.getElementById("btn-add-column");
  const modalCol = document.getElementById("modal-column");
  const formCol = document.getElementById("form-column");
  const closeColBtn = document.getElementById("modal-col-close");
  const cancelColBtn = document.getElementById("btn-cancel-column");

  addColBtn?.addEventListener("click", () => {
    formCol.reset();
    document.getElementById("col-id").value = "";
    modalCol.style.display = "flex";
    document.getElementById("col-name").focus();
  });

  function closeColModal() {
    modalCol.style.display = "none";
  }

  closeColBtn?.addEventListener("click", closeColModal);
  cancelColBtn?.addEventListener("click", closeColModal);
  modalCol?.addEventListener("click", (e) => { if (e.target === modalCol) closeColModal(); });

  formCol?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("col-name").value.trim();
    if (!name) return;

    try {
      await api.post(`/api/projects/${projectId}/columns`, {
        name,
        is_done: document.getElementById("col-is-done").checked
      });
      showToast("Columna creada", "success");
      window.location.reload();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // Filtros del tablero
  const searchInput = document.getElementById("board-search");
  const prioritySelect = document.getElementById("board-filter-priority");
  const memberSelect = document.getElementById("board-filter-member");
  const roleSelect = document.getElementById("board-filter-role");

  function applyFilters() {
    const q = searchInput?.value.toLowerCase().trim() || "";
    const priority = prioritySelect?.value || "";
    const member = memberSelect?.value || "";
    const role = roleSelect?.value || "";

    document.querySelectorAll(".kanban-task-card").forEach(card => {
      const title = card.querySelector(".kanban-task-title")?.textContent.toLowerCase() || "";
      const cardPriority = card.dataset.priority || "";
      const cardRoleId = card.dataset.roleId || "";
      const assigneeIds = (card.dataset.assigneeIds || "").split(",").filter(Boolean);

      let matchText = !q || title.includes(q);
      let matchPriority = !priority || cardPriority === priority;
      let matchRole = !role || cardRoleId === role;
      let matchMember = true;

      if (member === "unassigned") {
        matchMember = assigneeIds.length === 0;
      } else if (member === "my_tasks") {
        matchMember = assigneeIds.includes(String(window.currentUserUserId));
      } else if (member) {
        matchMember = assigneeIds.includes(member);
      }

      card.style.display = (matchText && matchPriority && matchRole && matchMember) ? "block" : "none";
    });
  }

  searchInput?.addEventListener("input", applyFilters);
  prioritySelect?.addEventListener("change", applyFilters);
  memberSelect?.addEventListener("change", applyFilters);
  roleSelect?.addEventListener("change", applyFilters);

  // Eventos de sincronización tras guardar/borrar en drawer
  window.addEventListener("project:task-created", () => window.location.reload());
  window.addEventListener("project:task-updated", () => window.location.reload());
  window.addEventListener("project:task-deleted", () => window.location.reload());
});

