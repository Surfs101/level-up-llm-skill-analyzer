import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Spacing = "none" | "sm" | "md" | "lg";

type DividerProps = HTMLAttributes<HTMLDivElement> & {
  spacing?: Spacing;
};

const spacingStyles: Record<Spacing, string> = {
  none: "my-0",
  sm: "my-2",
  md: "my-4",
  lg: "my-8",
};

export default function Divider({
  spacing = "md",
  className,
  ...props
}: DividerProps) {
  return (
    <div
      role="separator"
      className={cn("h-px w-full bg-border", spacingStyles[spacing], className)}
      {...props}
    />
  );
}
