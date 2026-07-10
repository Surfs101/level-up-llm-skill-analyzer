"use client";

import { useState } from "react";
import { motion, useReducedMotion, AnimatePresence } from "motion/react";
import { Plus } from "lucide-react";

import { ease } from "@/lib/motion";

const VIEWPORT = { once: true, margin: "-80px" } as const;

const QUESTIONS = [
  {
    q: "How is the score calculated?",
    a: "We extract every concrete skill from the role description and split them into required and preferred. Required match counts for 80% of your composite; preferred counts for 20%. Each missing skill shows the exact percentage you'd gain by learning it. The breakdown is always visible, never a black box.",
  },
  {
    q: "Do I have to sign in?",
    a: "No. Your first analysis runs without an account. Sign in only when you want to save analyses, track progress over time, or use the matching jobs feature.",
  },
  {
    q: "Is my resume private?",
    a: "Yes. The first analysis runs without an account so nothing is stored after you close the page. When you sign in, saved analyses are tied to your account only. We never share your resume with employers and we don't use it to train public models.",
  },
  {
    q: "Will it work for non-engineering roles?",
    a: "Yes — anywhere the job description names concrete tools or technologies. Product, design, data, and operations roles all extract cleanly. Roles described purely in soft terms produce thinner skill lists, which the analysis tells you up-front.",
  },
  {
    q: "How is this different from Jobscan or Teal?",
    a: "Those tools optimize for ATS keyword matching. SkillBridge scores skill depth across categories and connects each gap to a concrete next step, not a list of keywords to add.",
  },
] as const;

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(0);
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
    <section id="faq" className="px-6">
      <div className="mx-auto max-w-[760px] pb-[120px] pt-20 md:pb-40 md:pt-16">
        <motion.p
          {...fade(0)}
          className="text-center text-[12px] font-medium uppercase tracking-[0.18em] text-score"
        >
          Questions
        </motion.p>

        <motion.h2
          {...fade(0.05)}
          className="mt-3 text-center text-[32px] font-semibold leading-[1.15] tracking-[-0.02em] text-text md:text-[40px]"
        >
          Common questions
        </motion.h2>

        <ul className="mt-12 divide-y divide-border border-y border-border">
          {QUESTIONS.map((item, i) => {
            const isOpen = open === i;
            return (
              <motion.li
                key={item.q}
                initial={reduced ? { opacity: 0 } : { opacity: 0, y: 6 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={VIEWPORT}
                transition={{
                  duration: 0.3,
                  ease: ease.out,
                  delay: reduced ? 0 : 0.1 + i * 0.04,
                }}
              >
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : i)}
                  className="flex w-full items-center justify-between gap-6 py-5 text-left outline-none focus-visible:ring-2 focus-visible:ring-accent/40 md:py-6"
                  aria-expanded={isOpen}
                >
                  <span className="text-[17px] font-medium leading-snug text-text md:text-[18px]">
                    {item.q}
                  </span>
                  <span
                    className={[
                      "grid size-7 shrink-0 place-items-center rounded-full border text-text-muted transition-all duration-[220ms] ease-out",
                      isOpen
                        ? "rotate-45 border-score/40 bg-score/10 text-score"
                        : "border-border bg-bg-secondary",
                    ].join(" ")}
                    aria-hidden
                  >
                    <Plus className="size-3.5" />
                  </span>
                </button>

                <AnimatePresence initial={false}>
                  {isOpen && (
                    <motion.div
                      key="content"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: ease.inOut }}
                      className="overflow-hidden"
                    >
                      <p className="pb-6 pr-12 text-[15px] leading-[1.75] text-text-muted md:text-[16px]">
                        {item.a}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
