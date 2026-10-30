/**
 * Owngarnization — Manual de Usuario Interactivo (Modal & Tabs)
 * Soporta tanto el Manual Web (guide_modal.html) como el Manual Móvil (mobile_guide_modal.html).
 */

const guide = {
  init() {
    document.getElementById("btn-guide")?.addEventListener("click", () => this.open());
    document.getElementById("guide-close-btn")?.addEventListener("click", () => this.close());
    document.getElementById("guide-ok-btn")?.addEventListener("click", () => this.close());

    const guideModal = document.getElementById("guide-modal");
    guideModal?.addEventListener("click", (e) => {
      if (e.target === guideModal) this.close();
    });

    // Pestañas temáticas del manual de usuario
    document.querySelectorAll(".guide-tab-btn").forEach(tabBtn => {
      tabBtn.addEventListener("click", () => {
        const targetId = tabBtn.dataset.tab;
        document.querySelectorAll(".guide-tab-btn").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        document.querySelectorAll(".guide-panel").forEach(p => p.classList.remove("active"));

        tabBtn.classList.add("active");
        tabBtn.setAttribute("aria-selected", "true");

        const targetPanel = document.getElementById(targetId);
        if (targetPanel) targetPanel.classList.add("active");

        const contentEl = guideModal?.querySelector(".guide-content");
        if (contentEl) contentEl.scrollTop = 0;
      });
    });
  },

  open() {
    const guideModal = document.getElementById("guide-modal");
    if (!guideModal) return;
    guideModal.style.display = "flex";
    guideModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  },

  close() {
    const guideModal = document.getElementById("guide-modal");
    if (!guideModal) return;
    guideModal.style.display = "none";
    guideModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
};

window.guide = guide;
