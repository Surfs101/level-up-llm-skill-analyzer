"use client";

import { motion, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  Check,
  FileText,
  GraduationCap,
  Plus,
  Sparkles,
} from "lucide-react";

import { ease } from "@/lib/motion";

type ResumeDoc = {
  kind: "resume";
  name: string;
  role: string;
  yrs: number;
  skills: string[];
  match: number;
};

type StepDoc = {
  kind: "step";
  index: number;
  title: string;
  type: "Course" | "Project";
  earns: string;
  hrs: number;
  impact: string;
};

type JobDoc = {
  kind: "job";
  company: string;
  role: string;
  comp: string;
  loc: string;
  must: string[];
  prefer: string[];
  projected: number;
};

type Doc = ResumeDoc | StepDoc | JobDoc;

const DOCUMENTS: Doc[] = [
  {
    kind: "resume",
    name: "Alex Chen",
    role: "Senior Backend",
    yrs: 5,
    skills: ["TypeScript", "Go", "Postgres", "AWS"],
    match: 74,
  },
  {
    kind: "step",
    index: 1,
    title: "Distributed Systems Foundations",
    type: "Course",
    earns: "gRPC",
    hrs: 14,
    impact: "+6%",
  },
  {
    kind: "step",
    index: 2,
    title: "Kubernetes hands-on",
    type: "Project",
    earns: "Kubernetes",
    hrs: 16,
    impact: "+6%",
  },
  {
    kind: "step",
    index: 3,
    title: "Stream processing",
    type: "Course",
    earns: "Kafka",
    hrs: 12,
    impact: "+6%",
  },
  {
    kind: "job",
    company: "Stripe",
    role: "Senior Backend Engineer",
    comp: "$180-240k",
    loc: "Remote",
    must: ["gRPC", "Kubernetes", "Kafka"],
    prefer: ["Helm", "Go"],
    projected: 92,
  },
];

const RESUME_SKILLS_LOWER = new Set(
  (DOCUMENTS.find((d): d is ResumeDoc => d.kind === "resume")?.skills ?? []).map(
    (s) => s.toLowerCase(),
  ),
);

const ROTATIONS = [-5, -2.5, 0, 2.5, 5] as const;
const Y_OFFSETS = [12, 4, -8, 4, 12] as const;
const Z_INDICES = [1, 2, 3, 2, 1] as const;

