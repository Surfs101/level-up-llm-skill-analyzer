"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Clock } from "lucide-react";

import PlanView from "@/components/app/PlanView";
import StageList from "@/components/app/StageList";
import { ButtonLink } from "@/components/ui";
import { fetchRunStatus } from "@/lib/api/analyze";
import type { PlanDetail } from "@/lib/api/plans";

const STAGES = [
  "Parsing your resume",
  "Extracting your skills",
  "Reading the job description",
  "Finding the gap",
  "Picking your courses",
  "Generating your projects",
];

const POLL_INTERVAL_MS = 1000;

export default function RunningPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  // ui_stage from the API: 0..5 while running, 6 when every stage is done.
  const [uiStage, setUiStage] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [failed, setFailed] = useState(false);
  // A guest has no saved plan to navigate to — the plan comes back inline.
  const [guestPlan, setGuestPlan] = useState<PlanDetail | null>(null);

  // Poll the run until it completes (→ its plan) or fails.
  useEffect(() => {
    let active = true;

    async function poll() {
      try {
        const run = await fetchRunStatus(params.id);
        if (!active) return;
        setUiStage(run.ui_stage);
        if (run.status === "completed") {
          if (run.plan_id) {
            router.push(`/plans/${run.plan_id}`); // signed-in → the saved plan
          } else if (run.plan) {
            setGuestPlan(run.plan); // guest → render inline, no navigation
          }
          return;
        }
        if (run.status === "failed") {
          setFailed(true);
          return;
        }
      } catch {
        // transient error — keep polling
      }
      if (active) setTimeout(poll, POLL_INTERVAL_MS);
    }

    poll();
    return () => {
      active = false;
    };
  }, [params.id, router]);

  // Elapsed time ticker, 1 Hz.
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds((s) => s + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Guest result: render the plan inline (no save — signing up is how you keep it).
  if (guestPlan) {
    return (
      <div className="pb-16">
        <div className="rounded-card border border-border bg-elevated p-4">
          <p className="text-body">
            This plan is temporary — it lives only in this tab.{" "}
            <span className="text-text-muted">Sign in to save it and track your skills.</span>
          </p>
          <div className="mt-3">
            <ButtonLink href="/signin">Sign in to save</ButtonLink>
          </div>
        </div>
        <PlanView plan={guestPlan} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[480px]">
      <header className="text-center">
        <h1 className="text-[24px] font-medium leading-[1.15]">
          {failed ? "Something went wrong" : "Crafting your plan"}
        </h1>
        <p className="mt-2 text-body text-text-muted">
          {failed
            ? "We couldn't finish this analysis. Head back and try again."
            : "We're analyzing your details to build your optimal plan."}
        </p>
      </header>

      {!failed && (
        <div className="mt-12">
          <StageList stages={STAGES} currentStage={uiStage} />
        </div>
      )}

      <div className="mt-8 text-center">
        <div className="inline-flex items-center gap-1.5 rounded-pill bg-bg-secondary px-3 py-1 text-caption text-text-muted">
          <Clock className="size-3.5" aria-hidden />
          <span className="font-mono tabular-nums">
            {formatElapsed(elapsedSeconds)}
          </span>
          <span>elapsed</span>
        </div>
        <p className="mt-2 text-caption text-text-muted">
          Usually under 30 seconds.
        </p>
      </div>
    </div>
  );
}

function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${pad(minutes)}:${pad(secs)}`;
}

function pad(n: number): string {
  return n.toString().padStart(2, "0");
}
