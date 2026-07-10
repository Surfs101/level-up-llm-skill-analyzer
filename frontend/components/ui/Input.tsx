import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type InputProps = InputHTMLAttributes<HTMLInputElement>;

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-btn border border-border bg-transparent px-3 text-[14px] text-text",
        "transition-colors duration-[160ms] ease-out",
        "outline-none focus:border-strong focus:ring-2 focus:ring-accent-glow",
        "placeholder:text-text-muted/70",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
});

export default Input;
