/**
 * Owngarnization — Coordinador Global de Modales y Atajos
 * Orquesta taskModal, drawer y guide manteniendo compatibilidad global.
 */

const modal = {
  init() {
    if (window.taskModal) window.taskModal.init();
    if (window.drawer) window.drawer.init();
    if (window.guide) window.guide.init();

    this.bindGlobalShortcuts();
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
    this.closeTaskModal();
    this.closeDetailDrawer();
    this.closeGuideModal();
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
