/**
 * Owngarnization — Personas, Roles y Permisos de Proyecto
 */

document.addEventListener("DOMContentLoaded", () => {
  const layoutEl = document.querySelector(".project-layout");
  const projectId = layoutEl?.dataset.projectId;
  if (!projectId) return;

  // --- MODAL INVITAR MIEMBRO ---
  const inviteModal = document.getElementById("modal-invite-member");
  const inviteForm = document.getElementById("form-invite-member");
  const openInviteBtn = document.getElementById("btn-open-invite");
  const closeInviteBtn = document.getElementById("modal-invite-close");
  const cancelInviteBtn = document.getElementById("btn-cancel-invite");

  openInviteBtn?.addEventListener("click", () => {
    inviteForm.reset();
    inviteModal.style.display = "flex";
    document.getElementById("invite-email").focus();
  });

  function closeInvite() { inviteModal.style.display = "none"; }
  closeInviteBtn?.addEventListener("click", closeInvite);
  cancelInviteBtn?.addEventListener("click", closeInvite);
  inviteModal?.addEventListener("click", (e) => { if (e.target === inviteModal) closeInvite(); });

  inviteForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("invite-email").value.trim();
    if (!email) return;

    const roleVal = document.getElementById("invite-role").value;
    const hoursVal = document.getElementById("invite-hours").value;

    const payload = {
      email,
      permission: document.getElementById("invite-permission").value,
      role_id: roleVal ? parseInt(roleVal, 10) : null,
      weekly_hours: hoursVal ? parseInt(hoursVal, 10) : null
    };

    try {
      await api.post(`/api/projects/${projectId}/members`, payload);
      showToast("Miembro invitado con éxito", "success");
      closeInvite();
      window.location.reload();
    } catch (err) {
      showToast(err.message || "Error al invitar", "error");
    }
  });

  // --- MODAL CREAR ROL ---
  const roleModal = document.getElementById("modal-role");
  const roleForm = document.getElementById("form-role");
  const openRoleBtn = document.getElementById("btn-open-create-role");
  const closeRoleBtn = document.getElementById("modal-role-close");
  const cancelRoleBtn = document.getElementById("btn-cancel-role");
  const roleColorInput = document.getElementById("role-color");
  const roleColorPreview = document.getElementById("role-color-preview");

  roleModal?.querySelectorAll(".color-pill, .color-quick-btn").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = btn.dataset.target || "role-color";
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

  roleColorInput?.addEventListener("input", (e) => {
    const badge = document.getElementById("role-color-badge") || roleColorPreview;
    if (badge) badge.style.backgroundColor = e.target.value;
    roleModal?.querySelectorAll('.color-pill, .color-quick-btn').forEach(b => {
      b.classList.toggle("active", (b.dataset.color || "").toLowerCase() === e.target.value.toLowerCase());
    });
  });

  openRoleBtn?.addEventListener("click", () => {
    roleForm.reset();
    document.getElementById("role-id").value = "";
    const badge = document.getElementById("role-color-badge") || roleColorPreview;
    if (badge) badge.style.backgroundColor = "#C9B49A";
    if (roleColorInput) roleColorInput.value = "#C9B49A";
    roleModal?.querySelectorAll(".color-pill, .color-quick-btn").forEach((b, idx) => b.classList.toggle("active", idx === 0));
    roleModal.style.display = "flex";
    document.getElementById("role-name").focus();
  });

  function closeRole() { roleModal.style.display = "none"; }
  closeRoleBtn?.addEventListener("click", closeRole);
  cancelRoleBtn?.addEventListener("click", closeRole);
  roleModal?.addEventListener("click", (e) => { if (e.target === roleModal) closeRole(); });

  roleForm?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("role-name").value.trim();
    if (!name) return;

    try {
      await api.post(`/api/projects/${projectId}/roles`, {
        name,
        color: document.getElementById("role-color").value || "#C9B49A"
      });
      showToast("Rol creado", "success");
      closeRole();
      window.location.reload();
    } catch (err) {
      showToast(err.message, "error");
    }
  });

  // --- ELIMINAR / EXPULSAR MIEMBRO ---
  document.getElementById("project-members-tbody")?.addEventListener("click", async (e) => {
    const remBtn = e.target.closest(".btn-remove-member");
    if (remBtn) {
      const uid = remBtn.dataset.userId;
      if (confirm("¿Estás seguro de expulsar a este miembro del proyecto?")) {
        try {
          await api.delete(`/api/projects/${projectId}/members/${uid}`);
          showToast("Miembro expulsado", "info");
          window.location.reload();
        } catch (err) {
          showToast(err.message, "error");
        }
      }
      return;
    }

    const leaveBtn = e.target.closest(".btn-leave-project");
    if (leaveBtn) {
      const uid = leaveBtn.dataset.userId;
      if (confirm("¿Deseas abandonar este proyecto?")) {
        try {
          await api.delete(`/api/projects/${projectId}/members/${uid}`);
          showToast("Has salido del proyecto", "info");
          window.location.href = "/projects";
        } catch (err) {
          showToast(err.message, "error");
        }
      }
    }
  });

  // --- ELIMINAR ROL ---
  document.getElementById("project-roles-list")?.addEventListener("click", async (e) => {
    const delBtn = e.target.closest(".btn-delete-role");
    if (delBtn) {
      const roleId = delBtn.dataset.roleId;
      if (confirm("¿Eliminar este rol de equipo? Los miembros asignados quedarán sin rol.")) {
        try {
          await api.delete(`/api/projects/${projectId}/roles/${roleId}`);
          showToast("Rol eliminado", "info");
          window.location.reload();
        } catch (err) {
          showToast(err.message, "error");
        }
      }
    }
  });

  // --- BORRAR PROYECTO (OWNER) ---
  document.getElementById("btn-delete-project-action")?.addEventListener("click", async () => {
    if (confirm("¿Estás seguro de eliminar este proyecto por completo? Esta acción lo archivará.")) {
      try {
        await api.delete(`/api/projects/${projectId}`);
        showToast("Proyecto eliminado", "info");
        window.location.href = "/projects";
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  });
});

