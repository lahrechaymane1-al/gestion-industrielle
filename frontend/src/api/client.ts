import axios, { type AxiosError } from "axios";

function getCookie(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(";").shift() ?? null;
  return null;
}

function decodeCookieValue(raw: string): string {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

/**
 * Django rotates the CSRF cookie on login; the HTML meta tag does not update until a full reload.
 * Prefer the cookie so X-CSRFToken matches the secret Django validates (avoids 403 after login).
 */
function getCsrfToken(): string {
  const fromCookie = getCookie("csrftoken");
  if (fromCookie) return decodeCookieValue(fromCookie);
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta?.getAttribute("content")) return meta.getAttribute("content")!;
  return "";
}

export const api = axios.create({
  baseURL: "",
  withCredentials: true,
  headers: { "X-Requested-With": "XMLHttpRequest" },
});

api.interceptors.request.use((config) => {
  const method = (config.method ?? "get").toLowerCase();
  if (["post", "put", "patch", "delete"].includes(method)) {
    const token = getCsrfToken();
    if (token) {
      config.headers = config.headers ?? {};
      (config.headers as Record<string, string>)["X-CSRFToken"] = token;
    }
  }
  return config;
});

export function formatApiError(err: unknown): string {
  const ax = err as AxiosError<{ error?: string; errors?: Record<string, string[]> }>;
  if (ax.response?.data && typeof ax.response.data === "object") {
    const d = ax.response.data;
    if (d.error) return String(d.error);
    if (d.errors) {
      const parts = Object.entries(d.errors).flatMap(([k, v]) =>
        (Array.isArray(v) ? v : [v]).map((x) => `${k}: ${x}`)
      );
      if (parts.length) return parts.join(" · ");
    }
  }
  if (ax.message) return ax.message;
  return "Erreur réseau ou serveur.";
}
