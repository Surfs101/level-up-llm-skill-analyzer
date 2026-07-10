"use client";

import { useEffect, useState } from "react";
import { Clock } from "lucide-react";

import SkillCategorySection, {
  type DashboardSkill,
} from "@/components/app/SkillCategorySection";
import { fetchDashboard, type DashboardResponse } from "@/lib/api/dashboard";
import { formatDate } from "@/lib/format";
import { SKILL_CATEGORIES, getSkillById } from "@/lib/mock-data/skills";

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);

  useEffect(() => {
    fetchDashboard()
      .then(setDashboard)
      .catch(() => setDashboard(null));
  }, []);

  if (!dashboard) return null;

  return (
    <div>
      <header>
        <h1 className="text-h3">Your skill profile</h1>
        <p className="mt-2 inline-flex items-center gap-1.5 text-[14px] text-text-muted">
          <Clock className="size-3.5" aria-hidden />
          <LastUpdated dashboard={dashboard} />
        </p>
      </header>

      <div className="mt-8 space-y-4">
        {SKILL_CATEGORIES.map((category) => {
          const ids = dashboard.skills_by_category[category] ?? [];
          const initialSkills: DashboardSkill[] = ids.map((id) => {
            const skill = getSkillById(id);
            return { id, name: skill?.canonical_name ?? id };
          });
          return (
            <SkillCategorySection
              key={category}
              category={category}
              initialSkills={initialSkills}
            />
          );
        })}
      </div>
    </div>
  );
}

function LastUpdated({ dashboard }: { dashboard: DashboardResponse }) {
  if (dashboard.last_updated_from && dashboard.last_updated_at) {
    return (
      <>
        Last updated from {dashboard.last_updated_from} on{" "}
        {formatDate(dashboard.last_updated_at)}
      </>
    );
  }
  if (dashboard.last_updated_at) {
    return <>Last updated on {formatDate(dashboard.last_updated_at)}</>;
  }
  return <>No skills yet</>;
}
