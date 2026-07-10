"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import PlanView from "@/components/app/PlanView";
import StickySaveBar from "@/components/app/StickySaveBar";
import { fetchPlanDetail, type PlanDetail } from "@/lib/api/plans";

export default function PlanPage({ params }: { params: { id: string } }) {
  const [plan, setPlan] = useState<PlanDetail | null>(null);

  useEffect(() => {
    fetchPlanDetail(params.id)
      .then(setPlan)
      .catch(() => setPlan(null));
  }, [params.id]);

  if (!plan) return null;

  return (
    <div className="pb-32">
      <Link
        href="/saved"
        className="inline-flex items-center gap-1.5 text-caption text-text-muted transition-colors duration-[140ms] ease-out hover:text-text"
      >
        <ArrowLeft className="size-3.5" aria-hidden />
        Back to saved plans
      </Link>

      <PlanView plan={plan} />

      <StickySaveBar />
    </div>
  );
}
