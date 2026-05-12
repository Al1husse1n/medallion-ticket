const API_BASE_URL = "http://localhost:8000/medallion";
const AUTH_TOKEN_KEY = "medallion_auth_token";
const AUTH_ROLE_KEY = "medallion_auth_role";
const AUTH_EMAIL_KEY = "medallion_auth_email";

function createToastContainer() {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.position = "fixed";
    container.style.top = "1rem";
    container.style.right = "1rem";
    container.style.zIndex = "9999";
    container.style.display = "flex";
    container.style.flexDirection = "column";
    container.style.gap = "0.5rem";
    document.body.appendChild(container);
  }
  return container;
}

function showToast(message, type = "info") {
  const container = createToastContainer();
  const toast = document.createElement("div");
  toast.textContent = message;
  toast.style.minWidth = "220px";
  toast.style.padding = "0.9rem 1rem";
  toast.style.borderRadius = "0.75rem";
  toast.style.boxShadow = "0 12px 30px rgba(15, 23, 42, 0.12)";
  toast.style.color = "#ffffff";
  toast.style.fontFamily = "Inter, sans-serif";
  toast.style.fontSize = "0.95rem";
  toast.style.opacity = "0";
  toast.style.transition = "opacity 180ms ease, transform 180ms ease";
  toast.style.transform = "translateY(-6px)";

  if (type === "success") {
    toast.style.background = "#059669";
  } else if (type === "error") {
    toast.style.background = "#dc2626";
  } else {
    toast.style.background = "#0f172a";
  }

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";
  });

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(-6px)";
    toast.addEventListener("transitionend", () => toast.remove(), { once: true });
  }, 4000);
}

function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decodeURIComponent(escape(decoded)));
  } catch (error) {
    return null;
  }
}

class AuthService {
  constructor() {
    this.token = this.getToken();
  }

  getToken() {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  }

  setToken(token) {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
      this.token = token;
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      this.token = null;
    }
  }

  getCurrentUserRole() {
    const storedRole = localStorage.getItem(AUTH_ROLE_KEY);
    if (storedRole) {
      return storedRole;
    }
    const token = this.getToken();
    if (!token) {
      return null;
    }
    const payload = decodeJwt(token);
    const role = payload?.role ?? payload?.role?.toString?.();
    if (role) {
      localStorage.setItem(AUTH_ROLE_KEY, role);
    }
    return role || null;
  }

  setCurrentUserRole(role) {
    if (role) {
      localStorage.setItem(AUTH_ROLE_KEY, role);
    } else {
      localStorage.removeItem(AUTH_ROLE_KEY);
    }
  }

  getCurrentUserEmail() {
    return localStorage.getItem(AUTH_EMAIL_KEY);
  }

  setCurrentUserEmail(email) {
    if (email) {
      localStorage.setItem(AUTH_EMAIL_KEY, email);
    } else {
      localStorage.removeItem(AUTH_EMAIL_KEY);
    }
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  async login(email, password) {
    try {
      const response = await fetch(`${API_BASE_URL}/employee/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ username: email, password }),
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const message = errorBody?.detail || errorBody?.message || "Login failed";
        return { success: false, error: message };
      }

      const data = await response.json();
      this.setToken(data.access_token);
      this.setCurrentUserEmail(email);
      const role = this.getCurrentUserRole();
      if (role) {
        this.setCurrentUserRole(role);
      }
      return { success: true, data: { access_token: data.access_token, token_type: data.token_type, role } };
    } catch (error) {
      return { success: false, error: error.message || "Unable to login" };
    }
  }

  logout(redirect = true) {
    this.setToken(null);
    this.setCurrentUserRole(null);
    this.setCurrentUserEmail(null);
    if (redirect) {
      window.location.href = "login.html";
    }
  }

  async registerEmployee(employeeData) {
    return apiRequest("/employee/register", {
      method: "POST",
      body: JSON.stringify(employeeData),
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  getAuthHeaders() {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  isAuthorized(allowedRoles) {
    const role = this.getCurrentUserRole();
    if (!role) return false;
    if (!allowedRoles || allowedRoles.length === 0) return true;
    const normalizedRole = role.toString().toLowerCase();
    return allowedRoles
      .map((entry) => entry.toString().toLowerCase().trim())
      .includes(normalizedRole);
  }

  requireAuthorization(allowedRoles, fallbackUrl = "login.html") {
    if (!this.isAuthenticated()) {
      showToast("You must be logged in to access this page.", "error");
      this.logout(false);
      window.location.href = fallbackUrl;
      return false;
    }
    if (!this.isAuthorized(allowedRoles)) {
      showToast("You are not authorized to access this page.", "error");
      this.logout(false);
      window.location.href = fallbackUrl;
      return false;
    }
    return true;
  }
}

window.authService = new AuthService();

function hideUnauthorizedLinks() {
  const role = authService.getCurrentUserRole();
  if (!role) return;
  document.querySelectorAll('[data-role]').forEach((node) => {
    const raw = node.dataset.role || "";
    const allowedRoles = raw.split(",").map((entry) => entry.toString().toLowerCase().trim());
    if (!allowedRoles.includes(role.toString().toLowerCase())) {
      node.remove();
    }
  });
}

function redirectToRoleHome() {
  const role = authService.getCurrentUserRole();
  if (role === "manager") {
    window.location.href = "manager.html";
  } else if (role === "clerk") {
    window.location.href = "clerk.html";
  } else {
    authService.logout();
  }
}

async function apiRequest(endpoint, options = {}) {
  const token = authService.getToken();
  const headers = {
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const config = {
    ...options,
    headers,
  };

  if (config.body && typeof config.body === "object" && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
    if (!config.headers?.["Content-Type"]) {
      config.headers = { ...config.headers, "Content-Type": "application/json" };
    }
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    if (response.status === 401 || response.status === 403) {
      const contentType = response.headers.get("Content-Type") || "";
      const responseBody = contentType.includes("application/json") ? await response.json().catch(() => null) : null;
      const message = responseBody?.detail || responseBody?.message || "You are not authorized to perform this action.";
      showToast(message, "error");
      authService.logout();
      return { success: false, error: message };
    }
    const contentType = response.headers.get("Content-Type") || "";
    const responseBody = contentType.includes("application/json") ? await response.json().catch(() => null) : null;
    if (!response.ok) {
      const message = responseBody?.detail || responseBody?.message || response.statusText || "Request failed";
      return { success: false, error: message };
    }
    return { success: true, data: responseBody };
  } catch (error) {
    return { success: false, error: error.message || "Network error" };
  }
}
