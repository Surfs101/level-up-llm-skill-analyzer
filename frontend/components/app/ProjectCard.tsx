"use client";

import { motion, useReducedMotion } from "motion/react";
import { Lightbulb, TrendingUp, Zap } from "lucide-react";

import { Card, Chip } from "@/components/ui";
import { ease } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { PlanProject } from "@/lib/mock-data/plans";
import type { Skill } from "@/lib/mock-data/skills";

type ProjectCardProps = {
  project: PlanProject;
  techStack: Skill[];
};

const chipFadeVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.2, ease: ease.out },
  },
};

export default function ProjectCard({ project, techStack }: ProjectCardProps) {
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
  const isCurrent = project.kind === "current";
  const Icon = isCurrent ? Zap : TrendingUp;
  const badgeText = isCurrent ? "Build with what you have" : "Build after Course 1";

  return (
    <Card>
      <span
        className={cn(
          "inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-caption",
          isCurrent ? "bg-bg-secondary text-text" : "text-accent",
        )}
        style={
          isCurrent
            ? undefined
            : {
                backgroundColor:
                  "color-mix(in srgb, var(--accent) 12%, transparent)",
              }
        }
      >
        <Icon className="size-3.5" aria-hidden />
        {badgeText}
      </span>

      <h3 className="mt-3 text-h5">{project.title}</h3>

      <p className="mt-3 text-[14px] leading-[1.6]">
        <span className="font-medium">Problem statement:</span>{" "}
        <span className="text-text-muted">{project.problem_statement}</span>
      </p>

      <motion.div
        variants={chipStaggerVariants}
        className="mt-4 flex flex-wrap items-center gap-2"
      >
        <span className="text-caption text-text-muted">Tech stack:</span>
        {techStack.map((s) => (
          <motion.div key={s.id} variants={chipFadeVariants}>
            <Chip variant="neutral">{s.canonical_name}</Chip>
          </motion.div>
        ))}
      </motion.div>

      <div className="mt-4">
        <p className="text-caption text-text-muted">Milestones:</p>
        <ul className="mt-2 space-y-1.5">
          {project.milestones.map((m) => (
            <li key={m} className="flex gap-2 text-body">
              <span className="text-text-muted" aria-hidden>
                ·
              </span>
              <span>{m}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-5 rounded-card border border-border bg-elevated p-4">
        <div className="flex items-start gap-2">
          <Lightbulb
            className="mt-0.5 size-4 shrink-0 text-text-muted"
            aria-hidden
          />
          <div>
            <p className="text-caption text-text-muted">
              What to highlight in your README:
            </p>
            <p className="mt-1 text-body italic">{project.readme_highlight}</p>
          </div>
        </div>
      </div>
    </Card>
  );
}
