/**
 * Owngarnization — Registro PWA, Detección Standalone y Descarga de App Móvil
 * Soporta tanto la página dedicada de descarga (/download) como la App Móvil (/m).
 */

const pwaManager = {
  deferredPrompt: null,
  DISMISS_KEY: "owngarnization_pwa_dismiss_until",

  init() {
    this.registerServiceWorker();
    this.setupInstallHandlers();
    this.setupDownloadPage();
  },

  async registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    try {
      await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    } catch (err) {
      console.warn("No se pudo registrar el Service Worker:", err);
    }
  },

  isStandalone() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true
    );
  },

  isIOS() {
    const ua = window.navigator.userAgent || "";
    const iOSDevice = /iPad|iPhone|iPod/.test(ua);
    const iPadOS = navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
    return iOSDevice || iPadOS;
  },

  isDismissedRecently() {
    const until = localStorage.getItem(this.DISMISS_KEY);
    if (!until) return false;
    return Date.now() < Number(until);
  },

  dismissBanner() {
    const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
    localStorage.setItem(this.DISMISS_KEY, String(Date.now() + sevenDaysMs));
    const banner = document.getElementById("pwa-install-banner");
    if (banner) banner.style.display = "none";
  },

  setupInstallHandlers() {
    const banner = document.getElementById("pwa-install-banner");
    const installBtn = document.getElementById("btn-pwa-install");
    const dismissBtn = document.getElementById("btn-pwa-dismiss");
    const bannerDesc = document.getElementById("pwa-banner-desc");

    dismissBtn?.addEventListener("click", () => this.dismissBanner());

    // Capturar evento nativo de instalación en Android / Chrome / Edge
    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      this.deferredPrompt = e;

      // Actualizar botón de la página /download si estamos en ella
      this.updateDownloadPageInstallState(true);

      // Mostrar banner en /m si no está instalada ni descartada
      if (banner && !this.isStandalone() && !this.isDismissedRecently()) {
        if (installBtn) installBtn.style.display = "inline-flex";
        banner.style.display = "flex";
      }
    });

    installBtn?.addEventListener("click", async () => {
      await this.triggerInstallPrompt();
    });

    window.addEventListener("appinstalled", () => {
      this.deferredPrompt = null;
      if (banner) banner.style.display = "none";
      this.updateDownloadPageInstalled();
      if (typeof showToast === "function") {
        showToast("¡App Móvil instalada correctamente!", "success");
      }
    });

    // En iOS Safari dentro de /m mostrar guía breve si no está en modo standalone
    if (banner && !this.isStandalone() && !this.isDismissedRecently() && this.isIOS()) {
      if (installBtn) installBtn.style.display = "none";
      if (bannerDesc) {
        bannerDesc.innerHTML = 'En Safari pulsa <strong>Compartir ⬆️</strong> y elige <strong>"Añadir a pantalla de inicio"</strong>.';
      }
      banner.style.display = "flex";
    }
  },

  setupDownloadPage() {
    const downloadBtn = document.getElementById("btn-download-install");
    const iosBadge = document.getElementById("ios-highlight-badge");
    if (!downloadBtn) return;

    if (this.isIOS() && iosBadge) {
      iosBadge.style.display = "inline-block";
    }

    if (this.isStandalone()) {
      this.updateDownloadPageInstalled();
    }

    downloadBtn.addEventListener("click", async () => {
      if (this.deferredPrompt) {
        await this.triggerInstallPrompt();
      } else {
        window.location.href = "/m";
      }
    });
  },

  updateDownloadPageInstallState(ready) {
    const downloadBtn = document.getElementById("btn-download-install");
    const statusEl = document.getElementById("download-install-status");
    if (!downloadBtn) return;

    if (ready) {
      downloadBtn.textContent = "📲 Instalar App Móvil ahora";
      if (statusEl) {
        statusEl.textContent = "Tu navegador permite instalar la App Móvil directamente con un clic.";
      }
    }
  },

  updateDownloadPageInstalled() {
    const downloadBtn = document.getElementById("btn-download-install");
    const statusEl = document.getElementById("download-install-status");
    if (downloadBtn) {
      downloadBtn.textContent = "✅ Abrir App Móvil";
      downloadBtn.onclick = () => {
        window.location.href = "/m";
      };
    }
    if (statusEl) {
      statusEl.textContent = "La App Móvil ya está instalada en este dispositivo.";
    }
  },

  async triggerInstallPrompt() {
    if (!this.deferredPrompt) return false;
    this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;
    this.deferredPrompt = null;
    const banner = document.getElementById("pwa-install-banner");
    if (outcome === "accepted" && banner) {
      banner.style.display = "none";
    }
    return outcome === "accepted";
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.pwaManager = pwaManager;
  pwaManager.init();
});
