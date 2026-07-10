/**
 * Dashboard API client — the live replacement for lib/mock-data/dashboard.ts.
 *
 * The response shape matches the mock field-for-field, so consumers that used the
 * mock only need to swap the data source. `last_updated_*` may be null until a
 * resume has been uploaded (the extracted partition arrives in a later phase).
 */

import type { SkillCategory } from "../mock-data/skills";
import { apiFetch, csrfHeaders } from "./base";

export type DashboardResponse = {
  last_updated_from: string | null;
  last_updated_at: string | null;
  skills_by_category: Partial<Record<SkillCategory, string[]>>;
};

export async function fetchDashboard(): Promise<DashboardResponse> {
  const response = await apiFetch("/dashboard");
  if (!response.ok) {
    throw new Error(`GET /dashboard failed: ${response.status}`);
  }
  return response.json();
}

/**
 * Add/remove manual skills. A non-idempotent write, so it sends the CSRF header.
 * (The UI picker that calls this is still to be built — the skills-search endpoint.)
 */
export async function patchDashboard(changes: {
  add?: string[];
  remove?: string[];
}): Promise<DashboardResponse> {
  const response = await apiFetch("/dashboard", {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    body: JSON.stringify(changes),
  });
  if (!response.ok) {
    throw new Error(`PATCH /dashboard failed: ${response.status}`);
  }
  return response.json();
}
