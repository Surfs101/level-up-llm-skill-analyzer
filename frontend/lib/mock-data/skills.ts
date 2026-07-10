/**
 * MOCK DATA — canonical skill taxonomy used for matching.
 *
 * Will be replaced by a call to the skills API (e.g. `GET /api/skills`)
 * once the backend is wired up. Keep the shape stable; screens import
 * from here and shouldn't notice the swap.
 *
 * Category values match the backend's API contract exactly (lowercase
 * singular). Display labels live in CATEGORY_LABELS below.
 */

export type SkillCategory =
  | "language"
  | "framework"
  | "library"
  | "database"
  | "cloud"
  | "devops"
  | "tool";

export type Skill = {
  id: string;
  canonical_name: string;
  category: SkillCategory;
  aliases: string[];
};

/** Canonical render order — code → compose → import → store → deploy → automate → other. */
export const SKILL_CATEGORIES: SkillCategory[] = [
  "language",
  "framework",
  "library",
  "database",
  "cloud",
  "devops",
  "tool",
];

/** Human-readable section headers and filter button text. */
export const CATEGORY_LABELS: Record<SkillCategory, string> = {
  language: "Languages",
  framework: "Frameworks",
  library: "Libraries",
  database: "Databases",
  cloud: "Cloud",
  devops: "DevOps",
  tool: "Tools",
};

export const SKILLS: Skill[] = [
  // Languages
  { id: "python", canonical_name: "Python", category: "language", aliases: ["py", "python3"] },
  { id: "javascript", canonical_name: "JavaScript", category: "language", aliases: ["js", "ecmascript"] },
  { id: "typescript", canonical_name: "TypeScript", category: "language", aliases: ["ts"] },
  { id: "java", canonical_name: "Java", category: "language", aliases: [] },
  { id: "go", canonical_name: "Go", category: "language", aliases: ["golang"] },
  { id: "rust", canonical_name: "Rust", category: "language", aliases: [] },
  { id: "sql", canonical_name: "SQL", category: "language", aliases: [] },
  { id: "html", canonical_name: "HTML", category: "language", aliases: ["html5"] },
  { id: "css", canonical_name: "CSS", category: "language", aliases: ["css3"] },

  // Frameworks
  { id: "react", canonical_name: "React", category: "framework", aliases: ["react.js", "reactjs"] },
  { id: "vue", canonical_name: "Vue", category: "framework", aliases: ["vue.js", "vuejs"] },
  { id: "svelte", canonical_name: "Svelte", category: "framework", aliases: [] },
  { id: "nextjs", canonical_name: "Next.js", category: "framework", aliases: ["next.js", "next"] },
  { id: "nodejs", canonical_name: "Node.js", category: "framework", aliases: ["node", "node.js"] },
  { id: "express", canonical_name: "Express", category: "framework", aliases: ["express.js"] },
  { id: "django", canonical_name: "Django", category: "framework", aliases: [] },
  { id: "fastapi", canonical_name: "FastAPI", category: "framework", aliases: [] },
  { id: "flask", canonical_name: "Flask", category: "framework", aliases: [] },
  { id: "rails", canonical_name: "Ruby on Rails", category: "framework", aliases: ["rails", "ror"] },
  { id: "tailwindcss", canonical_name: "Tailwind CSS", category: "framework", aliases: ["tailwind"] },

  // Libraries (testing harnesses + UI/data libs that pair with frameworks)
  { id: "jest", canonical_name: "Jest", category: "library", aliases: [] },
  { id: "playwright", canonical_name: "Playwright", category: "library", aliases: [] },

  // Databases (datastores; backend categorizes them as "tool" → here as "database")
  { id: "postgresql", canonical_name: "PostgreSQL", category: "database", aliases: ["postgres", "psql"] },
  { id: "mongodb", canonical_name: "MongoDB", category: "database", aliases: ["mongo"] },
  { id: "redis", canonical_name: "Redis", category: "database", aliases: [] },
  { id: "bigquery", canonical_name: "BigQuery", category: "database", aliases: [] },
  { id: "supabase", canonical_name: "Supabase", category: "database", aliases: [] },

  // Cloud platforms / hosting
  { id: "aws", canonical_name: "AWS", category: "cloud", aliases: ["amazon web services"] },
  { id: "gcp", canonical_name: "GCP", category: "cloud", aliases: ["google cloud", "google cloud platform"] },
  { id: "azure", canonical_name: "Azure", category: "cloud", aliases: ["microsoft azure"] },
  { id: "vercel", canonical_name: "Vercel", category: "cloud", aliases: [] },
  { id: "cloudflare", canonical_name: "Cloudflare", category: "cloud", aliases: [] },

  // DevOps (build, deploy, infra, version control, CI)
  { id: "git", canonical_name: "Git", category: "devops", aliases: [] },
  { id: "docker", canonical_name: "Docker", category: "devops", aliases: [] },
  { id: "kubernetes", canonical_name: "Kubernetes", category: "devops", aliases: ["k8s"] },
  { id: "terraform", canonical_name: "Terraform", category: "devops", aliases: [] },
  { id: "github-actions", canonical_name: "GitHub Actions", category: "devops", aliases: ["gh actions"] },
  { id: "webpack", canonical_name: "Webpack", category: "devops", aliases: [] },
  { id: "vite", canonical_name: "Vite", category: "devops", aliases: [] },

  // Tools (design + everything else)
  { id: "figma", canonical_name: "Figma", category: "tool", aliases: [] },
];

export function getSkillById(id: string): Skill | undefined {
  return SKILLS.find((s) => s.id === id);
}

export function getSkillsByCategory(category: SkillCategory): Skill[] {
  return SKILLS.filter((s) => s.category === category);
}
