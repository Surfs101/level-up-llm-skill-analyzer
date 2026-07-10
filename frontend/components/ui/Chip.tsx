import { forwardRef, type HTMLAttributes, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

type Variant =
  | "matched"
  | "missing"
  | "score"
  | "premium"
  | "neutral"
  | "removable";

type ChipProps = Omit<HTMLAttributes<HTMLSpanElement>, "onRemove"> & {
  variant?: Variant;
  icon?: ReactNode;
  onRemove?: () => void;
};

const variantStyles: Record<Variant, string> = {
  matched: "bg-matched-bg text-matched-text border-matched-border",
  missing: "bg-missing-bg text-missing-text border-missing-border",
  score: "bg-score-bg text-score border-score-border",
  premium: "bg-premium-bg text-premium border-premium-border",
  neutral: "bg-transparent text-text border-border",
  removable: "bg-transparent text-text border-border",
};

const Chip = forwardRef<HTMLSpanElement, ChipProps>(function Chip(
  { variant = "neutral", icon, onRemove, children, className, ...props },
  ref,
) {
  const showRemoveButton = variant === "removable";

  return (
    <span
      ref={ref}
      className={cn(
        "inline-flex h-[26px] items-center gap-1.5 rounded-pill border px-[10px] text-caption font-normal",
        showRemoveButton && "group/chip",
        variantStyles[variant],
        className,
      )}
      {...props}
    >
      {icon ? (
        <span className="inline-flex shrink-0 items-center [&>svg]:size-3.5">
          {icon}
        </span>
      ) : null}
      <span>{children}</span>
      {showRemoveButton ? (
        <button
          type="button"
          onClick={onRemove}
          aria-label="Remove"
          className={cn(
            "-mr-0.5 inline-flex shrink-0 items-center text-text-muted",
            "opacity-0 transition-opacity duration-[140ms] ease-out",
            "hover:text-text",
            "group-hover/chip:opacity-100 focus-visible:opacity-100",
            "outline-none",
          )}
        >
          <X className="size-3" />
        </button>
      ) : null}
    </span>
  );
});

export default Chip;
