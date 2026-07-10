import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ className, ...props }, ref) {
    return (
      <textarea
        ref={ref}
        className={cn(
          "min-h-[160px] w-full resize-y rounded-btn border border-border bg-transparent px-4 pt-4 pb-[14px] text-[14px] text-text",
          "transition-colors duration-[160ms] ease-out",
          "outline-none focus:border-strong focus:ring-2 focus:ring-accent-glow",
          "placeholder:text-text-muted/70",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      />
    );
  },
);

export default Textarea;
