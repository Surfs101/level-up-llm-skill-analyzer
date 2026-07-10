/** Analyze API client — trigger a run and poll it. */

import { API_BASE, apiFetch } from "./base";
import type { PlanDetail } from "./plans";

export type RunStatus = {
  run_id: string;
  status: "queued" | "running" | "completed" | "failed";
  current_stage: number | null;
  /** StageList active index (0..5); 6 means every stage is done. */
  ui_stage: number;
  error_message: string | null;
  /** Signed-in runs: the saved Plan's id (navigate to /plans/{id}). */
  plan_id: string | null;
  /** Guest runs: the plan inline (guests have no saved Plan to navigate to). */
  plan: PlanDetail | null;
};

/** POST the resume + JD as multipart and return the new run id. */
export async function createAnalysis(file: File, jdText: string): Promise<string> {
  const form = new FormData();
  form.append("resume", file);
  form.append("jd_text", jdText);

  // Don't set Content-Type — the browser adds the multipart boundary.
  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!response.ok) throw new Error(`POST /analyze failed: ${response.status}`);
  const body = await response.json();
  return body.run_id;
}

export async function fetchRunStatus(runId: string): Promise<RunStatus> {
  const response = await apiFetch(`/runs/${runId}`);
  if (!response.ok) throw new Error(`GET /runs/${runId} failed: ${response.status}`);
  return response.json();
}
