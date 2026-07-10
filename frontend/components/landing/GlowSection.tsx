import { cn } from "@/lib/utils";

const PANEL_STYLE: React.CSSProperties = {
  zIndex: 1,
  backgroundImage:
    "linear-gradient(180deg, var(--accent-tint-4) 0%, transparent 50%)",
  backgroundColor: "var(--bg-elevated)",
  borderColor: "var(--accent-border-15)",
};

type GlowSectionProps = {
  className?: string;
  innerClassName?: string;
  children: React.ReactNode;
};

export default function GlowSection({
  className,
  innerClassName,
  children,
}: GlowSectionProps) {
  return (
    <div className={cn("relative isolate", className)}>
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute -inset-8 rounded-[32px]",
          "[filter:blur(60px)]",
        )}
        style={{
          zIndex: 0,
          opacity: 1,
          background:
            "radial-gradient(ellipse at center, var(--accent-radial-65) 0%, transparent 65%)",
        }}
      />
      <div
        className={cn("relative rounded-panel border", innerClassName)}
        style={PANEL_STYLE}
      >
        {children}
      </div>
    </div>
  );
}
