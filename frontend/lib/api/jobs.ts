/**
 * Jobs API client — the live replacement for lib/mock-data/jobs.ts.
 *
 * The backend ranks postings by overlap with the signed-in user's skills and returns
 * matched/missing as {id, display_name, category} objects. `location` may be null.
 */

import { apiFetch } from "./base";
import type { SkillRef } from "./plans";

export type JobMatch = {
  id: string;
  company: string;
  title: string;
  location: string | null;
  url: string;
  posted_at: string;
  overlap: number;
  matched_skills: SkillRef[];
  missing_skills: SkillRef[];
};

export async function fetchJobs(): Promise<JobMatch[]> {
  const response = await apiFetch("/jobs");
  if (!response.ok) throw new Error(`GET /jobs failed: ${response.status}`);
  return response.json();
}
