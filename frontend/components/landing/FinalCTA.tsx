"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

import { ease } from "@/lib/motion";

const VIEWPORT = { once: true, margin: "-80px" } as const;

const PULSE_LOW = "0 0 24px var(--accent-glow-soft)";
const PULSE_HIGH = "0 0 24px var(--accent-glow)";

export default function FinalCTA() {
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
    <section className="px-6">
      <div className="mx-auto max-w-[860px] pb-[120px] pt-20 md:pb-40 md:pt-24">
        <motion.div
          {...fade(0)}
          className="relative overflow-hidden rounded-panel border border-border bg-elevated px-8 py-14 text-center md:px-14 md:py-20"
        >
          <span
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-px"
            style={{
              background:
                "linear-gradient(90deg, transparent, color-mix(in srgb, var(--accent) 50%, transparent), transparent)",
            }}
          />

          <p className="text-[12px] font-medium uppercase tracking-[0.18em] text-accent">
            Run an analysis
          </p>

          <h2 className="mt-4 text-[32px] font-semibold leading-[1.15] tracking-[-0.02em] text-text md:text-[44px]">
            Ready to see what is missing from your resume?
          </h2>

          <p className="mx-auto mt-5 max-w-[540px] text-[16px] leading-[1.7] text-text-muted md:text-[17px]">
            Get a clear fit score, missing skills, and a practical plan
            before you apply.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/analyze"
              className="inline-block rounded-btn outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
            >
              <motion.span
                animate={
                  reduced
                    ? { boxShadow: PULSE_LOW }
                    : { boxShadow: [PULSE_LOW, PULSE_HIGH, PULSE_LOW] }
                }
                transition={
                  reduced
                    ? { duration: 0 }
                    : { duration: 3, repeat: Infinity, ease: "easeInOut" }
                }
                whileTap={{ scale: 0.97 }}
                className="inline-flex h-12 items-center gap-2 rounded-btn bg-accent px-6 font-medium text-on-accent transition-colors duration-200 ease-out hover:bg-accent-hover [&>svg]:size-[18px]"
              >
                Analyze my resume
                <ArrowRight aria-hidden />
              </motion.span>
            </Link>

            <Link
              href="/#how-it-works"
              className="inline-flex h-12 items-center justify-center rounded-btn border border-strong px-6 font-medium text-text transition-colors duration-200 ease-out hover:bg-bg-secondary"
            >
              See how it works
            </Link>
          </div>

          <p className="mt-6 font-mono text-[12px] uppercase tracking-[0.18em] text-text-muted">
            Free first report &middot; No signup required &middot; Resume stays private
          </p>
        </motion.div>
      </div>
    </section>
  );
}
