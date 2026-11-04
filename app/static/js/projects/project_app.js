/**
 * Owngarnization — Coordinador Global del Espacio de Proyecto
 */

document.addEventListener("DOMContentLoaded", () => {
  const tabBoard = document.getElementById("tab-btn-board");
  const tabSchedule = document.getElementById("tab-btn-schedule");
  const tabPeople = document.getElementById("tab-btn-people");

  const mobileTabBoard = document.getElementById("mobile-tab-board");
  const mobileTabSchedule = document.getElementById("mobile-tab-schedule");
  const mobileTabPeople = document.getElementById("mobile-tab-people");

  const viewBoard = document.getElementById("project-view-board");
  const viewSchedule = document.getElementById("project-view-schedule");
  const viewPeople = document.getElementById("project-view-people");

  const dropdownBtn = document.getElementById("btn-project-dropdown");
  const dropdownMenu = document.getElementById("project-dropdown-menu");

  const btnNewTask = document.getElementById("btn-project-new-task");
  const mobileFab = document.getElementById("btn-project-mobile-fab");
  const btnNewProjectDropdown = document.getElementById("btn-new-project-dropdown");
  const modalProject = document.getElementById("modal-project");

  function switchTab(tabName) {
    [tabBoard, tabSchedule, tabPeople].forEach(btn => {
      if (btn) {
        const isActive = btn.dataset.tab === tabName;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", isActive);
      }
    });

    [mobileTabBoard, mobileTabSchedule, mobileTabPeople].forEach(btn => {
      if (btn) {
        const isActive = btn.dataset.tab === tabName;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", isActive);
      }
    });

    // Controlar visibilidad del FAB flotante
    if (mobileFab) {
      mobileFab.style.display = tabName === "people" ? "none" : "flex";
    }

    if (viewBoard) viewBoard.style.display = tabName === "board" ? "flex" : "none";
    if (viewSchedule) {
      viewSchedule.style.display = tabName === "schedule" ? "flex" : "none";
      if (tabName === "schedule" && window.projectSchedule) {
        window.projectSchedule.loadSchedule();
        window.projectSchedule.loadWorkload();
      }
    }
    if (viewPeople) viewPeople.style.display = tabName === "people" ? "block" : "none";
  }

  tabBoard?.addEventListener("click", () => switchTab("board"));
  tabSchedule?.addEventListener("click", () => switchTab("schedule"));
  tabPeople?.addEventListener("click", () => switchTab("people"));

  mobileTabBoard?.addEventListener("click", () => switchTab("board"));
  mobileTabSchedule?.addEventListener("click", () => switchTab("schedule"));
  mobileTabPeople?.addEventListener("click", () => switchTab("people"));

  // Apertura de Drawer desde FAB móvil
  mobileFab?.addEventListener("click", () => {
    const firstCol = document.querySelector(".kanban-column");
    const colId = firstCol ? parseInt(firstCol.dataset.columnId, 10) : null;
    projectDrawer.open(null, colId);
  });

  // Dropdown selector de proyecto
  dropdownBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    dropdownMenu?.classList.toggle("show");
  });

  document.addEventListener("click", () => {
    dropdownMenu?.classList.remove("show");
  });

  // Botón nueva tarea
  btnNewTask?.addEventListener("click", () => {
    const firstCol = document.querySelector(".kanban-column");
    const colId = firstCol ? parseInt(firstCol.dataset.columnId, 10) : null;
    projectDrawer.open(null, colId);
  });

  // Nuevo proyecto desde dropdown
  const formProject = document.getElementById("form-project");
  const closeProjectBtn = document.getElementById("modal-project-close");
  const cancelProjectBtn = document.getElementById("btn-cancel-project");
  const colorInput = document.getElementById("project-color");
  const colorBadge = document.getElementById("project-color-badge") || document.getElementById("project-color-preview");
  const iconInput = document.getElementById("project-icon");

  function openNewProjectModal() {
    if (!modalProject) return;
    formProject?.reset();
    const pid = document.getElementById("project-id");
    if (pid) pid.value = "";
    const title = document.getElementById("modal-project-title");
    if (title) title.textContent = "Nuevo proyecto";
    const currentBadge = document.getElementById("project-color-badge") || colorBadge;
    if (currentBadge) currentBadge.style.backgroundColor = "#C9B49A";
    if (colorInput) colorInput.value = "#C9B49A";
    if (iconInput) iconInput.value = "📁";
    modalProject.querySelectorAll(".emoji-pill, .emoji-quick-btn").forEach((b, idx) => b.classList.toggle("active", idx === 0));
    modalProject.querySelectorAll(".color-pill, .color-quick-btn").forEach((b, idx) => b.classList.toggle("active", idx === 0));
    modalProject.style.display = "flex";
    setTimeout(() => document.getElementById("project-name")?.focus(), 50);
  }

  function closeNewProjectModal() {
    if (modalProject) modalProject.style.display = "none";
  }

  btnNewProjectDropdown?.addEventListener("click", (e) => {
    e.preventDefault();
    openNewProjectModal();
  });

  closeProjectBtn?.addEventListener("click", closeNewProjectModal);
  cancelProjectBtn?.addEventListener("click", closeNewProjectModal);
  modalProject?.addEventListener("click", (e) => {
    if (e.target === modalProject) closeNewProjectModal();
  });

  // Pickers en modalProject
  modalProject?.querySelectorAll(".emoji-pill, .emoji-quick-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const emoji = btn.dataset.emoji;
      if (!emoji) return;
      if (iconInput) {
        iconInput.value = emoji;
        iconInput.dispatchEvent(new Event("change", { bubbles: true }));
      }
      modalProject.querySelectorAll(".emoji-pill, .emoji-quick-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });

  modalProject?.querySelectorAll(".color-pill, .color-quick-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = btn.dataset.target || "project-color";
      const input = document.getElementById(targetId);
      const badge = document.getElementById(`${targetId}-badge`) || document.getElementById(`${targetId}-preview`);
      if (input) {
        input.value = btn.dataset.color;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
      if (badge) badge.style.backgroundColor = btn.dataset.color;
      btn.parentElement.querySelectorAll(".color-pill, .color-quick-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });

  colorInput?.addEventListener("input", (e) => {
    const currentBadge = document.getElementById("project-color-badge") || colorBadge;
    if (currentBadge) currentBadge.style.backgroundColor = e.target.value;
    modalProject?.querySelectorAll('.color-pill, .color-quick-btn').forEach(b => {
      b.classList.toggle("active", (b.dataset.color || "").toLowerCase() === e.target.value.toLowerCase());
    });
  });

  iconInput?.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    modalProject?.querySelectorAll('.emoji-pill, .emoji-quick-btn').forEach(b => {
      b.classList.toggle("active", b.dataset.emoji === val);
    });
  });

  formProject?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("project-name").value.trim();
    if (!name) return;

    const submitBtn = document.getElementById("btn-save-project");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Guardando...";
    }

    const payload = {
      name,
      description: document.getElementById("project-desc")?.value.trim() || null,
      icon: document.getElementById("project-icon")?.value.trim() || "📁",
      color: document.getElementById("project-color")?.value || "#C9B49A"
    };

    try {
      const res = await api.post("/api/projects", payload);
      if (res && res.id) {
        showToast("Proyecto creado con éxito", "success");
        const isMobile = window.location.pathname.startsWith("/m") || window.innerWidth <= 768;
        window.location.href = isMobile ? `/m/projects/${res.id}` : `/projects/${res.id}`;
      }
    } catch (err) {
      showToast(err.message || "Error al crear proyecto", "error");
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Guardar proyecto";
      }
    }
  });

  // Atajos de teclado (1, 2, 3, N, Esc)
  window.addEventListener("keydown", (e) => {
    const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
    if (["input", "textarea", "select"].includes(activeTag)) return;

    if (e.key === "1") switchTab("board");
    if (e.key === "2") switchTab("schedule");
    if (e.key === "3") switchTab("people");
    if (e.key.toLowerCase() === "n") {
      e.preventDefault();
      btnNewTask?.click();
    }
  });
});

