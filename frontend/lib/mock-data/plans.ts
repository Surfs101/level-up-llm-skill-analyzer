/**
 * MOCK DATA — saved gap-analysis plans for a fictional user.
 *
 * Will be replaced by a call to the plans API (e.g. `GET /api/plans`)
 * once the backend is wired up. Each plan is the result of running a
 * resume against a single job description and saving the output.
 */

export type ProjectKind = "current" | "with_course_1";

export type PlanProject = {
  kind: ProjectKind;
  title: string;
  problem_statement: string;
  /** Skill IDs the project exercises. */
  tech_stack: string[];
  milestones: string[];
  readme_highlight: string;
};

export type PlanCourse = {
  course_id: string;
  rank: number;
  /** Subset of `course.skills_covered` ∩ `plan.missing_skills` — what this course buys you for this gap. */
  skills_covered: string[];
};

export type Plan = {
  id: string;
  jd_title: string;
  jd_company: string;
  jd_text: string;
  resume_filename: string;
  /** ISO date (yyyy-mm-dd). */
  created_at: string;
  /** Skill IDs already evidenced on the user's resume. */
  matched_skills: string[];
  /** Skill IDs the JD requires that the resume doesn't surface. */
  missing_skills: string[];
  /** Top 2 recommended courses, ranked. */
  courses: PlanCourse[];
  /** Two projects: one the user already has, one to build after course #1. */
  projects: PlanProject[];
};

