/**
 * MOCK DATA — Greenhouse-style job postings with pre-computed match
 * results against the fictional default user.
 *
 * Will be replaced by a call to the jobs API (e.g. `GET /api/jobs`)
 * once the backend is wired up. The `matched_skills` / `missing_skills`
 * fields are pre-computed against `DEFAULT_USER_SKILLS` below; the live
 * version will compute these on the server based on the signed-in user.
 */

/**
 * Skill IDs the fictional default user has on their profile. The union
 * of `matched_skills` across all saved plans (see `plans.ts`).
 */
export const DEFAULT_USER_SKILLS: string[] = [
  "javascript",
  "typescript",
  "react",
  "html",
  "css",
  "tailwindcss",
  "git",
  "python",
  "sql",
  "postgresql",
  "agile",
  "technical-writing",
  "figma",
  "user-research",
];

export type Job = {
  id: string;
  company: string;
  title: string;
  location: string;
  /** ISO date (yyyy-mm-dd). */
  posted_at: string;
  /** Skill IDs the JD calls for. */
  skills: string[];
  /** Pre-computed: `skills` ∩ `DEFAULT_USER_SKILLS`. */
  matched_skills: string[];
  /** Pre-computed: `skills` − `DEFAULT_USER_SKILLS`. */
  missing_skills: string[];
};

export const JOBS: Job[] = [
  {
    id: "job-acme-frontend",
    company: "Acme",
    title: "Frontend Engineer",
    location: "Remote · United States",
    posted_at: "2026-05-06",
    skills: ["javascript", "typescript", "react", "nextjs", "tailwindcss", "vercel"],
    matched_skills: ["javascript", "typescript", "react", "tailwindcss"],
    missing_skills: ["nextjs", "vercel"],
  },
  {
    id: "job-lumina-data-engineer",
    company: "Lumina Data",
    title: "Data Engineer",
    location: "London, UK · Hybrid",
    posted_at: "2026-05-04",
    skills: ["python", "sql", "bigquery", "gcp", "agile", "data-visualization"],
    matched_skills: ["python", "sql", "agile"],
    missing_skills: ["bigquery", "gcp", "data-visualization"],
  },
  {
    id: "job-fintech-backend",
    company: "Fintech Innovations",
    title: "Backend Engineer, Payments",
    location: "New York, NY",
    posted_at: "2026-05-02",
    skills: ["python", "postgresql", "redis", "docker", "rest-apis", "system-design"],
    matched_skills: ["python", "postgresql"],
    missing_skills: ["redis", "docker", "rest-apis", "system-design"],
  },
  {
    id: "job-helio-fullstack",
    company: "Helio Labs",
    title: "Full Stack Engineer",
    location: "Remote · Worldwide",
    posted_at: "2026-04-30",
    skills: ["typescript", "react", "nodejs", "postgresql", "graphql", "aws"],
    matched_skills: ["typescript", "react", "postgresql"],
    missing_skills: ["nodejs", "graphql", "aws"],
  },
  {
    id: "job-northwind-designer",
    company: "Northwind Studio",
    title: "Junior Product Designer",
    location: "Berlin, Germany · Hybrid",
    posted_at: "2026-04-28",
    skills: ["figma", "user-research", "html", "css", "technical-writing", "ab-testing"],
    matched_skills: ["figma", "user-research", "html", "css", "technical-writing"],
    missing_skills: ["ab-testing"],
  },
  {
    id: "job-coral-tech-writer",
    company: "Coral Cloud",
    title: "Technical Writer",
    location: "San Francisco, CA",
    posted_at: "2026-04-26",
    skills: ["technical-writing", "html", "css", "git", "javascript", "agile", "rest-apis"],
    matched_skills: ["technical-writing", "html", "css", "git", "javascript", "agile"],
    missing_skills: ["rest-apis"],
  },
];

export function getJobById(id: string): Job | undefined {
  return JOBS.find((j) => j.id === id);
}

/**
 * Returns jobs ordered by match strength (highest matched-ratio first),
 * with a stable tiebreak on most-recent posting.
 */
export function getJobsRankedByMatch(): Job[] {
  return [...JOBS].sort((a, b) => {
    const ratioA = a.matched_skills.length / a.skills.length;
    const ratioB = b.matched_skills.length / b.skills.length;
    if (ratioA !== ratioB) return ratioB - ratioA;
    return b.posted_at.localeCompare(a.posted_at);
  });
}
