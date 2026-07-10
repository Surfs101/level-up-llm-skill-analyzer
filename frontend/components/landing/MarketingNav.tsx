"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ButtonLink } from "@/components/ui";
import Wordmark from "@/components/landing/Wordmark";
import { cn } from "@/lib/utils";

const CENTER_LINKS = [
  { label: "How it works", href: "/#how-it-works" },
  { label: "Pricing", href: "/pricing" },
  { label: "Sign in", href: "/signin" },
];

export default function MarketingNav() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 8);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-40 h-16 backdrop-blur-lg",
        "bg-[color-mix(in_srgb,var(--bg)_70%,transparent)]",
        "border-b transition-colors duration-[140ms] ease-out",
        scrolled ? "border-border" : "border-transparent",
      )}
    >
      <div className="mx-auto flex h-full max-w-[1200px] items-center justify-between px-8">
        <Link
          href="/"
          className="rounded-btn outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
        >
          <Wordmark />
        </Link>

        <nav className="hidden items-center gap-7 md:flex">
          <Link
            href="/#product"
            className="text-[14px] text-text-muted transition-colors duration-[140ms] ease-out hover:text-text"
          >
            Product
          </Link>
          {CENTER_LINKS.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-[14px] text-text-muted transition-colors duration-[140ms] ease-out hover:text-text"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="hidden items-center gap-1 rounded-md border border-border bg-bg-secondary px-2 py-1 font-mono text-[11px] text-text-muted lg:inline-flex"
          >
            <kbd className="font-sans">&#8984;</kbd>
            <kbd className="font-sans">K</kbd>
          </span>
          <ButtonLink href="/analyze" size="sm">
            Try the analysis
          </ButtonLink>
        </div>
      </div>
    </header>
  );
}