export default function HeroDocs() {
  const reduced = useReducedMotion() ?? false;

  return (
    <div className="relative mt-12 select-none md:mt-14">
      <div className="relative flex items-end justify-center [perspective:1200px]">
        {DOCUMENTS.map((doc, i) => {
          const rot = ROTATIONS[i];
          const y = Y_OFFSETS[i];
          const z = Z_INDICES[i];
          const fromCenter = Math.abs(2 - i);
          const delay = reduced ? 0 : 0.95 + fromCenter * 0.1;

          const initial = reduced
            ? { opacity: 0 }
            : { opacity: 0, y: 60, rotate: rot * 1.6, scale: 0.92 };

          return (
            <motion.div
              key={i}
              initial={initial}
              animate={{ opacity: 1, y, rotate: rot, scale: 1 }}
              transition={{ duration: 0.85, ease: ease.out, delay }}
              whileHover={
                reduced
                  ? undefined
                  : {
                      y: y - 14,
                      rotate: rot * 0.5,
                      transition: { duration: 0.3, ease: ease.out },
                    }
              }
              className={[
                "relative",
                i === 0 ? "" : "-ml-10 sm:-ml-12 md:-ml-14",
                fromCenter === 2 ? "hidden lg:block" : "",
              ].join(" ")}
              style={{
                zIndex: z,
                transformOrigin: "bottom center",
              }}
            >
              {doc.kind === "resume" ? (
                <ResumeCard doc={doc} />
              ) : doc.kind === "step" ? (
                <StepCard doc={doc} />
              ) : (
                <JobCard doc={doc} />
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

function CardShell({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={[
        "flex h-[240px] w-[170px] flex-col overflow-hidden rounded-card border border-border bg-elevated p-3.5 shadow-[0_20px_50px_-20px_rgba(0,0,0,0.6),0_6px_18px_-12px_rgba(45,212,191,0.10)] sm:h-[280px] sm:w-[200px] sm:p-4",
        className ?? "",
      ].join(" ")}
    >
      {children}
    </div>
  );
}

function ResumeCard({ doc }: { doc: ResumeDoc }) {
  const matchSegments = 5;
  const filled = Math.round((doc.match / 100) * matchSegments);

  return (
    <CardShell>
      <div className="flex items-center justify-between">
        <span className="rounded-pill border border-border bg-bg-secondary px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-text-muted">
          Today &middot; Resume
        </span>
        <span className="grid size-5 place-items-center rounded-full border border-border bg-bg-secondary">
          <FileText className="size-2.5 text-text-muted" aria-hidden />
        </span>
      </div>

      <div className="mt-4">
        <p className="text-[14px] font-semibold leading-tight text-text sm:text-[15px]">
          {doc.name}
        </p>
        <p className="mt-0.5 text-[11px] text-text-muted sm:text-[12px]">
          {doc.role} &middot; {doc.yrs} yrs
        </p>
      </div>

      <p className="mt-3 font-mono text-[9px] uppercase tracking-[0.16em] text-subtle">
        Current skills
      </p>
      <div className="mt-1.5 flex flex-wrap gap-1">
        {doc.skills.slice(0, 4).map((s) => (
          <span
            key={s}
            className="inline-flex items-center gap-1 rounded-md border border-matched-border bg-matched-bg px-1.5 py-0.5 font-mono text-[9px] text-matched-text sm:text-[10px]"
          >
            <Check className="size-2.5 stroke-[3]" aria-hidden />
            {s}
          </span>
        ))}
      </div>

      <div className="mt-4 space-y-1.5">
        <div className="h-1 rounded-full bg-bg-secondary" />
        <div className="h-1 w-4/5 rounded-full bg-bg-secondary" />
        <div className="h-1 w-3/5 rounded-full bg-bg-secondary" />
      </div>

      <div className="mt-auto pt-4">
        <div className="flex items-center justify-between border-t border-border pt-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-subtle">
            Current fit
          </span>
          <span className="flex items-center gap-1.5">
            <span className="font-mono text-[12px] font-semibold tabular-nums text-score">
              {doc.match}%
            </span>
            <span className="flex gap-0.5">
              {Array.from({ length: matchSegments }).map((_, i) => (
                <span
                  key={i}
                  className={
                    i < filled
                      ? "size-1 rounded-full bg-score shadow-[0_0_4px_var(--score-glow)]"
                      : "size-1 rounded-full bg-border"
                  }
                />
              ))}
            </span>
          </span>
        </div>
      </div>
    </CardShell>
  );
}

function StepCard({ doc }: { doc: StepDoc }) {
  const Icon = doc.type === "Course" ? GraduationCap : Sparkles;

  return (
    <CardShell>
      <div className="flex items-start justify-between">
        <span className="font-mono text-[28px] font-semibold leading-none tabular-nums text-plan [text-shadow:0_0_18px_var(--plan-glow-soft)]">
          {String(doc.index).padStart(2, "0")}
        </span>
        <span className="rounded-pill border border-plan/40 bg-plan/10 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-plan">
          Step
        </span>
      </div>

      <div className="mt-3">
        <p className="text-[13px] font-semibold leading-tight text-text sm:text-[14px]">
          {doc.title}
        </p>
        <p className="mt-1 inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.14em] text-subtle">
          <Icon className="size-2.5 text-text-muted" aria-hidden />
          {doc.type}
        </p>
      </div>

      <div className="mt-3.5">
        <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-subtle">
          Earns
        </p>
        <span className="mt-1.5 inline-flex items-center gap-1 rounded-md border border-matched-border bg-matched-bg px-1.5 py-0.5 font-mono text-[10px] text-matched-text sm:text-[11px]">
          <Check className="size-2.5 stroke-[3]" aria-hidden />
          {doc.earns}
        </span>
      </div>

      <div className="mt-4 space-y-1.5">
        <div className="h-1 rounded-full bg-bg-secondary" />
        <div className="h-1 w-3/4 rounded-full bg-bg-secondary" />
        <div className="h-1 w-1/2 rounded-full bg-bg-secondary" />
      </div>

      <div className="mt-auto pt-4">
        <div className="flex items-center justify-between border-t border-border pt-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-subtle">
            {doc.hrs} hrs
          </span>
          <span className="font-mono text-[12px] font-semibold tabular-nums text-matched-text">
            {doc.impact}
          </span>
        </div>
      </div>
    </CardShell>
  );
}

function JobCard({ doc }: { doc: JobDoc }) {
  return (
    <CardShell className="bg-gradient-to-b from-[color-mix(in_srgb,var(--score)_10%,var(--bg-elevated))] to-elevated">
      <div className="flex items-center justify-between">
        <span className="rounded-pill border border-score/40 bg-score/15 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.16em] text-score">
          Target &middot; Role
        </span>
        <span className="rounded-md border border-border bg-bg-secondary px-1.5 py-0.5 font-mono text-[9px] text-text">
          {doc.company}
        </span>
      </div>

      <div className="mt-4">
        <p className="text-[13px] font-semibold leading-tight text-text sm:text-[14px]">
          {doc.role}
        </p>
        <p className="mt-1 font-mono text-[10px] tabular-nums text-text-muted sm:text-[11px]">
          {doc.comp} &middot; {doc.loc}
        </p>
      </div>

      <div className="mt-3.5">
        <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-missing-text">
          Missing &middot; required
        </p>
        <div className="mt-1.5 flex flex-wrap gap-1">
          {doc.must.map((s) => (
            <span
              key={s}
              className="inline-flex items-center gap-1 rounded-md border border-missing-border bg-missing-bg px-1.5 py-0.5 font-mono text-[9px] text-missing-text sm:text-[10px]"
            >
              <Plus className="size-2.5 stroke-[3]" aria-hidden />
              {s}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-2.5">
        <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-subtle">
          Preferred
        </p>
        <div className="mt-1.5 flex flex-wrap gap-1">
          {doc.prefer.map((s) => {
            const has = RESUME_SKILLS_LOWER.has(s.toLowerCase());
            return has ? (
              <span
                key={s}
                className="inline-flex items-center gap-1 rounded-md border border-matched-border bg-matched-bg px-1.5 py-0.5 font-mono text-[9px] text-matched-text sm:text-[10px]"
              >
                <Check className="size-2.5 stroke-[3]" aria-hidden />
                {s}
              </span>
            ) : (
              <span
                key={s}
                className="inline-flex items-center gap-1 rounded-md border border-missing-border bg-missing-bg px-1.5 py-0.5 font-mono text-[9px] text-missing-text sm:text-[10px]"
              >
                <Plus className="size-2.5 stroke-[3]" aria-hidden />
                {s}
              </span>
            );
          })}
        </div>
      </div>

      <div className="mt-auto pt-3">
        <div className="flex items-center justify-between border-t border-border pt-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-subtle">
            Projected fit
          </span>
          <span className="flex items-center gap-1.5">
            <span className="font-mono text-[12px] font-semibold tabular-nums text-score">
              {doc.projected}%
            </span>
            <ArrowRight className="size-3 text-score" aria-hidden />
          </span>
        </div>
      </div>
    </CardShell>
  );
}
