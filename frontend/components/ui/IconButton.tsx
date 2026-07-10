"use client";

import { forwardRef, type ReactNode } from "react";
import { motion, type HTMLMotionProps } from "motion/react";
import { cn } from "@/lib/utils";

type IconButtonProps = Omit<HTMLMotionProps<"button">, "children"> & {
  icon: ReactNode;
  "aria-label": string;
};

const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton({ icon, className, disabled, ...props }, ref) {
    return (
      <motion.button
        ref={ref}
        whileTap={disabled ? undefined : { scale: 0.94 }}
        transition={{ duration: 0.1, ease: "linear" }}
        disabled={disabled}
        className={cn(
          "inline-flex size-8 shrink-0 items-center justify-center rounded-full",
          "text-text-muted transition-colors duration-[140ms] ease-out",
          "hover:bg-bg-secondary hover:text-text",
          "outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "[&>svg]:size-[18px]",
          className,
        )}
        {...props}
      >
        {icon}
      </motion.button>
    );
  },
);

export default IconButton;
