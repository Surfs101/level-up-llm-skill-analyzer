/** Shared config for the backend API client. */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** fetch against the API with the session cookie attached (credentialed CORS). */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${API_BASE}${path}`, { credentials: "include", ...init });
}

/**
 * The CSRF double-submit header for non-idempotent authed writes (PATCH/DELETE).
 * Echoes the readable `csrf_token` cookie the backend set at sign-in; the server
 * rejects the write if the header doesn't match the cookie.
 */
export function csrfHeaders(): Record<string, string> {
  const token = readCookie("csrf_token");
  return token ? { "X-CSRF-Token": token } : {};
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}
