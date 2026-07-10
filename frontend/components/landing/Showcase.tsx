"use client";

import { useRef } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";
import { ArrowRight, Check, GraduationCap, Sparkles, X } from "lucide-react";

import GlowSection from "@/components/landing/GlowSection";
import { ease } from "@/lib/motion";

const COMPOSITE_PCT = 74;
const PREV_COMPOSITE = 62;

const REQ_WEIGHT = 0.8;
const PREF_WEIGHT = 0.2;

type Skill = { name: string; matched: boolean };

const REQUIRED: ReadonlyArray<Skill> = [
  { name: "TypeScript", matched: true },
  { name: "Go", matched: true },
  { name: "Postgres", matched: true },
  { name: "Redis", matched: true },
  { name: "Docker", matched: true },
  { name: "AWS", matched: true },
  { name: "REST APIs", matched: true },
  { name: "SQL", matched: true },
  { name: "Git", matched: true },
  { name: "Linux", matched: true },
  { name: "gRPC", matched: false },
  { name: "Kubernetes", matched: false },
  { name: "Kafka", matched: false },
];

const PREFERRED: ReadonlyArray<Skill> = [
  { name: "GraphQL", matched: true },
  { name: "Terraform", matched: true },
  { name: "RabbitMQ", matched: true },
  { name: "Prometheus", matched: true },
  { name: "OpenAPI", matched: true },
  { name: "Snowflake", matched: false },
  { name: "Helm", matched: false },
  { name: "Vault", matched: false },
];

const REQ_MATCHED = REQUIRED.filter((s) => s.matched).length;
const PREF_MATCHED = PREFERRED.filter((s) => s.matched).length;

const TOP_MISSING: ReadonlyArray<{ name: string; tier: "required" | "preferred"; impact: string }> = [
  { name: "gRPC", tier: "required", impact: "+6%" },
  { name: "Kubernetes", tier: "required", impact: "+6%" },
  { name: "Kafka", tier: "required", impact: "+6%" },
  { name: "Snowflake", tier: "preferred", impact: "+2.5%" },
  { name: "Helm", tier: "preferred", impact: "+2.5%" },
];

const TREND_SERIES = [54, 58, 62, 65, 68, 70, 74] as const;

const VIEWPORT = { once: true, margin: "-80px" } as const;

export default function Showcase() {
  const reduced = useReducedMotion() ?? false;
  const sectionRef = useRef<HTMLDivElement>(null);
  const inView = useInView(sectionRef, VIEWPORT);

  return (
    <section id="product" className="overflow-visible px-6">
      <div
        ref={sectionRef}
        className="mx-auto max-w-[1080px] overflow-visible pb-[120px] pt-20 md:pb-40 md:pt-16"
      >
        <motion.p
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={VIEWPORT}
          transition={{ duration: 0.25, ease: ease.out }}
          className="text-center text-[12px] font-medium uppercase tracking-[0.18em] text-score"
        >
          The product
        </motion.p>

        <motion.h2
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={VIEWPORT}
          transition={{ duration: 0.25, ease: ease.out, delay: 0.05 }}
          className="mt-3 text-center text-[34px] font-semibold leading-[1.15] tracking-[-0.02em] text-text md:text-[44px]"
        >
          A real fit score, not a vague match
        </motion.h2>

        <motion.p
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={VIEWPORT}
          transition={{ duration: 0.25, ease: ease.out, delay: 0.12 }}
          className="mx-auto mt-4 max-w-[580px] text-center text-[15px] leading-[1.65] text-text-muted md:text-[16px]"
        >
          We extract every concrete skill from the role, weight what&apos;s
          required higher than what&apos;s preferred, and tell you exactly
          which gaps move the score.
        </motion.p>

        <motion.div
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={VIEWPORT}
          transition={{ duration: 0.4, ease: ease.out, delay: 0.18 }}
          className="mt-12"
        >
          <GlowSection innerClassName="overflow-hidden p-0">
            <Chrome />

            <div className="grid grid-cols-1 gap-3 p-3 md:grid-cols-3 md:gap-4 md:p-4">
              <CompositeCard inView={inView} reduced={reduced} />
              <MissingCard reduced={reduced} />
              <TrendCard inView={inView} reduced={reduced} />
              <SkillsBreakdownCard reduced={reduced} />
              <NextStepCard reduced={reduced} />
            </div>
          </GlowSection>
        </motion.div>
      </div>
    </section>
  );
}

