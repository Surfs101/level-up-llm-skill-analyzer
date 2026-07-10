"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { ArrowUpDown, Filter } from "lucide-react";

import PlanRow from "@/components/app/PlanRow";
import { Button, ButtonLink, Divider } from "@/components/ui";
import { deletePlan, fetchPlanSummaries, type PlanSummary } from "@/lib/api/plans";
import { ease } from "@/lib/motion";

const rowStaggerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04 } },
};

export default function SavedPage() {
  const reduced = useReducedMotion() ?? false;
  const rowFadeUpVariants = {
    hidden: reduced ? { opacity: 0 } : { opacity: 0, y: 8 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.25, ease: ease.out },
    },
  };
  const [plans, setPlans] = useState<PlanSummary[] | null>(null);

  useEffect(() => {
    fetchPlanSummaries()
      .then(setPlans)
      .catch(() => setPlans([]));
  }, []);

  async function handleDelete(id: string) {
    setPlans((current) => (current ?? []).filter((p) => p.id !== id));
    try {
      await deletePlan(id);
    } catch {
      // Refetch to resync if the delete didn't land.
      fetchPlanSummaries()
        .then(setPlans)
        .catch(() => setPlans([]));
    }
  }

  return (
    <div>
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-h3">Saved plans</h1>
          <p className="mt-2 text-[14px] text-text-muted">
            Review your saved plans and skill gap analyses.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" leftIcon={<Filter />}>
            Filter
          </Button>
          <Button variant="secondary" size="sm" leftIcon={<ArrowUpDown />}>
            Sort by date
          </Button>
        </div>
      </header>

      <div className="mt-8">
        {plans !== null && plans.length === 0 ? (
          <EmptyState />
        ) : (
          <motion.div
            initial="hidden"
            animate="visible"
            variants={rowStaggerVariants}
          >
            {(plans ?? []).map((plan, i) => (
              <motion.div key={plan.id} variants={rowFadeUpVariants}>
                {i > 0 && <Divider spacing="none" />}
                <PlanRow plan={plan} onDelete={handleDelete} />
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center py-20 text-center">
      <p className="text-body">No saved plans yet</p>
      <div className="mt-4">
        <ButtonLink href="/analyze">Start a new analysis</ButtonLink>
      </div>
    </div>
  );
}
