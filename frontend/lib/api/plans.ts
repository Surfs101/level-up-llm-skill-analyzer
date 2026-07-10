/**
 * Plans API client — the live replacement for lib/mock-data/plans.ts.
 *
 * The backend returns skills as objects {id, display_name, category} and projects as
 * Markdown (the pipeline emits Markdown; the old mock assumed pre-structured
 * projects). It also embeds each recommended course's display fields, since there is
 * no separate courses endpoint. jd_title / jd_company / resume_filename have no
 * backend source yet, so the UI derives a heading from jd_text.
 */

import { apiFetch, csrfHeaders } from "./base";

export type SkillRef = {
  id: string;
  display_name: string;
  category: string;
};

export type PlanCourseRef = {
  course_id: string;
  rank: number;
  title: string;
  provider: string;
  description: string | null;
  url: string;
  skills_covered: SkillRef[];
};

export type PlanSummary = {
  id: string;
  jd_text: string;
  created_at: string;
  fit_score: number;
  matched_count: number;
  missing_count: number;
};

export type PlanDetail = {
  id: string;
  jd_text: string;
  created_at: string;
  fit_score: number;
  matched_skills: SkillRef[];
  missing_skills: SkillRef[];
  courses: PlanCourseRef[];
  project_one_md: string;
  project_two_md: string;
};

export async function fetchPlanSummaries(): Promise<PlanSummary[]> {
  const response = await apiFetch("/plans");
  if (!response.ok) throw new Error(`GET /plans failed: ${response.status}`);
  return response.json();
}

export async function fetchPlanDetail(id: string): Promise<PlanDetail> {
  const response = await apiFetch(`/plans/${id}`);
  if (!response.ok) throw new Error(`GET /plans/${id} failed: ${response.status}`);
  return response.json();
}

export async function deletePlan(id: string): Promise<void> {
  // A non-idempotent write — send the CSRF double-submit header.
  const response = await apiFetch(`/plans/${id}`, { method: "DELETE", headers: csrfHeaders() });
  if (!response.ok) throw new Error(`DELETE /plans/${id} failed: ${response.status}`);
}