function Chrome() {
  return (
    <div className="flex items-center gap-2 border-b border-border bg-bg-secondary px-5 py-3">
      <span className="flex gap-1.5">
        <span className="size-2.5 rounded-full bg-[#ff5f57]/80" aria-hidden />
        <span className="size-2.5 rounded-full bg-[#ffbd2e]/80" aria-hidden />
        <span className="size-2.5 rounded-full bg-[#28c840]/80" aria-hidden />
      </span>
      <span className="ml-3 truncate font-mono text-[12px] text-subtle">
        analyze / senior-backend-engineer-stripe.json
      </span>
      <span className="ml-auto hidden items-center gap-3 sm:flex">
        <span className="font-mono text-[11px] tabular-nums text-subtle">
          v3 / 7
        </span>
        <span className="rounded-pill border border-matched-border bg-matched-bg px-2.5 py-0.5 font-mono text-[11px] tabular-nums text-matched-text">
          Strong fit
        </span>
      </span>
    </div>
  );
}

function Cell({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={[
        "rounded-card border border-border bg-bg-secondary p-5",
        className ?? "",
      ].join(" ")}
    >
      {children}
    </div>
  );
}

function CellLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-subtle">
      {children}
    </p>
  );
}

function CompositeCard({
  inView,
  reduced,
}: {
  inView: boolean;
  reduced: boolean;
}) {
  return (
    <Cell className="flex flex-col gap-5 md:col-span-2 md:row-span-2">
      <div className="flex items-start justify-between gap-3">
        <div>
          <CellLabel>Composite score</CellLabel>
          <p className="mt-1 text-[14px] text-text-muted">
            Senior Backend Engineer &middot; Stripe &middot; Remote
          </p>
          <p className="mt-1 font-mono text-[12px] text-subtle">
            resume_2026_v3.pdf &middot; 124 KB &middot; analyzed 2 min ago
          </p>
        </div>
        <span className="rounded-pill border border-matched-border bg-matched-bg px-2.5 py-1 font-mono text-[11px] tabular-nums text-matched-text">
          +12 since Mar 4
        </span>
      </div>

      <div className="flex flex-col items-center gap-6 md:flex-row md:items-center md:gap-8">
        <RadialRing inView={inView} reduced={reduced} />

        <div className="flex-1">
          <p className="text-[15px] leading-[1.65] text-text-muted">
            You hit{" "}
            <span className="font-medium text-text">
              {REQ_MATCHED} of {REQUIRED.length} required skills
            </span>
            . The gap is concentrated in distributed-systems primitives:{" "}
            <span className="font-medium text-text">
              gRPC, Kubernetes, Kafka
            </span>
            .
          </p>

          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className="rounded-pill border border-score/30 bg-score/10 px-2.5 py-1 font-mono text-[11px] text-score">
              Required &times;{REQ_WEIGHT.toFixed(1)}
            </span>
            <span className="rounded-pill border border-border bg-bg-secondary px-2.5 py-1 font-mono text-[11px] text-text-muted">
              Preferred &times;{PREF_WEIGHT.toFixed(1)}
            </span>
            <span className="rounded-pill border border-border bg-bg-secondary px-2.5 py-1 font-mono text-[11px] text-text-muted">
              ~6 weeks to close
            </span>
          </div>
        </div>
      </div>
    </Cell>
  );
}

function RadialRing({
  inView,
  reduced,
}: {
  inView: boolean;
  reduced: boolean;
}) {
  const size = 168;
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const target = c * (1 - COMPOSITE_PCT / 100);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-hidden
      >
        <defs>
          <linearGradient id="ring-grad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#7DD3FC" />
            <stop offset="100%" stopColor="#38BDF8" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#ring-grad)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: reduced ? target : c }}
          animate={
            reduced || inView
              ? { strokeDashoffset: target }
              : { strokeDashoffset: c }
          }
          transition={{ duration: 1.2, ease: ease.inOut, delay: 0.2 }}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ filter: "drop-shadow(0 0 12px rgba(56,189,248,0.45))" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-mono text-[44px] font-semibold leading-none tracking-tight text-score [text-shadow:0_0_24px_var(--score-glow)]">
          {COMPOSITE_PCT}%
        </span>
        <span className="mt-1.5 text-[11px] uppercase tracking-[0.16em] text-subtle">
          fit
        </span>
      </div>
    </div>
  );
}

