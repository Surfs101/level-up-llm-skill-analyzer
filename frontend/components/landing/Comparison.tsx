"use client";

import { motion, useReducedMotion } from "motion/react";
import { Check, X } from "lucide-react";

import GlowSection from "@/components/landing/GlowSection";
import { ease } from "@/lib/motion";

const TYPICAL_BULLETS: string[] = [
  "Resumes treated like bags of words. Easy to game, noisy for technical roles.",
  "One opaque percentage with no sense of which skills move the needle.",
  "Leaves you guessing what to study next, or pushes unrelated certificates.",
  "Hard to revisit progress across resume versions and interviews.",
];

const SKILLBRIDGE_BULLETS: string[] = [
  "Every concrete skill is extracted, not just keyword surface area.",
  "Required and preferred are scored separately, with required weighing higher.",
  "Each gap maps to specific courses and project ideas, ordered by score impact.",
  "Signed-in history keeps analyses, resumes, and plans aligned over time.",
];

const VIEWPORT = { once: true, margin: "-80px" } as const;

export default function Comparison() {
  const reduced = useReducedMotion() ?? false;

  function fade(delay: number) {
    return {
      initial: reduced ? { opacity: 0 } : { opacity: 0, y: 8 },
      whileInView: { opacity: 1, y: 0 },
      viewport: VIEWPORT,
      transition: {
        duration: 0.3,
        ease: ease.out,
        delay: reduced ? 0 : delay,
      },
    };
  }

  return (
    <section className="overflow-visible px-6">
      <div className="mx-auto max-w-[1080px] overflow-visible pb-[120px] pt-20 md:pb-40 md:pt-16">
        <div className="grid items-start gap-10 md:grid-cols-12 md:gap-12">
          <div className="md:col-span-5 md:sticky md:top-24">
            <p className="text-[12px] font-medium uppercase tracking-[0.18em] text-score">
              The difference
            </p>
            <motion.h2
              {...fade(0.05)}
              className="mt-3 text-[32px] font-semibold leading-[1.12] tracking-[-0.02em] text-text md:text-[44px]"
            >
              Most tools count keywords.
              <br />
              <span className="text-text-muted">We score skill depth.</span>
            </motion.h2>
            <motion.p
              {...fade(0.12)}
              className="mt-5 max-w-[420px] text-[16px] leading-[1.7] text-text-muted"
            >
              A keyword match tells you whether the word is on the page. A
              skill score tells you whether you can do the job. The
              difference shows up in the second interview.
            </motion.p>
          </div>

          <div className="space-y-4 md:col-span-7">
            <motion.div
              {...fade(0.18)}
              className="rounded-card border border-border bg-bg-secondary p-7"
            >
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-[16px] font-semibold leading-snug text-text-muted">
                  Generic keyword tools
                </h3>
                <span className="rounded-pill border border-border bg-bg px-2.5 py-1 text-[11px] uppercase tracking-[0.14em] text-subtle">
                  Typical
                </span>
              </div>
              <ul className="mt-5 space-y-3.5">
                {TYPICAL_BULLETS.map((text) => (
                  <li key={text} className="flex gap-3">
                    <span
                      className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border border-border bg-bg text-text-muted"
                      aria-hidden
                    >
                      <X className="size-3 stroke-[2.5]" />
                    </span>
                    <span className="text-[15px] leading-[1.7] text-text-muted">
                      {text}
                    </span>
                  </li>
                ))}
              </ul>
            </motion.div>

            <motion.div {...fade(0.24)}>
              <GlowSection innerClassName="p-7">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-[16px] font-semibold leading-snug text-text">
                    SkillBridge
                  </h3>
                  <span className="rounded-pill border border-score/30 bg-score/10 px-2.5 py-1 text-[11px] uppercase tracking-[0.14em] text-score">
                    Our approach
                  </span>
                </div>
                <ul className="mt-5 space-y-3.5">
                  {SKILLBRIDGE_BULLETS.map((text) => (
                    <li key={text} className="flex gap-3">
                      <span
                        className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border border-matched-border bg-matched-bg text-matched-text"
                        aria-hidden
                      >
                        <Check className="size-3 stroke-[2.5]" />
                      </span>
                      <span className="text-[15px] leading-[1.7] text-text">
                        {text}
                      </span>
                    </li>
                  ))}
                </ul>
              </GlowSection>
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}
