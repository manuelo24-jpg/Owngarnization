/**
 * Owngarnization — Gestión de Notificaciones Web Push y Preferencias de Recordatorio
 */

const pushManagerClient = {
  vapidPublicKey: null,
  configured: false,
  currentSubscription: null,

  init() {
    this.bindModalEvents();
    this.syncTimezoneAndSubscriptionSilently();
  },

  bindModalEvents() {
    const openBtn = document.getElementById("btn-notifications");
    const closeBtn = document.getElementById("notif-modal-close-btn");
    const modalEl = document.getElementById("notification-settings-modal");
    const saveBtn = document.getElementById("btn-save-notif-prefs");
    const testBtn = document.getElementById("btn-test-push");
    const toggleDeviceBtn = document.getElementById("btn-toggle-device-push");
    const enabledCheck = document.getElementById("notif-enabled-check");
    const offsetSelect = document.getElementById("notif-offset-select");

    openBtn?.addEventListener("click", () => this.openModal());
    closeBtn?.addEventListener("click", () => this.closeModal());

    modalEl?.addEventListener("click", (e) => {
      if (e.target === modalEl) this.closeModal();
    });

    toggleDeviceBtn?.addEventListener("click", () => this.toggleDeviceSubscription());
    testBtn?.addEventListener("click", () => this.sendTestNotification());
    saveBtn?.addEventListener("click", () => this.savePreferences({ closeOnSave: true }));

    // Guardado automático al cambiar opciones para que no se pierdan si cierra el modal directamente
    enabledCheck?.addEventListener("change", () => this.savePreferences({ silent: true }));
    offsetSelect?.addEventListener("change", () => this.savePreferences({ silent: true }));
  },

  async ensureServiceWorkerReady() {
    if (!("serviceWorker" in navigator)) return null;
    let reg = await navigator.serviceWorker.getRegistration("/");
    if (!reg) {
      reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    }
    return await navigator.serviceWorker.ready;
  },

  async syncTimezoneAndSubscriptionSilently() {
    try {
      const detectedTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const tzKey = "owngarnization_synced_tz";
      if (detectedTz && sessionStorage.getItem(tzKey) !== detectedTz) {
        const prefs = await api.get("/api/me/preferences");
        if (prefs && prefs.timezone !== detectedTz) {
          await api.patch("/api/me/preferences", { timezone: detectedTz });
        }
        sessionStorage.setItem(tzKey, detectedTz);
      }

      // Si el navegador ya tiene permiso y suscripción activa, asegurar que el backend la tenga registrada
      const subKey = "owngarnization_synced_sub";
      if (
        !sessionStorage.getItem(subKey) &&
        "serviceWorker" in navigator &&
        "PushManager" in window &&
        "Notification" in window &&
        Notification.permission === "granted"
      ) {
        const reg = await this.ensureServiceWorkerReady();
        const sub = reg ? await reg.pushManager.getSubscription() : null;
        if (sub) {
          const subJson = sub.toJSON();
          if (subJson?.endpoint && subJson?.keys?.p256dh && subJson?.keys?.auth) {
            await api.post("/api/push/subscriptions", {
              endpoint: subJson.endpoint,
              keys: {
                p256dh: subJson.keys.p256dh,
                auth: subJson.keys.auth
              },
              user_agent: navigator.userAgent
            });
            sessionStorage.setItem(subKey, "1");
          }
        }
      }
    } catch {
      // Ignorar errores silenciosos en el arranque
    }
  },

  async openModal() {
    const modalEl = document.getElementById("notification-settings-modal");
    if (!modalEl) return;

    modalEl.style.display = "flex";
    modalEl.setAttribute("aria-hidden", "false");

    await this.loadStateIntoModal();
  },

  closeModal() {
    const modalEl = document.getElementById("notification-settings-modal");
    if (!modalEl) return;
    modalEl.style.display = "none";
    modalEl.setAttribute("aria-hidden", "true");
  },

  async loadStateIntoModal() {
    const enabledCheck = document.getElementById("notif-enabled-check");
    const offsetSelect = document.getElementById("notif-offset-select");
    const tzInput = document.getElementById("notif-timezone-display");

    try {
      const [keyInfo, prefs] = await Promise.all([
        api.get("/api/push/public-key"),
        api.get("/api/me/preferences")
      ]);

      this.vapidPublicKey = keyInfo?.public_key || keyInfo?.publicKey || "";
      this.configured = Boolean(this.vapidPublicKey);

      if (prefs) {
        if (enabledCheck) enabledCheck.checked = Boolean(prefs.reminders_enabled);
        if (offsetSelect) offsetSelect.value = String(prefs.reminder_offset_min ?? 0);
        if (tzInput) {
          const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Madrid";
          tzInput.value = prefs.timezone || browserTz;
        }
      }

      await this.refreshDeviceSubscriptionUI();
    } catch (err) {
      console.error("Error al cargar configuración de notificaciones:", err);
      showToast("No se pudo cargar la configuración de avisos", "error");
    }
  },

  async refreshDeviceSubscriptionUI() {
    const statusBox = document.getElementById("notif-permission-status");
    const toggleBtn = document.getElementById("btn-toggle-device-push");
    const testBtn = document.getElementById("btn-test-push");
    const iosWarning = document.getElementById("notif-ios-warning");

    const isIOS = window.pwaManager?.isIOS();
    const isStandalone = window.pwaManager?.isStandalone();

    if (isIOS && !isStandalone) {
      if (iosWarning) iosWarning.style.display = "block";
    } else if (iosWarning) {
      iosWarning.style.display = "none";
    }

    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
      if (statusBox) {
        statusBox.textContent = isIOS && !isStandalone
          ? "📱 Abre la app desde el icono de tu pantalla de inicio para activar avisos en iPhone"
          : "No compatible en este navegador (en iPhone requiere iOS 16.4+ e instalar desde Safari)";
      }
      if (toggleBtn) toggleBtn.disabled = true;
      if (testBtn) testBtn.disabled = true;
      return;
    }

    if (Notification.permission === "denied") {
      if (statusBox) {
        statusBox.textContent = "🚫 Permiso bloqueado en los ajustes del teléfono/navegador";
      }
      if (toggleBtn) {
        toggleBtn.textContent = "Permiso denegado";
        toggleBtn.disabled = true;
      }
      if (testBtn) testBtn.disabled = true;
      return;
    }

    try {
      const reg = await this.ensureServiceWorkerReady();
      const sub = reg ? await reg.pushManager.getSubscription() : null;
      this.currentSubscription = sub;

      if (sub) {
        if (statusBox) {
          statusBox.textContent = "✅ Avisos activos en este dispositivo";
        }
        if (toggleBtn) {
          toggleBtn.textContent = "Desactivar avisos en este dispositivo";
          toggleBtn.disabled = false;
        }
        if (testBtn) testBtn.disabled = false;
      } else {
        if (statusBox) {
          statusBox.textContent = this.configured
            ? "🔕 Avisos inactivos en este dispositivo (pulsa abajo para activar)"
            : "⚠️ Falta configurar claves VAPID en el servidor";
        }
        if (toggleBtn) {
          toggleBtn.textContent = "Activar avisos en este dispositivo";
          toggleBtn.disabled = !this.configured;
        }
        if (testBtn) testBtn.disabled = true;
      }
    } catch (err) {
      console.error("Error comprobando Service Worker:", err);
      if (statusBox) {
        statusBox.textContent = "⚠️ No se pudo inicializar el Service Worker";
      }
    }
  },

  urlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  },

  async toggleDeviceSubscription() {
    if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
      showToast("En iPhone debes añadir la app a la pantalla de inicio desde Safari y abrirla desde su icono", "error");
      return;
    }

    try {
      if (this.currentSubscription) {
        await api.delete("/api/push/subscriptions", { endpoint: this.currentSubscription.endpoint });
        await this.currentSubscription.unsubscribe();
        this.currentSubscription = null;
        sessionStorage.removeItem("owngarnization_synced_sub");
        showToast("Notificaciones desactivadas en este dispositivo", "info");
        await this.refreshDeviceSubscriptionUI();
        return;
      }

      if (!this.configured || !this.vapidPublicKey) {
        showToast("El servidor aún no tiene claves VAPID configuradas", "error");
        return;
      }

      // Solicitar Notification.requestPermission() inmediatamente dentro del gesto táctil (requisito iOS WebKit)
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        showToast("Debes conceder permiso de notificaciones en el aviso de tu teléfono", "error");
        await this.refreshDeviceSubscriptionUI();
        return;
      }

      const reg = await this.ensureServiceWorkerReady();
      const existing = await reg.pushManager.getSubscription();
      if (existing) {
        await existing.unsubscribe();
      }

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
      });

      this.currentSubscription = sub;
      const subJson = sub.toJSON();
      await api.post("/api/push/subscriptions", {
        endpoint: subJson.endpoint,
        keys: {
          p256dh: subJson.keys?.p256dh || "",
          auth: subJson.keys?.auth || ""
        },
        user_agent: navigator.userAgent
      });
      sessionStorage.setItem("owngarnization_synced_sub", "1");

      // Asegurar que las preferencias de avisos y zona horaria queden activas en la cuenta
      const enabledCheck = document.getElementById("notif-enabled-check");
      if (enabledCheck) enabledCheck.checked = true;
      await this.savePreferences({ silent: true });

      showToast("¡Avisos activados en este dispositivo!", "success");
      await this.refreshDeviceSubscriptionUI();
    } catch (err) {
      console.error("Error al gestionar suscripción Push:", err);
      showToast(err.message || "Error al activar notificaciones", "error");
    }
  },

  async savePreferences({ silent = false, closeOnSave = false } = {}) {
    const enabledCheck = document.getElementById("notif-enabled-check");
    const offsetSelect = document.getElementById("notif-offset-select");
    const tzInput = document.getElementById("notif-timezone-display");
    const detectedTz = Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Madrid";

    const payload = {
      reminders_enabled: Boolean(enabledCheck ? enabledCheck.checked : true),
      reminder_offset_min: Number(offsetSelect?.value ?? 10),
      timezone: (tzInput?.value || detectedTz).trim()
    };

    try {
      await api.patch("/api/me/preferences", payload);
      if (!silent) {
        showToast("Preferencias de avisos guardadas", "success");
      }
      if (closeOnSave) {
        this.closeModal();
      }
    } catch (err) {
      if (!silent) {
        showToast(err.message || "Error al guardar preferencias", "error");
      }
    }
  },

  async sendTestNotification() {
    try {
      await api.post("/api/push/test", {});
      showToast("Notificación de prueba enviada", "success");
    } catch (err) {
      showToast(err.message || "No se pudo enviar la prueba", "error");
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  window.pushManagerClient = pushManagerClient;
  pushManagerClient.init();
});
