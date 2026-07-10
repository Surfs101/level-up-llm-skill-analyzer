"use client";

import { motion, useReducedMotion } from "motion/react";
import { Check, X } from "lucide-react";

import { ease } from "@/lib/motion";

const VIEWPORT = { once: true, margin: "-80px" } as const;

const COUNTS_AS_SKILL = [
  "Languages, frameworks, runtimes",
  "Databases, queues, caches",
  "Cloud providers, services, infra tools",
  "Libraries and concrete protocols (gRPC, REST, GraphQL)",
];

const DOES_NOT_COUNT = [
  "Years of experience",
  "Vague soft skills",
  "Domain buzzwords without a tool behind them",
  "Keywords that aren't teachable in a course",
];

export default function Dimensions() {
  const reduced = useReducedMotion() ?? false;

  function fade(delay: number) {
    return {
      initial: reduced ? { opacity: 0 } : { opacity: 0, y: 8 },
      whileInView: { opacity: 1, y: 0 },
      viewport: VIEWPORT,
      transition: { duration: 0.3, ease: ease.out, delay: reduced ? 0 : delay },
    };
  }

  return (
    <section className="px-6">
      <div className="mx-auto max-w-[1000px] pb-[120px] pt-20 md:pb-40 md:pt-16">
        <div className="grid gap-10 md:grid-cols-[minmax(0,360px)_1fr] md:items-start md:gap-16">
          <div className="md:sticky md:top-24">
            <motion.p
              {...fade(0)}
              className="text-[12px] font-medium uppercase tracking-[0.18em] text-score"
            >
              Scoring model
            </motion.p>
            <motion.h2
              {...fade(0.05)}
              className="mt-3 text-[30px] font-semibold leading-[1.15] tracking-[-0.02em] text-text md:text-[36px]"
            >
              We score the skills you can actually learn
            </motion.h2>
            <motion.p
              {...fade(0.12)}
              className="mt-4 text-[16px] leading-[1.7] text-text-muted"
            >
              Forget categories like &quot;methodology&quot; or
              &quot;soft skills.&quot; SkillBridge extracts every concrete
              skill from the role, the things you can pick up in a course or
              on the job, and weights what&apos;s required higher than
              what&apos;s preferred.
            </motion.p>
          </div>

          <div className="space-y-8">
            <motion.div {...fade(0.15)}>
              <p className="text-[12px] font-medium uppercase tracking-[0.16em] text-subtle">
                The weights
              </p>
              <div className="mt-4 rounded-card border border-border bg-bg-secondary p-5">
                <WeightRow
                  label="Required"
                  weight={0.8}
                  width="100%"
                  tone="accent"
                  caption="Must-haves named in the role description"
                />
                <div className="my-4 h-px bg-border" />
                <WeightRow
                  label="Preferred"
                  weight={0.2}
                  width="40%"
                  tone="muted"
                  caption="Nice-to-haves and listed bonuses"
                />
                <div className="mt-5 flex items-center gap-2 border-t border-border pt-4 font-mono text-[12px] text-text-muted">
                  <span className="text-text">composite</span>
                  <span>&nbsp;=&nbsp;</span>
                  <span>required &times; 0.8</span>
                  <span>+</span>
                  <span>preferred &times; 0.2</span>
                </div>
              </div>
            </motion.div>

            <motion.div
              {...fade(0.22)}
              className="grid gap-4 sm:grid-cols-2"
            >
              <div className="rounded-card border border-matched-border bg-matched-bg/30 p-5">
                <p className="text-[12px] font-medium uppercase tracking-[0.16em] text-matched-text">
                  Counts as a skill
                </p>
                <ul className="mt-3 space-y-2.5">
                  {COUNTS_AS_SKILL.map((item) => (
                    <li key={item} className="flex gap-2.5">
                      <span
                        className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full border border-matched-border bg-matched-bg text-matched-text"
                        aria-hidden
                      >
                        <Check className="size-2.5 stroke-[3]" />
                      </span>
                      <span className="text-[14px] leading-[1.6] text-text">
                        {item}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-card border border-border bg-bg-secondary p-5">
                <p className="text-[12px] font-medium uppercase tracking-[0.16em] text-subtle">
                  Doesn&apos;t count
                </p>
                <ul className="mt-3 space-y-2.5">
                  {DOES_NOT_COUNT.map((item) => (
                    <li key={item} className="flex gap-2.5">
                      <span
                        className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full border border-border bg-bg text-text-muted"
                        aria-hidden
                      >
                        <X className="size-2.5 stroke-[3]" />
                      </span>
                      <span className="text-[14px] leading-[1.6] text-text-muted">
                        {item}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}

function WeightRow({
  label,
  weight,
  width,
  tone,
  caption,
}: {
  label: string;
  weight: number;
  width: string;
  tone: "accent" | "muted";
  caption: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={
              tone === "accent"
                ? "rounded-pill border border-score/40 bg-score/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-score"
                : "rounded-pill border border-border bg-bg px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted"
            }
          >
            {label}
          </span>
          <span className="font-mono text-[12px] tabular-nums text-text-muted">
            weight &times;{weight.toFixed(1)}
          </span>
        </div>
      </div>
      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-bg">
        <div
          className="h-full rounded-full"
          style={{
            width,
            background:
              tone === "accent"
                ? "linear-gradient(90deg, var(--score), color-mix(in srgb, var(--score) 60%, transparent))"
                : "linear-gradient(90deg, var(--text-muted), color-mix(in srgb, var(--text-muted) 30%, transparent))",
            boxShadow:
              tone === "accent"
                ? "0 0 12px var(--score-glow-soft)"
                : "none",
          }}
        />
      </div>
      <p className="mt-2 text-[13px] leading-[1.6] text-text-muted">
        {caption}
      </p>
    </div>
  );
}
