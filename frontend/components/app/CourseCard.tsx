"use client";

import { motion, useReducedMotion } from "motion/react";
import { Sparkles } from "lucide-react";

import { Card, Chip } from "@/components/ui";
import { ease } from "@/lib/motion";
import type { Course } from "@/lib/mock-data/courses";
import type { Skill } from "@/lib/mock-data/skills";

type CourseCardProps = {
  rank: 1 | 2;
  course: Course;
  skillsCovered: Skill[];
};

const chipFadeVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.2, ease: ease.out },
  },
};

export default function CourseCard({ rank, course, skillsCovered }: CourseCardProps) {
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
  const badgeText = rank === 1 ? "Covers most of your gap" : "Covers the rest";
  return (
    <Card className="border-l-2 border-l-score">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-caption uppercase tracking-wide text-text-muted">
            {course.provider}
          </p>
          <h3 className="mt-1 text-h5">{course.title}</h3>
          <p className="mt-2 line-clamp-2 text-[14px] leading-[1.6] text-text-muted">
            {course.description}
          </p>
        </div>
        <span className="shrink-0 rounded-pill border border-score-border bg-score-bg px-2.5 py-1 text-caption text-score">
          {badgeText}
        </span>
      </div>
      <motion.div
        variants={chipStaggerVariants}
        className="mt-4 flex flex-wrap items-center gap-2"
      >
        <span className="text-caption text-text-muted">Covers:</span>
        {skillsCovered.map((s) => (
          <motion.div key={s.id} variants={chipFadeVariants}>
            <Chip variant="score" icon={<Sparkles />}>
              {s.canonical_name}
            </Chip>
          </motion.div>
        ))}
      </motion.div>
    </Card>
  );
}
