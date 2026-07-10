"use client";

import { useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { Bookmark, Check } from "lucide-react";

import { Button } from "@/components/ui";
import { ease } from "@/lib/motion";

export default function StickySaveBar() {
  const reduced = useReducedMotion() ?? false;
  const [saved, setSaved] = useState(false);

  return (
    <motion.div
      initial={reduced ? { opacity: 0 } : { y: 40, opacity: 0 }}
      animate={reduced ? { opacity: 1 } : { y: 0, opacity: 1 }}
      transition={{ duration: 0.25, delay: 0.4, ease: ease.drawer }}
      className="fixed bottom-6 left-1/2 z-30 w-[calc(100%-48px)] max-w-[720px] -translate-x-1/2 rounded-card border border-border bg-elevated p-4"
      style={{ boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)" }}
      role="region"
      aria-label="Save plan"
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-2">
          <AnimatePresence mode="wait" initial={false}>
            {saved ? (
              <motion.span
                key="saved-icon"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2, ease: ease.out }}
                className="flex"
              >
                <Check
                  className="size-4 shrink-0 text-matched-text"
                  aria-hidden
                />
              </motion.span>
            ) : (
              <motion.span
                key="save-icon"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15, ease: ease.out }}
                className="flex"
              >
                <Bookmark
                  className="size-4 shrink-0 text-text-muted"
                  aria-hidden
                />
              </motion.span>
            )}
          </AnimatePresence>
          <p className="truncate text-body">
            {saved ? "Plan saved" : "Save this plan to your dashboard"}
          </p>
        </div>
        <Button
          onClick={() => setSaved(true)}
          disabled={saved}
          leftIcon={saved ? <Check /> : undefined}
          className="shrink-0"
        >
          {saved ? "Saved" : "Save plan"}
        </Button>
      </div>
    </motion.div>
  );
}
