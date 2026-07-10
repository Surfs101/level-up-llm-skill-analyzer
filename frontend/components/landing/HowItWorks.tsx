"use client";

import { motion, useReducedMotion } from "motion/react";
import { Check, FileText } from "lucide-react";

import { ease } from "@/lib/motion";

const VIEWPORT = { once: true, margin: "-80px" } as const;

export default function HowItWorks() {
  const reduced = useReducedMotion() ?? false;

  function fade(delay: number) {
    return {
      initial: reduced ? { opacity: 0 } : { opacity: 0, y: 12 },
      whileInView: { opacity: 1, y: 0 },
      viewport: VIEWPORT,
      transition: { duration: 0.3, ease: ease.out, delay: reduced ? 0 : delay },
    };
  }

  return (
    <section id="how-it-works" className="px-6">
      <div className="mx-auto max-w-[1100px] pb-[120px] pt-20 md:pb-40 md:pt-16">
        <motion.p
          {...fade(0)}
          className="text-center text-[12px] font-medium uppercase tracking-[0.18em] text-score"
        >
          How it works
        </motion.p>

        <motion.h2
          {...fade(0.05)}
          className="mt-3 text-center text-[34px] font-semibold leading-[1.15] tracking-[-0.02em] text-text md:text-[44px]"
        >
          Three steps from resume to plan
        </motion.h2>

        <div className="relative mt-16 grid gap-8 md:mt-20 md:grid-cols-3 md:gap-6">
          <span
            aria-hidden
            className="pointer-events-none absolute left-[8%] right-[8%] top-[28px] hidden h-px bg-gradient-to-r from-transparent via-border-strong to-transparent md:block"
          />

          <Step
            index={1}
            title="Upload resume and role"
            description="Drop a resume in PDF or paste plain text, then paste the job description. SkillBridge parses both into structured skills."
            delay={0.1}
            visual={<UploadVisual />}
          />
          <Step
            index={2}
            title="Score fit, not keywords"
            description="Required skills weigh heavier than preferred. The composite tells you the gap; the breakdown tells you which skills carry it."
            delay={0.18}
            visual={<ScoreVisual />}
          />
          <Step
            index={3}
            title="Get a plan you can act on"
            description="Each gap maps to focused courses, project ideas, and practice prompts, ordered by impact on your score."
            delay={0.26}
            visual={<PlanVisual />}
          />
        </div>
      </div>
    </section>
  );
}

function Step({
  index,
  title,
  description,
  delay,
  visual,
}: {
  index: number;
  title: string;
  description: string;
  delay: number;
  visual: React.ReactNode;
}) {
  const reduced = useReducedMotion() ?? false;

  return (
    <motion.div
      initial={reduced ? { opacity: 0 } : { opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={VIEWPORT}
      transition={{ duration: 0.3, ease: ease.out, delay: reduced ? 0 : delay }}
      className="relative flex flex-col items-center text-center"
    >
      <span
        className="relative z-10 grid size-14 place-items-center rounded-full border border-plan/30 bg-bg shadow-[0_0_24px_var(--plan-glow-soft)]"
        aria-hidden
      >
        <span className="font-mono text-[18px] font-semibold tabular-nums text-plan">
          {String(index).padStart(2, "0")}
        </span>
      </span>

      <div className="mt-7 w-full">{visual}</div>

      <h3 className="mt-7 text-[19px] font-semibold leading-[1.3] text-text">
        {title}
      </h3>
      <p className="mx-auto mt-2 max-w-[320px] text-[15px] leading-[1.7] text-text-muted">
        {description}
      </p>
    </motion.div>
  );
}

function UploadVisual() {
  return (
    <div className="relative mx-auto h-[120px] w-full max-w-[260px] overflow-hidden rounded-card border border-dashed border-score/30 bg-bg-secondary">
      <div className="absolute inset-0 grid place-items-center">
        <div className="flex flex-col items-center gap-2">
          <span className="grid size-9 place-items-center rounded-card border border-border bg-elevated">
            <FileText className="size-4 text-score" aria-hidden />
          </span>
          <span className="font-mono text-[11px] text-text-muted">resume.pdf</span>
          <span className="text-[10px] uppercase tracking-[0.18em] text-subtle">
            Drop to analyze
          </span>
        </div>
      </div>
    </div>
  );
}

function ScoreVisual() {
  return (
    <div className="relative mx-auto h-[120px] w-full max-w-[260px] overflow-hidden rounded-card border border-border bg-bg-secondary p-4">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-[28px] font-semibold leading-none tracking-tight text-score [text-shadow:0_0_18px_var(--score-glow)]">
          74%
        </span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-subtle">
          fit
        </span>
      </div>

      <div className="mt-4 space-y-3">
        <WeightLine
          label="Required"
          weight="×0.8"
          pct={77}
          tone="accent"
        />
        <WeightLine
          label="Preferred"
          weight="×0.2"
          pct={62}
          tone="muted"
        />
      </div>
    </div>
  );
}

function WeightLine({
  label,
  weight,
  pct,
  tone,
}: {
  label: string;
  weight: string;
  pct: number;
  tone: "accent" | "muted";
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={
          tone === "accent"
            ? "rounded-pill border border-score/40 bg-score/10 px-1.5 py-0 font-mono text-[8px] uppercase tracking-[0.14em] text-score"
            : "rounded-pill border border-border bg-bg px-1.5 py-0 font-mono text-[8px] uppercase tracking-[0.14em] text-text-muted"
        }
      >
        {label}
      </span>
      <span className="h-1 flex-1 overflow-hidden rounded-full bg-bg">
        <span
          className="block h-full rounded-full"
          style={{
            width: `${pct}%`,
            background:
              tone === "accent"
                ? "linear-gradient(90deg, var(--score), color-mix(in srgb, var(--score) 50%, transparent))"
                : "linear-gradient(90deg, var(--text-muted), color-mix(in srgb, var(--text-muted) 30%, transparent))",
            boxShadow:
              tone === "accent" ? "0 0 8px var(--score-glow-soft)" : "none",
          }}
        />
      </span>
      <span className="w-8 shrink-0 text-right font-mono text-[9px] tabular-nums text-text-muted">
        {weight}
      </span>
    </div>
  );
}

function PlanVisual() {
  const items = [
    { label: "Read: Designing Data-Intensive Apps", done: true },
    { label: "Build: gRPC service prototype", done: true },
    { label: "Course: Distributed Systems", done: false },
  ] as const;

  return (
    <div className="relative mx-auto h-[120px] w-full max-w-[260px] overflow-hidden rounded-card border border-border bg-bg-secondary p-3">
      <ul className="space-y-1.5">
        {items.map((it, i) => (
          <li
            key={i}
            className="flex items-center gap-2 rounded-md border border-border bg-bg px-2.5 py-1.5"
          >
            <span
              className={
                it.done
                  ? "grid size-4 shrink-0 place-items-center rounded-full border border-matched-border bg-matched-bg text-matched-text"
                  : "grid size-4 shrink-0 place-items-center rounded-full border border-border bg-elevated"
              }
            >
              {it.done && <Check className="size-2.5 stroke-[3]" aria-hidden />}
            </span>
            <span
              className={
                it.done
                  ? "truncate text-[11px] text-text-muted line-through"
                  : "truncate text-[11px] text-text"
              }
            >
              {it.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
