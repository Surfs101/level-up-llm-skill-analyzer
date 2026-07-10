"use client";

import { forwardRef, type ReactNode } from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

type ButtonProps = Omit<HTMLMotionProps<"button">, "children"> & {
  variant?: Variant;
  size?: Size;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  loading?: boolean;
  children?: ReactNode;
};

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-accent text-on-accent " +
    "shadow-[0_0_18px_var(--accent-glow-soft),0_2px_8px_color-mix(in_srgb,var(--accent)_24%,transparent)] " +
    "hover:bg-accent-hover " +
    "hover:shadow-[0_0_24px_var(--accent-glow),0_4px_14px_color-mix(in_srgb,var(--accent)_36%,transparent)]",
  secondary:
    "border border-border bg-transparent text-text hover:bg-bg-secondary",
  ghost: "bg-transparent text-text-muted hover:text-text",
};

const sizeStyles: Record<Size, string> = {
  sm: "h-8 px-3 text-caption gap-1.5",
  md: "h-10 px-4 text-body gap-2",
  lg: "h-12 px-6 text-body gap-2",
};

const iconClass: Record<Size, string> = {
  sm: "size-3.5",
  md: "size-4",
  lg: "size-[18px]",
};

const iconWrapperClass: Record<Size, string> = {
  sm: "[&>svg]:size-3.5",
  md: "[&>svg]:size-4",
  lg: "[&>svg]:size-[18px]",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    leftIcon,
    rightIcon,
    loading = false,
    disabled,
    className,
    children,
    ...props
  },
  ref,
) {
  const isDisabled = disabled || loading;

  return (
    <motion.button
      ref={ref}
      whileTap={isDisabled ? undefined : { scale: 0.97 }}
      transition={{ duration: 0.1, ease: "linear" }}
      disabled={isDisabled}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-btn font-medium",
        "transition-[color,background-color,border-color,box-shadow] duration-[220ms] ease-out",
        "outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      {...props}
    >
      {loading ? (
        <Loader2 className={cn("animate-spin", iconClass[size])} aria-hidden />
      ) : leftIcon ? (
        <span
          className={cn(
            "inline-flex shrink-0 items-center",
            iconWrapperClass[size],
          )}
        >
          {leftIcon}
        </span>
      ) : null}
      {children}
      {!loading && rightIcon ? (
        <span
          className={cn(
            "inline-flex shrink-0 items-center",
            iconWrapperClass[size],
          )}
        >
          {rightIcon}
        </span>
      ) : null}
    </motion.button>
  );
});

export default Button;
