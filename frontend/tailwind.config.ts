import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  future: {
    // Makes `hover:` only apply under @media (hover: hover) and (pointer: fine).
    hoverOnlyWhenSupported: true,
  },
  theme: {
    // Restrict to the only two weights the design system uses.
    fontWeight: {
      normal: "400",
      medium: "500",
      semibold: "600",
      bold: "700",
    },
    extend: {
      colors: {
        bg: "var(--bg)",
        "bg-secondary": "var(--bg-secondary)",
        elevated: "var(--bg-elevated)",
        text: "var(--text)",
        "text-muted": "var(--text-muted)",
        subtle: "var(--text-subtle)",
        border: "var(--border)",
        strong: "var(--border-strong)",
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-glow": "var(--accent-glow)",
        "accent-glow-soft": "var(--accent-glow-soft)",
        "on-accent": "var(--on-accent)",
        "accent-2": "var(--accent-2)",
        "accent-purple": "var(--accent-purple)",
        "elevated-hi": "var(--bg-elevated-hi)",
        warning: "var(--warning)",
        "warning-bg": "var(--warning-bg)",
        "warning-text": "var(--warning-text)",
        "warning-border": "var(--warning-border)",
        score: "var(--score)",
        "score-soft": "var(--score-soft)",
        "score-bg": "var(--score-bg)",
        "score-border": "var(--score-border)",
        plan: "var(--plan)",
        premium: "var(--premium)",
        "premium-bg": "var(--premium-bg)",
        "premium-border": "var(--premium-border)",
        decor: "var(--decor)",
        critical: "var(--critical-text)",
        "critical-bg": "var(--critical-bg)",
        "critical-border": "var(--critical-border)",
        "matched-bg": "var(--matched-bg)",
        "matched-text": "var(--matched-text)",
        "matched-border": "var(--matched-border)",
        "matched-glow": "var(--matched-glow)",
        "missing-bg": "var(--missing-bg)",
        "missing-text": "var(--missing-text)",
        "missing-border": "var(--missing-border)",
        "missing-glow": "var(--missing-glow)",
      },
      boxShadow: {
        glow: "0 0 24px var(--accent-glow)",
        "glow-soft": "0 0 24px var(--accent-glow-soft)",
        "glow-strong": "0 0 48px var(--accent-glow)",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-geist-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        h1: ["56px", { lineHeight: "1.15", fontWeight: "500" }],
        h2: ["40px", { lineHeight: "1.15", fontWeight: "500" }],
        h3: ["28px", { lineHeight: "1.15", fontWeight: "500" }],
        h4: ["22px", { lineHeight: "1.15", fontWeight: "500" }],
        h5: ["18px", { lineHeight: "1.15", fontWeight: "500" }],
        body: ["16px", { lineHeight: "1.6", fontWeight: "400" }],
        caption: ["13px", { lineHeight: "1.6", fontWeight: "400" }],
      },
      borderRadius: {
        btn: "8px",
        card: "12px",
        panel: "16px",
        pill: "9999px",
      },
    },
  },
  plugins: [],
};

export default config;
