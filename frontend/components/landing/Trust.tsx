"use client";

import { motion, useReducedMotion } from "motion/react";
import { ShieldCheck, Lock, FileLock2 } from "lucide-react";

import { ease } from "@/lib/motion";

const VIEWPORT = { once: true, margin: "-80px" } as const;

const POINTS = [
  {
    icon: ShieldCheck,
    title: "No account needed for your first report",
    body: "Run a full analysis without signing up. Sign in only when you want to save versions or revisit a score later.",
  },
  {
    icon: Lock,
    title: "Your resume stays your resume",
    body: "We don't share your resume with employers and we don't use it to train public models. Saved analyses are tied to your account only.",
  },
  {
    icon: FileLock2,
    title: "Built for job seekers, not training data",
    body: "SkillBridge exists to help you land the role. Every product decision starts there, including how we handle your data.",
  },
] as const;

export default function Trust() {
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
    <section id="trust" className="px-6">
      <div className="mx-auto max-w-[960px] pb-[80px] pt-12 md:pb-[100px] md:pt-16">
        <motion.div
          {...fade(0)}
          className="rounded-panel border border-border bg-bg-secondary p-7 md:p-10"
        >
          <div className="flex flex-col gap-3 md:flex-row md:items-baseline md:justify-between md:gap-6">
            <div>
              <p className="text-[12px] font-medium uppercase tracking-[0.18em] text-score">
                Privacy
              </p>
              <h2 className="mt-2 text-[24px] font-semibold leading-[1.2] tracking-[-0.01em] text-text md:text-[28px]">
                Built for job seekers
              </h2>
            </div>
            <p className="max-w-[420px] text-[15px] leading-[1.7] text-text-muted md:text-[16px]">
              Your resume is used to generate your report. That&apos;s it.
              Here&apos;s what that means in practice.
            </p>
          </div>

          <ul className="mt-8 grid gap-5 md:mt-10 md:grid-cols-3 md:gap-6">
            {POINTS.map((p, i) => {
              const Icon = p.icon;
              return (
                <motion.li
                  key={p.title}
                  {...fade(0.1 + i * 0.06)}
                  className="rounded-card border border-border bg-bg p-5"
                >
                  <span className="grid size-9 place-items-center rounded-md border border-score/30 bg-score/10">
                    <Icon className="size-4 text-score" aria-hidden />
                  </span>
                  <h3 className="mt-4 text-[15px] font-semibold leading-snug text-text md:text-[16px]">
                    {p.title}
                  </h3>
                  <p className="mt-2 text-[14px] leading-[1.7] text-text-muted md:text-[15px]">
                    {p.body}
                  </p>
                </motion.li>
              );
            })}
          </ul>
        </motion.div>
      </div>
    </section>
  );
}