function MissingCard({ reduced }: { reduced: boolean }) {
  return (
    <Cell>
      <div className="flex items-start justify-between gap-3">
        <CellLabel>Top-impact gaps</CellLabel>
        <span className="font-mono text-[11px] tabular-nums text-text-muted">
          {TOP_MISSING.length}
        </span>
      </div>

      <ul className="mt-4 space-y-2">
        {TOP_MISSING.map((s, i) => (
          <motion.li
            key={s.name}
            initial={reduced ? { opacity: 0 } : { opacity: 0, x: -6 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={VIEWPORT}
            transition={{
              duration: 0.3,
              ease: ease.out,
              delay: reduced ? 0 : 0.25 + i * 0.06,
            }}
            className="flex items-center justify-between gap-3"
          >
            <span className="flex min-w-0 items-center gap-2">
              <span
                className={[
                  "shrink-0 rounded-pill border px-1.5 py-0 font-mono text-[9px] uppercase tracking-[0.12em]",
                  s.tier === "required"
                    ? "border-score/40 bg-score/10 text-score"
                    : "border-border bg-bg text-subtle",
                ].join(" ")}
              >
                {s.tier === "required" ? "Req" : "Pref"}
              </span>
              <span className="truncate text-[13px] text-text">{s.name}</span>
            </span>
            <span className="font-mono text-[11px] tabular-nums text-text-muted">
              {s.impact}
            </span>
          </motion.li>
        ))}
      </ul>
    </Cell>
  );
}

function TrendCard({
  inView,
  reduced,
}: {
  inView: boolean;
  reduced: boolean;
}) {
  const W = 220;
  const H = 60;
  const max = Math.max(...TREND_SERIES);
  const min = Math.min(...TREND_SERIES);
  const range = max - min || 1;
  const stepX = W / (TREND_SERIES.length - 1);

  const points = TREND_SERIES.map((v, i) => {
    const x = i * stepX;
    const y = H - ((v - min) / range) * (H - 8) - 4;
    return [x, y] as const;
  });

  const path = points
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`)
    .join(" ");

  const lastX = points[points.length - 1][0];
  const lastY = points[points.length - 1][1];

  return (
    <Cell>
      <div className="flex items-start justify-between gap-3">
        <CellLabel>Score trend</CellLabel>
        <span className="font-mono text-[11px] tabular-nums text-text-muted">
          7 versions
        </span>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="font-mono text-[24px] font-semibold leading-none tabular-nums text-text">
          {PREV_COMPOSITE}
          <span className="text-subtle">{" → "}</span>
          {COMPOSITE_PCT}
        </span>
        <span className="rounded-pill border border-matched-border bg-matched-bg px-2 py-0.5 font-mono text-[10px] tabular-nums text-matched-text">
          +12
        </span>
      </div>
      <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.16em] text-subtle">
        Feb 12 &middot; Mar 4 &middot; today
      </p>

      <svg
        width="100%"
        viewBox={`0 0 ${W} ${H}`}
        className="mt-3 h-[56px] w-full"
        preserveAspectRatio="none"
        aria-hidden
      >
        <defs>
          <linearGradient id="spark-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(56,189,248,0.35)" />
            <stop offset="100%" stopColor="rgba(56,189,248,0)" />
          </linearGradient>
        </defs>
        <motion.path
          d={`${path} L ${W} ${H} L 0 ${H} Z`}
          fill="url(#spark-fill)"
          initial={{ opacity: reduced ? 1 : 0 }}
          animate={reduced || inView ? { opacity: 1 } : { opacity: 0 }}
          transition={{ duration: 0.6, delay: 0.7 }}
        />
        <motion.path
          d={path}
          fill="none"
          stroke="#38BDF8"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: reduced ? 1 : 0 }}
          animate={reduced || inView ? { pathLength: 1 } : { pathLength: 0 }}
          transition={{ duration: 1.1, ease: ease.inOut, delay: 0.3 }}
          style={{ filter: "drop-shadow(0 0 6px rgba(56,189,248,0.6))" }}
        />
        <motion.circle
          cx={lastX}
          cy={lastY}
          r={3.5}
          fill="#38BDF8"
          initial={{ scale: reduced ? 1 : 0 }}
          animate={reduced || inView ? { scale: 1 } : { scale: 0 }}
          transition={{ duration: 0.3, delay: 1.4 }}
          style={{ filter: "drop-shadow(0 0 6px rgba(56,189,248,0.8))" }}
        />
      </svg>
    </Cell>
  );
}

function SkillsBreakdownCard({ reduced }: { reduced: boolean }) {
  return (
    <Cell className="md:col-span-2">
      <div className="flex items-start justify-between gap-3">
        <CellLabel>Skills extracted</CellLabel>
        <span className="font-mono text-[11px] tabular-nums text-text-muted">
          {REQUIRED.length + PREFERRED.length} total
        </span>
      </div>

      <div className="mt-4">
        <SkillTierHeader
          tier="required"
          weight={REQ_WEIGHT}
          matched={REQ_MATCHED}
          total={REQUIRED.length}
        />
        <SkillChipRow skills={REQUIRED} reduced={reduced} delayBase={0.3} />
      </div>

      <div className="mt-5 border-t border-border pt-5">
        <SkillTierHeader
          tier="preferred"
          weight={PREF_WEIGHT}
          matched={PREF_MATCHED}
          total={PREFERRED.length}
        />
        <SkillChipRow skills={PREFERRED} reduced={reduced} delayBase={0.5} />
      </div>
    </Cell>
  );
}

function SkillTierHeader({
  tier,
  weight,
  matched,
  total,
}: {
  tier: "required" | "preferred";
  weight: number;
  matched: number;
  total: number;
}) {
  const pct = Math.round((matched / total) * 100);
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <span
          className={
            tier === "required"
              ? "rounded-pill border border-score/40 bg-score/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-score"
              : "rounded-pill border border-border bg-bg px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted"
          }
        >
          {tier === "required" ? "Required" : "Preferred"}
        </span>
        <span className="font-mono text-[11px] tabular-nums text-subtle">
          weight &times;{weight.toFixed(1)}
        </span>
      </div>
      <span className="font-mono text-[11px] tabular-nums text-text-muted">
        {matched} / {total}{" "}
        <span className="text-subtle">&middot; {pct}%</span>
      </span>
    </div>
  );
}

function SkillChipRow({
  skills,
  reduced,
  delayBase,
}: {
  skills: ReadonlyArray<Skill>;
  reduced: boolean;
  delayBase: number;
}) {
  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {skills.map((s, i) => (
        <motion.span
          key={s.name}
          initial={reduced ? { opacity: 0 } : { opacity: 0, y: 4 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={VIEWPORT}
          transition={{
            duration: 0.25,
            ease: ease.out,
            delay: reduced ? 0 : delayBase + i * 0.025,
          }}
          className={[
            "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 font-mono text-[11px]",
            s.matched
              ? "border-matched-border bg-matched-bg text-matched-text"
              : "border-missing-border bg-missing-bg text-missing-text",
          ].join(" ")}
        >
          {s.matched ? (
            <Check className="size-2.5 stroke-[3]" aria-hidden />
          ) : (
            <X className="size-2.5 stroke-[3]" aria-hidden />
          )}
          {s.name}
        </motion.span>
      ))}
    </div>
  );
}

function NextStepCard({ reduced }: { reduced: boolean }) {
  return (
    <Cell className="flex flex-col justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <span className="grid size-7 place-items-center rounded-md border border-plan/30 bg-plan/10">
            <Sparkles className="size-3.5 text-plan" aria-hidden />
          </span>
          <CellLabel>Next step</CellLabel>
        </div>
        <p className="mt-3 text-[15px] leading-[1.6] text-text">
          Start <span className="font-medium">gRPC + Distributed Systems</span>.
          Closes a required skill, biggest move on your composite.
        </p>
        <p className="mt-2 font-mono text-[11px] text-subtle">
          ~14 hrs &middot; +6% projected
        </p>
      </div>

      <motion.div
        whileHover={reduced ? undefined : { x: 3 }}
        transition={{ duration: 0.18, ease: "linear" }}
        className="flex items-center justify-between gap-3 rounded-md border border-border bg-bg-secondary px-3 py-2"
      >
        <span className="flex items-center gap-2">
          <GraduationCap className="size-4 text-text-muted" aria-hidden />
          <span className="text-[13px] text-text">Open course plan</span>
        </span>
        <ArrowRight className="size-4 text-text-muted" aria-hidden />
      </motion.div>
    </Cell>
  );
}
