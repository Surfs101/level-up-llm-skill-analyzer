"use client";

import { useRouter } from "next/navigation";
import { CheckCircle2, ExternalLink, PlusCircle, Target } from "lucide-react";

import { Button, Card, Chip, Divider } from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { Job } from "@/lib/mock-data/jobs";
import type { Skill } from "@/lib/mock-data/skills";

type JobCardProps = {
  job: Job;
  matchedSkills: Skill[];
  missingSkills: Skill[];
};

export default function JobCard({ job, matchedSkills, missingSkills }: JobCardProps) {
  const router = useRouter();

  return (
    <Card>
      <div className="flex items-start gap-3">
        <CompanyLogo company={job.company} />
        <div className="min-w-0 flex-1">
          <h3 className="text-h5">{job.title}</h3>
          <p className="mt-1 text-[14px] text-text-muted">
            {job.company} · {job.location} · {formatDate(job.posted_at)}
          </p>
        </div>
      </div>

      <p className="mt-4 inline-flex items-center gap-1.5 text-caption uppercase tracking-wide text-text-muted">
        <Target className="size-3.5" aria-hidden />
        Skill overlap: {job.matched_skills.length} of {job.skills.length} matched
      </p>

      <div className="mt-2 flex flex-wrap gap-2">
        {matchedSkills.map((skill) => (
          <Chip key={skill.id} variant="matched" icon={<CheckCircle2 />}>
            {skill.canonical_name}
          </Chip>
        ))}
        {missingSkills.map((skill) => (
          <Chip key={skill.id} variant="missing" icon={<PlusCircle />}>
            {skill.canonical_name}
          </Chip>
        ))}
      </div>

      <Divider spacing="md" />

      <div className="flex flex-wrap justify-end gap-3">
        <Button variant="secondary" leftIcon={<ExternalLink />}>
          View posting
        </Button>
        <Button
          onClick={() => router.push("/analyze")}
          className="whitespace-nowrap"
        >
          Make a gap plan for this job
        </Button>
      </div>
    </Card>
  );
}

function CompanyLogo({ company }: { company: string }) {
  return (
    <div
      className="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated text-[14px] font-medium text-text-muted"
      aria-hidden
    >
      {company[0]}
    </div>
  );
}

