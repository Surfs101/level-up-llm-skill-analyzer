import Link from "next/link";

import Wordmark from "@/components/landing/Wordmark";

const COLUMNS = [
  {
    heading: "Product",
    links: [
      { label: "How it works", href: "/#how-it-works" },
      { label: "Pricing", href: "/pricing" },
      { label: "Try the analysis", href: "/analyze" },
      { label: "Find jobs", href: "/signin" },
    ],
  },
  {
    heading: "Resources",
    links: [
      { label: "Skills library", href: "/resources/skills" },
      { label: "Courses", href: "/resources/courses" },
      { label: "FAQ", href: "/#faq" },
    ],
  },
  {
    heading: "Company",
    links: [
      { label: "About", href: "/about" },
      { label: "Contact", href: "/contact" },
    ],
  },
  {
    heading: "Legal",
    links: [
      { label: "Privacy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
    ],
  },
] as const;

export default function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto max-w-[1200px] px-8 pb-10 pt-16">
        <div className="grid gap-12 md:grid-cols-[1.4fr_repeat(4,minmax(0,1fr))] md:gap-10">
          <div className="max-w-[280px]">
            <Link
              href="/"
              className="inline-flex w-fit rounded-btn outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
            >
              <Wordmark />
            </Link>
            <p className="mt-4 text-[14px] leading-[1.7] text-text-muted">
              Bridge the gap between your skills and the role you want.
              Score fit, find gaps, build a plan.
            </p>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.heading}>
              <h3 className="text-[12px] font-medium uppercase tracking-[0.14em] text-text-muted">
                {col.heading}
              </h3>
              <ul className="mt-4 space-y-3">
                {col.links.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-[14px] text-text-muted transition-colors duration-[140ms] ease-out hover:text-text"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-14 flex flex-col gap-3 border-t border-border pt-6 md:flex-row md:items-center md:justify-between">
          <p className="text-[13px] text-text-muted">
            &copy; 2026 SkillBridge. All rights reserved.
          </p>
          <p className="font-mono text-[12px] uppercase tracking-[0.16em] text-text-muted">
            Made for people who want the role
          </p>
        </div>
      </div>
    </footer>
  );
}
