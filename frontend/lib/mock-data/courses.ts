/**
 * MOCK DATA — recommended courses for closing skill gaps.
 *
 * Will be replaced by a call to the courses API (e.g. `GET /api/courses`)
 * once the backend is wired up. URLs are placeholders; do not rely on
 * them resolving in development.
 */

export type Course = {
  id: string;
  title: string;
  provider: string;
  description: string;
  /** Skill IDs this course is meaningful prep for. */
  skills_covered: string[];
  url: string;
  /** Rough popularity score, 0-100. Used for ranking when several courses cover the same skill. */
  popularity: number;
};

export const COURSES: Course[] = [
  {
    id: "cs50",
    title: "CS50: Introduction to Computer Science",
    provider: "Harvard / edX",
    description:
      "Harvard's flagship intro to CS, taught in C, Python, JavaScript, and SQL. A long but well-paced foundation in algorithms, data structures, and systems thinking.",
    skills_covered: ["javascript", "python", "sql", "system-design"],
    url: "https://example.com/courses/cs50",
    popularity: 96,
  },
  {
    id: "full-stack-open",
    title: "Full Stack Open",
    provider: "University of Helsinki",
    description:
      "Free, project-driven course on building full-stack apps with React, Node.js, GraphQL, and TypeScript. Emphasizes shipping over lecturing.",
    skills_covered: ["react", "nodejs", "graphql", "typescript", "mongodb"],
    url: "https://example.com/courses/full-stack-open",
    popularity: 88,
  },
  {
    id: "react-v9-fm",
    title: "Complete Intro to React, v9",
    provider: "Frontend Masters",
    description:
      "Brian Holt's hands-on React course, updated for hooks, suspense, and modern bundling. Builds a real e-commerce app from scratch.",
    skills_covered: ["react", "typescript", "javascript"],
    url: "https://example.com/courses/react-v9-fm",
    popularity: 82,
  },
  {
    id: "docker-deep-dive",
    title: "Docker Deep Dive",
    provider: "Udemy",
    description:
      "Nigel Poulton's pragmatic walk through containers, images, networking, and orchestration. Ends with a working Kubernetes deployment.",
    skills_covered: ["docker", "kubernetes"],
    url: "https://example.com/courses/docker-deep-dive",
    popularity: 74,
  },
  {
    id: "system-design-interview",
    title: "Grokking the Modern System Design Interview",
    provider: "Educative",
    description:
      "Walks through 15 common system design problems — URL shortener, news feed, ride-share — with capacity planning and tradeoff analysis at each step.",
    skills_covered: ["system-design", "distributed-systems"],
    url: "https://example.com/courses/system-design-interview",
    popularity: 79,
  },
  {
    id: "sql-for-data-analysis",
    title: "SQL for Data Analysis",
    provider: "Udacity",
    description:
      "Focused course on writing SQL for analytical questions: window functions, joins, subqueries, and how to read query plans. Uses PostgreSQL throughout.",
    skills_covered: ["sql", "postgresql"],
    url: "https://example.com/courses/sql-for-data-analysis",
    popularity: 71,
  },
  {
    id: "ml-specialization",
    title: "Machine Learning Specialization",
    provider: "Coursera (DeepLearning.AI)",
    description:
      "Andrew Ng's updated ML series — supervised learning, unsupervised methods, and a full module on experimentation and A/B testing.",
    skills_covered: ["python", "machine-learning", "ab-testing"],
    url: "https://example.com/courses/ml-specialization",
    popularity: 91,
  },
  {
    id: "missing-semester-mit",
    title: "The Missing Semester of Your CS Education",
    provider: "MIT OCW",
    description:
      "Short, dense lectures on the things CS programs skip: shell scripting, Git internals, debugging, version control discipline, and writing technical docs.",
    skills_covered: ["git", "technical-writing"],
    url: "https://example.com/courses/missing-semester",
    popularity: 84,
  },
  {
    id: "responsive-web-design",
    title: "Responsive Web Design Certification",
    provider: "freeCodeCamp",
    description:
      "Hands-on certification on semantic HTML, modern CSS layout (Flexbox, Grid), and accessible markup. Roughly 300 hours of project work.",
    skills_covered: ["html", "css"],
    url: "https://example.com/courses/responsive-web-design",
    popularity: 68,
  },
  {
    id: "ddia-live",
    title: "Designing Data-Intensive Applications: A Course",
    provider: "O'Reilly Live",
    description:
      "Companion course to Kleppmann's book. Goes deep on storage engines, replication, and the tradeoffs between Postgres, Redis, and stream processors.",
    skills_covered: ["distributed-systems", "system-design", "postgresql", "redis"],
    url: "https://example.com/courses/ddia-live",
    popularity: 76,
  },
  {
    id: "ux-research-methods",
    title: "UX Research Methods and Best Practices",
    provider: "Coursera",
    description:
      "Mixed-methods user research: interview design, affinity mapping, survey instruments, and writing research reports stakeholders actually read.",
    skills_covered: ["user-research", "technical-writing"],
    url: "https://example.com/courses/ux-research-methods",
    popularity: 63,
  },
  {
    id: "data-viz-storytelling",
    title: "Data Visualization and Storytelling",
    provider: "Coursera",
    description:
      "Covers chart selection, perceptual hierarchy, and narrative structure for analytics reports. Final project is a polished dashboard with a written brief.",
    skills_covered: ["data-visualization", "technical-writing"],
    url: "https://example.com/courses/data-viz-storytelling",
    popularity: 59,
  },
];

export function getCourseById(id: string): Course | undefined {
  return COURSES.find((c) => c.id === id);
}

/**
 * Returns courses covering the given skill, most popular first.
 */
export function getCoursesBySkillId(skillId: string): Course[] {
  return COURSES
    .filter((c) => c.skills_covered.includes(skillId))
    .sort((a, b) => b.popularity - a.popularity);
}