export const PLANS: Plan[] = [
  {
    id: "plan-vercel-frontend",
    jd_title: "Frontend Engineer",
    jd_company: "Vercel",
    jd_text:
      "We're hiring a frontend engineer to ship the Vercel dashboard. You'll work in TypeScript and React, with a strong product sense and an eye for performance. Comfort with Node.js, GraphQL, and end-to-end testing is a plus; experience designing for distributed systems even more so.",
    resume_filename: "resume-2026.pdf",
    created_at: "2026-05-02",
    matched_skills: [
      "javascript",
      "typescript",
      "react",
      "html",
      "css",
      "tailwindcss",
      "git",
    ],
    missing_skills: ["nodejs", "graphql", "distributed-systems"],
    courses: [
      {
        course_id: "full-stack-open",
        rank: 1,
        skills_covered: ["nodejs", "graphql"],
      },
      {
        course_id: "ddia-live",
        rank: 2,
        skills_covered: ["distributed-systems"],
      },
    ],
    projects: [
      {
        kind: "current",
        title: "Recipe Search App",
        problem_statement:
          "A static recipe site I built last summer to learn React. Users filter ~2,000 recipes by cuisine and dietary restriction, but the all-client filter hangs on older phones once the list crosses about 400 results.",
        tech_stack: ["react", "typescript", "tailwindcss"],
        milestones: [
          "Migrate routing to the App Router and move the filter to a server component",
          "Lazy-load recipe images via next/image with a blur placeholder",
          "Add a Playwright test covering the search-then-filter flow",
        ],
        readme_highlight:
          "Profile-driven rewrite that drops time-to-interactive on a mid-tier Android from 4.1s to 1.2s.",
      },
      {
        kind: "with_course_1",
        title: "Live Q&A Board",
        problem_statement:
          "A Reddit-style live Q&A board where attendees of a virtual meetup can post questions and the host can pin and reorder them in real time. Showcases GraphQL subscriptions and a TypeScript Node backend, both new to me.",
        tech_stack: ["react", "typescript", "nodejs", "graphql", "postgresql"],
        milestones: [
          "Stand up an Apollo server with subscriptions over WebSockets",
          "Wire the host's reorder UI to optimistic updates",
          "Document the schema and mutations in a README diagram",
        ],
        readme_highlight:
          "End-to-end demo of a real-time GraphQL stack — schema-first, subscription-based, with reconnect handling.",
      },
    ],
  },
  {
    id: "plan-spotify-data-analyst",
    jd_title: "Junior Data Analyst",
    jd_company: "Spotify",
    jd_text:
      "We're looking for a junior data analyst to support our podcast monetization team. You'll write SQL against our event tables, build dashboards for product partners, and run light experiments. Comfort with Python for data wrangling and basic statistics is required; experience with A/B testing or BigQuery is a plus.",
    resume_filename: "resume-2026.pdf",
    created_at: "2026-04-18",
    matched_skills: ["python", "sql", "postgresql", "agile"],
    missing_skills: ["data-visualization", "machine-learning", "ab-testing"],
    courses: [
      {
        course_id: "ml-specialization",
        rank: 1,
        skills_covered: ["machine-learning", "ab-testing"],
      },
      {
        course_id: "data-viz-storytelling",
        rank: 2,
        skills_covered: ["data-visualization"],
      },
    ],
    projects: [
      {
        kind: "current",
        title: "Personal Finance Dashboard",
        problem_statement:
          "Tracking my own spending across two bank accounts and three credit cards. A Python script normalizes CSV exports and writes them into Postgres; queries run by hand from psql.",
        tech_stack: ["python", "postgresql", "sql"],
        milestones: [
          "Add a Streamlit front end so I'm not running queries by hand",
          "Write window-function queries for rolling 30-day spend by category",
          "Document the schema and the dedup rules in the README",
        ],
        readme_highlight:
          "Three-line CLI command ingests a year of statements and yields a category-level monthly view.",
      },
      {
        kind: "with_course_1",
        title: "Listening Habit Predictor",
        problem_statement:
          "Using my own Spotify listening-history JSON dump, train a small classifier to predict which playlist a given track belongs to and run an A/B test on a recommendation rule before and after retraining.",
        tech_stack: ["python", "sql", "machine-learning"],
        milestones: [
          "Load the JSON dump into a local table and feature-engineer track metadata",
          "Train a logistic regression baseline and a gradient-boosted model in scikit-learn",
          "Run an A/B comparison of recommendation rules and write up the lift",
        ],
        readme_highlight:
          "Demonstrates a full experiment loop — feature engineering, two model variants, and a written A/B writeup with confidence intervals.",
      },
    ],
  },
  {
    id: "plan-linear-pm",
    jd_title: "Product Manager",
    jd_company: "Linear",
    jd_text:
      "Linear is hiring a product manager with strong technical instincts. You'll partner closely with engineers on the issues product surface, write specs that hold up under scrutiny, and run user research with our power-users. B2B SaaS experience and a willingness to read code are both expected.",
    resume_filename: "resume-product.pdf",
    created_at: "2026-04-05",
    matched_skills: ["technical-writing", "agile", "sql", "figma", "user-research"],
    missing_skills: ["system-design", "ab-testing", "data-visualization"],
    courses: [
      {
        course_id: "system-design-interview",
        rank: 1,
        skills_covered: ["system-design"],
      },
      {
        course_id: "ml-specialization",
        rank: 2,
        skills_covered: ["ab-testing"],
      },
    ],
    projects: [
      {
        kind: "current",
        title: "Open Source Contribution Tracker",
        problem_statement:
          "A small dashboard that pulls my PRs from the GitHub API and groups them by week and repo. I built it in a weekend to track my own activity, and a friend started using it for her quarterly reviews.",
        tech_stack: ["typescript", "react", "sql", "postgresql"],
        milestones: [
          "Add issue-type labels so contributions can be summarized PM-style",
          "Run a usability test with two friends and write up the friction",
          "Publish a short blog post on the build and the tradeoffs",
        ],
        readme_highlight:
          "Lightweight internal tool built end-to-end, with a written brief on what I'd change before generalizing it.",
      },
      {
        kind: "with_course_1",
        title: "Roadmap Voting Prototype",
        problem_statement:
          "A Linear-shaped feature where customers can upvote roadmap items and PMs can see the vote distribution by segment. Uses the system-design course's capacity-planning template to scope the data model and write-throughput.",
        tech_stack: ["typescript", "react", "postgresql"],
        milestones: [
          "Write a 3-page spec including capacity planning for 10× current usage",
          "Build a working prototype with vote-by-segment dashboards",
          "Run a structured walkthrough with two engineers and capture pushback",
        ],
        readme_highlight:
          "Pairs a working prototype with a system-design spec — strong portfolio artifact for a technical PM role.",
      },
    ],
  },
  {
    id: "plan-stripe-ux-research",
    jd_title: "UX Researcher",
    jd_company: "Stripe",
    jd_text:
      "Stripe's merchant onboarding team is hiring a UX researcher. You'll run mixed-methods studies — user interviews, diary studies, and quantitative analysis on flow drop-off — and partner with designers and PMs on what to ship next. Strong written communication and comfort with SQL are essential.",
    resume_filename: "resume-research.pdf",
    created_at: "2026-03-22",
    matched_skills: [
      "user-research",
      "figma",
      "technical-writing",
      "agile",
      "sql",
    ],
    missing_skills: ["data-visualization", "ab-testing", "machine-learning"],
    courses: [
      {
        course_id: "data-viz-storytelling",
        rank: 1,
        skills_covered: ["data-visualization"],
      },
      {
        course_id: "ml-specialization",
        rank: 2,
        skills_covered: ["ab-testing", "machine-learning"],
      },
    ],
    projects: [
      {
        kind: "current",
        title: "Onboarding Flow Audit",
        problem_statement:
          "A self-driven audit of a small fintech app's onboarding flow. I ran 8 interviews with users in their first week, coded the transcripts, and wrote up the friction points in a 6-page report.",
        tech_stack: ["figma", "user-research", "technical-writing"],
        milestones: [
          "Compile interview notes into a coded affinity diagram in Figma",
          "Draft an executive summary with five concrete recommendations",
          "Publish the report on a personal blog and gather peer feedback",
        ],
        readme_highlight:
          "Complete qualitative cycle: planning, fieldwork, synthesis, and a written report shaped for a non-research audience.",
      },
      {
        kind: "with_course_1",
        title: "Cancellation Cohort Report",
        problem_statement:
          "A quantitative deep-dive on subscription cancellation triggers using a public dataset. The deliverable is a polished dashboard with a written brief — the kind of artifact a designer would actually use to scope a redesign.",
        tech_stack: ["sql", "data-visualization", "technical-writing"],
        milestones: [
          "Cluster cancellations into 4-5 cohorts using SQL window functions",
          "Build a four-chart story explaining the dominant cohort",
          "Publish the dashboard with a 2-page written brief",
        ],
        readme_highlight:
          "Strong example of moving from a qualitative comfort zone into mixed-methods, with charts that earn their place in the narrative.",
      },
    ],
  },
];

export function getPlanById(id: string): Plan | undefined {
  return PLANS.find((p) => p.id === id);
}

/**
 * Returns plans sorted most-recent first.
 */
export function getRecentPlans(): Plan[] {
  return [...PLANS].sort((a, b) => b.created_at.localeCompare(a.created_at));
}
