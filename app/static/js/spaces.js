/**
 * Owngarnization — Selector de Espacios (/spaces)
 */

document.addEventListener("DOMContentLoaded", () => {
  const personalCard = document.getElementById("card-personal");
  const projectsCard = document.getElementById("card-projects");
  const rememberCheckbox = document.getElementById("remember-space-choice");
  const personalSummary = document.getElementById("personal-summary-text");
  const projectsSummary = document.getElementById("projects-summary-text");
  const logoutBtn = document.getElementById("spaces-logout-btn");

  function checkIsMobile() {
    return window.location.pathname.startsWith("/m") ||
      window.innerWidth <= 768 ||
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  }

  // Cargar métricas resumen para alimentar las tarjetas en vivo
  async function loadSummary() {
    try {
      const data = await api.get("/api/spaces/summary");
      if (data && data.personal && personalSummary) {
        personalSummary.textContent = `${data.personal.today_total} tareas para hoy (${data.personal.today_done} completadas)`;
      }
      if (data && data.projects && projectsSummary) {
        projectsSummary.textContent = `${data.projects.active_projects} proyectos activos (${data.projects.assigned_tasks} tareas asignadas)`;
      }
    } catch (err) {
      if (personalSummary) personalSummary.textContent = "Listo para organizar tu día";
      if (projectsSummary) projectsSummary.textContent = "Gestiona tus proyectos y equipos";
    }
  }

  async function selectSpace(spaceType) {
    const remember = rememberCheckbox?.checked;
    if (remember) {
      try {
        await api.patch("/api/me/space", { last_space: spaceType });
      } catch (e) {
        console.error("Error al guardar preferencia de espacio:", e);
      }
    }

    const isMobile = checkIsMobile();
    if (spaceType === "personal") {
      window.location.href = isMobile ? "/m" : "/";
    } else {
      window.location.href = isMobile ? "/m/projects" : "/projects";
    }
  }

  personalCard?.addEventListener("click", (e) => {
    e.preventDefault();
    selectSpace("personal");
  });

  projectsCard?.addEventListener("click", (e) => {
    e.preventDefault();
    selectSpace("projects");
  });

  logoutBtn?.addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      if (window.pwaManager) window.pwaManager.clearApiCache();
      await fetch("/auth/logout", { method: "POST" });
    } catch {
      // fallback
    } finally {
      window.location.href = "/login";
    }
  });

  loadSummary();
});
