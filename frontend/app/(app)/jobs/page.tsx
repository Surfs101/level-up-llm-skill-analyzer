"use client";

import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "motion/react";

import JobCard from "@/components/app/JobCard";
import { fetchJobs, type JobMatch } from "@/lib/api/jobs";
import type { SkillRef } from "@/lib/api/plans";
import { ease } from "@/lib/motion";
import type { Job } from "@/lib/mock-data/jobs";
import type { Skill } from "@/lib/mock-data/skills";

const cardStaggerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

export default function JobsPage() {
  const reduced = useReducedMotion() ?? false;
  const cardFadeUpVariants = {
    hidden: reduced ? { opacity: 0 } : { opacity: 0, y: 8 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.25, ease: ease.out },
    },
  };
  const [jobs, setJobs] = useState<JobMatch[] | null>(null);

  useEffect(() => {
    fetchJobs()
      .then(setJobs)
      .catch(() => setJobs([]));
  }, []);

  return (
    <div>
      <header>
        <h1 className="text-h3">Your top job matches</h1>
        <p className="mt-2 max-w-[640px] text-[14px] text-text-muted">
          We&apos;ve ranked recent postings by overlap with your skill profile.
          Red chips show the gap you&apos;d need to fill for each role.
        </p>
      </header>

      <motion.div
        initial="hidden"
        animate="visible"
        variants={cardStaggerVariants}
        className="mt-8 space-y-4"
      >
        {(jobs ?? []).map((job) => (
          <motion.div key={job.id} variants={cardFadeUpVariants}>
            <JobCard
              job={toJob(job)}
              matchedSkills={job.matched_skills.map(toSkill)}
              missingSkills={job.missing_skills.map(toSkill)}
            />
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
}

// Shape the API's JobMatch into the mock Job type JobCard already renders (ids only;
// JobCard reads matched_skills.length and skills.length for the "X of Y" count).
function toJob(job: JobMatch): Job {
  return {
    id: job.id,
    company: job.company,
    title: job.title,
    location: job.location ?? "",
    posted_at: job.posted_at,
    skills: [...job.matched_skills, ...job.missing_skills].map((s) => s.id),
    matched_skills: job.matched_skills.map((s) => s.id),
    missing_skills: job.missing_skills.map((s) => s.id),
  };
}

function toSkill(ref: SkillRef): Skill {
  return {
    id: ref.id,
    canonical_name: ref.display_name,
    category: ref.category as Skill["category"],
    aliases: [],
  };
}
