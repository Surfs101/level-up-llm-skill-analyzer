import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "interactive";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  variant?: Variant;
  compact?: boolean;
};

const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { variant = "default", compact = false, className, children, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn(
        "rounded-card border border-border bg-bg-secondary",
        compact ? "p-4" : "p-6",
        variant === "interactive" &&
          "cursor-pointer transition-colors duration-[180ms] ease-out hover:bg-elevated-hi hover:border-text-muted/20",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
});

export default Card;
