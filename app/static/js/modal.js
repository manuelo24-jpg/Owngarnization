/**
 * Owngarnization — Coordinador Global de Modales y Atajos
 * Orquesta taskModal, drawer y guide manteniendo compatibilidad global.
 */

const modal = {
  init() {
    if (window.taskModal) window.taskModal.init();
    if (window.drawer) window.drawer.init();
    if (window.guide) window.guide.init();
    this.initConfirmModal();

    this.bindGlobalShortcuts();
  },

  initConfirmModal() {
    const modalEl = document.getElementById("confirm-modal");
    if (!modalEl) return;

    modalEl.addEventListener("click", (e) => {
      if (e.target === modalEl) this.closeConfirmModal();
    });

    document.getElementById("confirm-modal-close-btn")?.addEventListener("click", () => {
      this.closeConfirmModal();
    });

    document.getElementById("confirm-modal-cancel-btn")?.addEventListener("click", () => {
      this.closeConfirmModal();
    });
  },

  _confirmCallback: null,

  showConfirm({ title, message, taskTitle, confirmText, onConfirm }) {
    const modalEl = document.getElementById("confirm-modal");
    if (!modalEl) return;

    const titleEl = document.getElementById("confirm-modal-title");
    const msgEl = document.getElementById("confirm-modal-message");
    const previewEl = document.getElementById("confirm-modal-task-preview");
    const taskTitleEl = document.getElementById("confirm-modal-task-title");
    const acceptBtn = document.getElementById("confirm-modal-accept-btn");

    if (titleEl && title) titleEl.textContent = title;
    if (msgEl && message) msgEl.textContent = message;
    if (acceptBtn && confirmText) acceptBtn.textContent = confirmText;

    if (taskTitleEl && previewEl) {
      if (taskTitle) {
        taskTitleEl.textContent = taskTitle;
        previewEl.style.display = "flex";
      } else {
        previewEl.style.display = "none";
      }
    }

    this._confirmCallback = onConfirm;

    if (acceptBtn) {
      acceptBtn.onclick = async () => {
        if (typeof this._confirmCallback === "function") {
          const cb = this._confirmCallback;
          this._confirmCallback = null;
          this.closeConfirmModal();
          await cb();
        } else {
          this.closeConfirmModal();
        }
      };
    }

    modalEl.style.display = "flex";
    modalEl.setAttribute("aria-hidden", "false");
  },

  closeConfirmModal() {
    const modalEl = document.getElementById("confirm-modal");
    if (!modalEl) return;
    modalEl.style.display = "none";
    modalEl.setAttribute("aria-hidden", "true");
    this._confirmCallback = null;
  },

  bindGlobalShortcuts() {
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closeAll();
      } else if ((e.key === "n" || e.key === "N") && !this.isTypingInInput(e)) {
        e.preventDefault();
        this.openTaskModal("create");
      } else if (e.key === "?" && !this.isTypingInInput(e)) {
        e.preventDefault();
        this.openGuideModal();
      }
    });
  },

  isTypingInInput(e) {
    const tag = e.target.tagName.toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select";
  },

  closeAll() {
    this.closeConfirmModal();
    this.closeTaskModal();
    this.closeDetailDrawer();
    this.closeGuideModal();
    if (window.pushManagerClient) window.pushManagerClient.closeModal();
    if (window.appState) window.appState.closeMobileFilters();
  },

  // Proxies para compatibilidad con código existente
  openTaskModal(mode = "create", occ = null) {
    if (window.taskModal) window.taskModal.open(mode, occ);
  },

  closeTaskModal() {
    if (window.taskModal) window.taskModal.close();
  },

  openDetailDrawer(occ) {
    if (window.drawer) window.drawer.open(occ);
  },

  closeDetailDrawer() {
    if (window.drawer) window.drawer.close();
  },

  openGuideModal() {
    if (window.guide) window.guide.open();
  },

  closeGuideModal() {
    if (window.guide) window.guide.close();
  }
};

window.modal = modal;
