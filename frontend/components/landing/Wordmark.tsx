import { cn } from "@/lib/utils";

type WordmarkProps = {
  className?: string;
  textClassName?: string;
};

export default function Wordmark({ className, textClassName }: WordmarkProps) {
  return (
    <div className={cn("inline-flex items-center gap-2.5", className)}>
      <span className="grid size-7 place-items-center rounded-md bg-score shadow-[0_0_12px_var(--score-glow-soft)]">
        <BridgeMark />
      </span>
      <span
        className={cn(
          "text-[18px] font-medium tracking-tight text-text",
          textClassName,
        )}
      >
        SkillBridge
      </span>
      <span
        aria-label="Version 2"
        className="ml-0.5 inline-flex items-center rounded-md border border-score/30 bg-score/10 px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.12em] text-score"
      >
        v2
      </span>
    </div>
  );
}

function BridgeMark() {
  return (
    <svg
      width="20"
      height="14"
      viewBox="0 0 20 14"
      fill="none"
      stroke="white"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.2"
      aria-hidden
    >
      {/* Deck */}
      <line x1="1" y1="11" x2="19" y2="11" />
      {/* Pylons */}
      <line x1="5" y1="3" x2="5" y2="11" />
      <line x1="15" y1="3" x2="15" y2="11" />
      {/* Suspension cable */}
      <path d="M5 3 Q10 9.5 15 3" />
      {/* Back-stays */}
      <line x1="1" y1="11" x2="5" y2="3" strokeOpacity="0.7" />
      <line x1="19" y1="11" x2="15" y2="3" strokeOpacity="0.7" />
      {/* Suspender hangers */}
      <line x1="8" y1="6.6" x2="8" y2="11" strokeOpacity="0.55" strokeWidth="0.9" />
      <line x1="10" y1="7.4" x2="10" y2="11" strokeOpacity="0.55" strokeWidth="0.9" />
      <line x1="12" y1="6.6" x2="12" y2="11" strokeOpacity="0.55" strokeWidth="0.9" />
    </svg>
  );
}
