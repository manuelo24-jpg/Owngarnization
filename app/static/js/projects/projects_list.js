/**
 * Owngarnization — Listado de Proyectos (/projects)
 */

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("modal-project");
  const form = document.getElementById("form-project");
  const openBtn = document.getElementById("btn-open-create-project");
  const emptyOpenBtn = document.getElementById("btn-empty-create-project");
  const closeBtn = document.getElementById("modal-project-close");
  const cancelBtn = document.getElementById("btn-cancel-project");
  const iconInput = document.getElementById("project-icon");
  const colorInput = document.getElementById("project-color");
  const colorBadge = document.getElementById("project-color-badge") || document.getElementById("project-color-preview");

  function setupPickers() {
    // Emoji quick picks
    modal?.querySelectorAll(".emoji-pill, .emoji-quick-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const emoji = btn.dataset.emoji;
        if (!emoji) return;
        if (iconInput) {
          iconInput.value = emoji;
          iconInput.dispatchEvent(new Event("change", { bubbles: true }));
        }
        modal.querySelectorAll(".emoji-pill, .emoji-quick-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
      });
    });

    // Color quick picks
    modal?.querySelectorAll(".color-pill, .color-quick-btn").forEach(btn => {
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

    // Color input direct change (native color picker)
    colorInput?.addEventListener("input", (e) => {
      const currentBadge = document.getElementById("project-color-badge") || colorBadge;
      if (currentBadge) currentBadge.style.backgroundColor = e.target.value;
      modal?.querySelectorAll('.color-pill, .color-quick-btn').forEach(b => {
        b.classList.toggle("active", (b.dataset.color || "").toLowerCase() === e.target.value.toLowerCase());
      });
    });

    // Icon input direct change (typing an emoji)
    iconInput?.addEventListener("input", (e) => {
      const val = e.target.value.trim();
      modal?.querySelectorAll('.emoji-pill, .emoji-quick-btn').forEach(b => {
        b.classList.toggle("active", b.dataset.emoji === val);
      });
    });
  }

  setupPickers();

  function openModal() {
    form.reset();
    document.getElementById("project-id").value = "";
    document.getElementById("modal-project-title").textContent = "Nuevo proyecto";
    const currentBadge = document.getElementById("project-color-badge") || colorBadge;
    if (currentBadge) currentBadge.style.backgroundColor = "#C9B49A";
    if (colorInput) colorInput.value = "#C9B49A";
    if (iconInput) iconInput.value = "📁";
    modal?.querySelectorAll(".emoji-pill, .emoji-quick-btn").forEach((b, idx) => b.classList.toggle("active", idx === 0));
    modal?.querySelectorAll(".color-pill, .color-quick-btn").forEach((b, idx) => b.classList.toggle("active", idx === 0));
    modal.style.display = "flex";
    setTimeout(() => document.getElementById("project-name")?.focus(), 50);
  }

  function closeModal() {
    modal.style.display = "none";
  }

  openBtn?.addEventListener("click", openModal);
  emptyOpenBtn?.addEventListener("click", openModal);
  closeBtn?.addEventListener("click", closeModal);
  cancelBtn?.addEventListener("click", closeModal);

  modal?.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.style.display !== "none") {
      closeModal();
    }
  });

  form?.addEventListener("submit", async (e) => {
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
      description: document.getElementById("project-desc").value.trim() || null,
      icon: document.getElementById("project-icon").value.trim() || "📁",
      color: document.getElementById("project-color").value || "#C9B49A"
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
});
