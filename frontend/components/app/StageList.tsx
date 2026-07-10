"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Check } from "lucide-react";

import { ease } from "@/lib/motion";
import { cn } from "@/lib/utils";

type StageState = "pending" | "active" | "done";

type StageListProps = {
  stages: string[];
  /** Index of the currently active stage. Stages before this index are done; after, pending. */
  currentStage: number;
};

export default function StageList({ stages, currentStage }: StageListProps) {
  return (
    <ul className="space-y-5">
      {stages.map((label, i) => {
        const state: StageState =
          i < currentStage ? "done" : i === currentStage ? "active" : "pending";
        return <StageRow key={label} label={label} state={state} />;
      })}
    </ul>
  );
}

function StageRow({ label, state }: { label: string; state: StageState }) {
  return (
    <li className="flex items-center gap-4">
      <Indicator state={state} />
      <span
        className={cn(
          "text-body transition-colors duration-[220ms] ease-out",
          state === "pending" && "text-text-muted",
          state === "active" && "font-medium text-accent",
          state === "done" && "text-text-muted opacity-60",
        )}
      >
        {label}
      </span>
    </li>
  );
}

function Indicator({ state }: { state: StageState }) {
  const reduced = useReducedMotion() ?? false;

  return (
    <div
      className={cn(
        "relative size-6 shrink-0 rounded-full",
        "transition-colors duration-[220ms] ease-out",
        state === "pending" && "border-[1.5px] border-border",
        state === "active" && "border-2 border-accent",
        state === "done" && "border-2 border-accent bg-accent",
      )}
    >
      <AnimatePresence>
        {state === "active" && (
          <motion.span
            key="active-dot"
            initial={{ opacity: 0 }}
            animate={
              reduced
                ? { opacity: 1 }
                : { opacity: 1, scale: [1, 1.1, 1] }
            }
            exit={{ opacity: 0 }}
            transition={
              reduced
                ? { duration: 0.2, ease: ease.out }
                : {
                    opacity: { duration: 0.2, ease: ease.out },
                    scale: {
                      duration: 1.4,
                      repeat: Infinity,
                      ease: "easeInOut",
                    },
                  }
            }
            className="absolute inset-0 m-auto block size-2 rounded-full bg-accent"
            aria-hidden
          />
        )}
        {state === "done" && (
          <motion.span
            key="done-check"
            initial={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.7 }}
            animate={reduced ? { opacity: 1 } : { opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, ease: ease.out }}
            className="absolute inset-0 flex items-center justify-center text-on-accent"
            aria-hidden
          >
            <Check className="size-3.5" strokeWidth={2.5} />
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}
