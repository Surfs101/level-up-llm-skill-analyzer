"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

import Wordmark from "@/components/landing/Wordmark";
import { ease } from "@/lib/motion";
import { cn } from "@/lib/utils";

const TABS = [
  { label: "Analyze", href: "/analyze", matchPrefixes: ["/analyze", "/running"] },
  { label: "Dashboard", href: "/dashboard", matchPrefixes: ["/dashboard"] },
  { label: "Saved Plans", href: "/saved", matchPrefixes: ["/saved", "/plans"] },
  { label: "Job Matches", href: "/jobs", matchPrefixes: ["/jobs"] },
];

const UNDERLINE_TRANSITION = {
  duration: 0.24,
  ease: ease.drawer, // [0.32, 0.72, 0, 1]
};

export default function AppNav() {
  const pathname = usePathname();

  return (
    <header
      className={cn(
        "sticky top-0 z-40 h-14 border-b border-border backdrop-blur-md",
        "bg-[color-mix(in_srgb,var(--bg)_60%,transparent)]",
      )}
    >
      <div className="mx-auto flex h-full max-w-[1180px] items-center justify-between px-6">
        <Link
          href="/"
          className="rounded-btn outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
        >
          <Wordmark />
        </Link>

        <nav className="flex h-full items-stretch">
          {TABS.map((tab) => {
            const isActive = tab.matchPrefixes.some((prefix) =>
              pathname === prefix || pathname.startsWith(`${prefix}/`),
            );
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  "relative inline-flex items-center px-3 text-body",
                  "outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
                  "transition-colors duration-[140ms] ease-out",
                  isActive ? "text-text" : "text-text-muted hover:text-text",
                )}
              >
                {tab.label}
                {isActive && (
                  <motion.div
                    layoutId="active-tab-underline"
                    className="absolute inset-x-0 -bottom-px h-[2px] bg-accent"
                    transition={UNDERLINE_TRANSITION}
                  />
                )}
              </Link>
            );
          })}
        </nav>

        <AvatarMenu />
      </div>
    </header>
  );
}

function AvatarMenu() {
  const reduced = useReducedMotion() ?? false;
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handleClickOutside(event: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  return (
    <div ref={wrapperRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-pill p-0.5 pr-2",
          "outline-none focus-visible:ring-2 focus-visible:ring-accent/40",
          "transition-colors duration-[140ms] ease-out hover:bg-bg-secondary",
        )}
      >
        <span className="inline-flex size-8 items-center justify-center rounded-full bg-bg-secondary text-caption font-medium text-text-muted">
          M
        </span>
        <ChevronDown
          className={cn(
            "size-3.5 text-text-muted",
            !reduced && "transition-transform duration-[140ms] ease-out",
            !reduced && open && "rotate-180",
          )}
          aria-hidden
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: -4 }}
            animate={reduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: -4 }}
            transition={{ duration: 0.14, ease: ease.out }}
            role="menu"
            className="absolute right-0 top-full mt-2 min-w-[160px] rounded-card border border-border bg-elevated p-1"
          >
            <Link
              href="/signin"
              role="menuitem"
              onClick={() => setOpen(false)}
              className={cn(
                "block rounded-[6px] px-3 py-2 text-body text-text",
                "transition-colors duration-[140ms] ease-out hover:bg-bg-secondary",
              )}
            >
              Sign out
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
