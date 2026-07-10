"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary";
type Size = "sm" | "md" | "lg";

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-accent text-on-accent " +
    "shadow-[0_0_24px_var(--accent-glow-soft),0_4px_12px_color-mix(in_srgb,var(--accent)_20%,transparent)] " +
    "hover:bg-accent-hover " +
    "hover:shadow-[0_0_32px_var(--accent-glow),0_6px_20px_color-mix(in_srgb,var(--accent)_35%,transparent)]",
  secondary:
    "border border-strong bg-transparent text-text hover:bg-bg-secondary",
};

const sizeStyles: Record<Size, string> = {
  sm: "h-8 px-3 text-caption gap-1.5",
  md: "h-10 px-4 text-body gap-2",
  lg: "h-12 px-6 text-body gap-2",
};

const iconWrapperBySize: Record<Size, string> = {
  sm: "[&>svg]:size-3.5",
  md: "[&>svg]:size-4",
  lg: "[&>svg]:size-[18px]",
};

type ButtonLinkProps = {
  href: string;
  variant?: Variant;
  size?: Size;
  rightIcon?: ReactNode;
  leftIcon?: ReactNode;
  children: ReactNode;
  className?: string;
};

export default function ButtonLink({
  href,
  variant = "primary",
  size = "md",
  rightIcon,
  leftIcon,
  children,
  className,
}: ButtonLinkProps) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-block rounded-btn outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
        className,
      )}
    >
      <motion.span
        whileTap={{ scale: 0.97 }}
        transition={{ duration: 0.1, ease: "linear" }}
        className={cn(
          "inline-flex items-center justify-center rounded-btn font-medium",
          "transition-[color,background-color,border-color,box-shadow] duration-[220ms] ease-out",
          variantStyles[variant],
          sizeStyles[size],
          iconWrapperBySize[size],
        )}
      >
        {leftIcon}
        {children}
        {rightIcon}
      </motion.span>
    </Link>
  );
}
