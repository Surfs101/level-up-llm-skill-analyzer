"use client";

import Link from "next/link";
import { Building, ChevronRight, Trash2 } from "lucide-react";

import { Chip } from "@/components/ui";
import { formatDate } from "@/lib/format";
import type { PlanSummary } from "@/lib/api/plans";

type PlanRowProps = {
  plan: PlanSummary;
  onDelete: (id: string) => void;
};

// The backend doesn't store a JD title/company (no source yet), so derive a heading
// from the first line of the job description.
function planHeading(jdText: string): string {
  const firstLine = jdText.trim().split("\n")[0] ?? "";
  if (!firstLine) return "Untitled analysis";
  return firstLine.length > 80 ? `${firstLine.slice(0, 80)}…` : firstLine;
}

export default function PlanRow({ plan, onDelete }: PlanRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-5 transition-colors duration-[140ms] ease-out hover:bg-bg-secondary">
      <Link href={`/plans/${plan.id}`} className="min-w-0 flex-1">
        <p className="truncate text-body font-medium">{planHeading(plan.jd_text)}</p>
        <p className="mt-1 inline-flex items-center gap-1.5 text-caption text-text-muted">
          <Building className="size-3.5" aria-hidden />
          {formatDate(plan.created_at)} · Fit {plan.fit_score}
        </p>
      </Link>
      <div className="flex shrink-0 items-center gap-2">
        <Chip variant="matched">{plan.matched_count} matched</Chip>
        <Chip variant="missing">{plan.missing_count} missing</Chip>
        <button
          type="button"
          onClick={() => onDelete(plan.id)}
          aria-label="Delete plan"
          className="rounded-md p-1 text-text-muted outline-none transition-colors duration-[140ms] ease-out hover:text-missing-text focus-visible:ring-2 focus-visible:ring-accent/40"
        >
          <Trash2 className="size-4" aria-hidden />
        </button>
        <ChevronRight className="size-4 text-text-muted" aria-hidden />
      </div>
    </div>
  );
}
