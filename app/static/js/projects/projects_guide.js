/**
 * Owngarnization — Manual de Usuario de Proyectos (Interactivo)
 */

const projectsGuide = {
  init() {
    const modal = document.getElementById("projects-guide-modal");
    const openBtn = document.getElementById("btn-guide");
    const closeBtn = document.getElementById("projects-guide-close-btn");
    const okBtn = document.getElementById("projects-guide-ok-btn");

    openBtn?.addEventListener("click", () => this.open());
    closeBtn?.addEventListener("click", () => this.close());
    okBtn?.addEventListener("click", () => this.close());

    modal?.addEventListener("click", (e) => {
      if (e.target === modal) this.close();
    });

    // Pestañas temáticas del manual de proyectos
    document.querySelectorAll(".projects-guide-tab-btn").forEach(tabBtn => {
      tabBtn.addEventListener("click", () => {
        const targetId = tabBtn.dataset.tab;
        document.querySelectorAll(".projects-guide-tab-btn").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        document.querySelectorAll(".projects-guide-panel").forEach(p => {
          p.classList.remove("active");
          p.style.display = "none";
        });

        tabBtn.classList.add("active");
        tabBtn.setAttribute("aria-selected", "true");

        const targetPanel = document.getElementById(targetId);
        if (targetPanel) {
          targetPanel.classList.add("active");
          targetPanel.style.display = "block";
        }

        const contentEl = modal?.querySelector(".guide-content");
        if (contentEl) contentEl.scrollTop = 0;
      });
    });

    // Atajo ? para abrir y Esc para cerrar
    window.addEventListener("keydown", (e) => {
      const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
      if (["input", "textarea", "select"].includes(activeTag)) return;

      if (e.key === "?" && modal && modal.style.display === "none") {
        e.preventDefault();
        this.open();
      } else if (e.key === "Escape" && modal && modal.style.display !== "none") {
        this.close();
      }
    });
  },

  open() {
    const modal = document.getElementById("projects-guide-modal");
    if (!modal) return;
    modal.style.display = "flex";
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  },

  close() {
    const modal = document.getElementById("projects-guide-modal");
    if (!modal) return;
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }
};

window.projectsGuide = projectsGuide;

document.addEventListener("DOMContentLoaded", () => {
  projectsGuide.init();
});

