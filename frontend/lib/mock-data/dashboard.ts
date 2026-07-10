/**
 * MOCK DATA — the user's current skill profile.
 *
 * Will be replaced by a call to the dashboard API (e.g. `GET /api/dashboard`)
 * once the backend is wired up. The `skills_by_category` field reflects the
 * cumulative extraction across saved plans (see `plans.ts`); the live version
 * will compute it server-side from the same source.
 */

import type { SkillCategory } from "./skills";

export type Dashboard = {
  /** Filename of the most recent resume the profile was extracted from. */
  last_updated_from: string;
  /** ISO date (yyyy-mm-dd). */
  last_updated_at: string;
  /** Skill IDs grouped by category. Categories with no skills are omitted. */
  skills_by_category: Partial<Record<SkillCategory, string[]>>;
};

export const DASHBOARD: Dashboard = {
  last_updated_from: "resume-2026.pdf",
  last_updated_at: "2026-05-02",
  skills_by_category: {
    language: ["python", "javascript", "typescript", "sql", "html", "css"],
    framework: ["react", "tailwindcss"],
    database: ["postgresql"],
    devops: ["git"],
    tool: ["figma"],
  },
};

export function getDashboard(): Dashboard {
  return DASHBOARD;
}

/**
 * Flat list of every skill ID on the user's profile, regardless of category.
 */
export function getDashboardSkillIds(): string[] {
  return Object.values(DASHBOARD.skills_by_category).flat();
}
