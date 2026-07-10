"use client";

import { motion, useReducedMotion, type Variants } from "motion/react";
import { CheckCircle2, PlusCircle } from "lucide-react";

import { Card, Chip } from "@/components/ui";
import { ease } from "@/lib/motion";
import type { Skill } from "@/lib/mock-data/skills";

type SkillMatchPanelProps = {
  matched: Skill[];
  missing: Skill[];
};

const chipFadeVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.2, ease: ease.out },
  },
};

export default function SkillMatchPanel({ matched, missing }: SkillMatchPanelProps) {
  const reduced = useReducedMotion() ?? false;
  const chipStaggerVariants = {
    hidden: {},
    visible: {
      transition: {
        delayChildren: reduced ? 0 : 0.2,
        staggerChildren: reduced ? 0 : 0.04,
      },
    },
  };

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Panel
        skills={matched}
        label="matched"
        chipVariant="matched"
        icon={<CheckCircle2 className="size-4 text-matched-text" aria-hidden />}
        chipIcon={<CheckCircle2 />}
        staggerVariants={chipStaggerVariants}
      />
      <Panel
        skills={missing}
        label="missing"
        chipVariant="missing"
        icon={<PlusCircle className="size-4 text-missing-text" aria-hidden />}
        chipIcon={<PlusCircle />}
        staggerVariants={chipStaggerVariants}
      />
    </div>
  );
}

type PanelProps = {
  skills: Skill[];
  label: string;
  chipVariant: "matched" | "missing";
  icon: React.ReactNode;
  chipIcon: React.ReactNode;
  staggerVariants: Variants;
};

function Panel({
  skills,
  label,
  chipVariant,
  icon,
  chipIcon,
  staggerVariants,
}: PanelProps) {
  return (
    <Card>
      <div className="flex items-center gap-2">
        {icon}
        <p className="text-h3">
          <span className="font-medium">{skills.length}</span>{" "}
          <span className="text-text-muted">{label}</span>
        </p>
      </div>
      <motion.div
        variants={staggerVariants}
        className="mt-4 flex flex-wrap gap-2"
      >
        {skills.map((s) => (
          <motion.div key={s.id} variants={chipFadeVariants}>
            <Chip variant={chipVariant} icon={chipIcon}>
              {s.canonical_name}
            </Chip>
          </motion.div>
        ))}
      </motion.div>
    </Card>
  );
}
