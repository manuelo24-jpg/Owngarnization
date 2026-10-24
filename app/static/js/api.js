/**
 * Owngarnization — Cliente API y Utilidades Globales
 */

const api = {
  async request(url, options = {}) {
    const config = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    };

    if (config.body && typeof config.body === "object") {
      config.body = JSON.stringify(config.body);
    }

    try {
      const response = await fetch(url, config);
      
      // Si la sesión expiró o no está autenticado, redirigir a login
      if (response.status === 401 && !url.includes("/auth/login")) {
        window.location.href = "/login";
        return;
      }

      const contentType = response.headers.get("content-type");
      let data = null;
      if (contentType && contentType.includes("application/json")) {
        data = await response.json();
      }

      if (!response.ok) {
        const errorMsg = data?.detail || `Error en la petición (${response.status})`;
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`API Error [${options.method || "GET"} ${url}]:`, err);
      throw err;
    }
  },

  get(url, params = {}) {
    const query = new URLSearchParams();
    for (const [key, val] of Object.entries(params)) {
      if (val !== null && val !== undefined && val !== "") {
        query.append(key, val);
      }
    }
    const fullUrl = query.toString() ? `${url}?${query.toString()}` : url;
    return this.request(fullUrl, { method: "GET" });
  },

  post(url, body) {
    return this.request(url, { method: "POST", body });
  },

  patch(url, body) {
    return this.request(url, { method: "PATCH", body });
  },

  delete(url) {
    return this.request(url, { method: "DELETE" });
  }
};

/**
 * Muestra un mensaje toast temporal en pantalla
 */
function showToast(message, type = "info", duration = 3000) {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  // Animación de entrada
  setTimeout(() => toast.classList.add("show"), 10);

  // Auto-eliminación
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 250);
  }, duration);
}
