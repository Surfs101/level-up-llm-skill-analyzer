"use client";

import { useEffect, useRef } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  useTransform,
} from "motion/react";

import { ButtonLink } from "@/components/ui";
import HeroBridge from "@/components/landing/HeroBridge";
import HeroDocs from "@/components/landing/HeroDocs";
import { ease } from "@/lib/motion";

const HEADLINE = ["Close", "the", "gap", "between", "you", "and", "the", "role"];
const TRACED_WORD_INDEX = 2;

export default function Hero() {
  const reduced = useReducedMotion() ?? false;
  const stageRef = useRef<HTMLDivElement>(null);

  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const smoothX = useSpring(mouseX, { stiffness: 60, damping: 20, mass: 0.6 });
  const smoothY = useSpring(mouseY, { stiffness: 60, damping: 20, mass: 0.6 });

  const orb1X = useTransform(smoothX, (v) => v * 24);
  const orb1Y = useTransform(smoothY, (v) => v * 24);
  const orb2X = useTransform(smoothX, (v) => v * -32);
  const orb2Y = useTransform(smoothY, (v) => v * -18);
  const meshShiftX = useTransform(smoothX, (v) => v * -6);
  const meshShiftY = useTransform(smoothY, (v) => v * -6);

  useEffect(() => {
    if (reduced) return;
    const node = stageRef.current;
    if (!node) return;

    function onMove(e: MouseEvent) {
      const rect = node!.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      mouseX.set((e.clientX - cx) / rect.width);
      mouseY.set((e.clientY - cy) / rect.height);
    }
    function onLeave() {
      mouseX.set(0);
      mouseY.set(0);
    }

    window.addEventListener("mousemove", onMove);
    node.addEventListener("mouseleave", onLeave);
    return () => {
      window.removeEventListener("mousemove", onMove);
      node.removeEventListener("mouseleave", onLeave);
    };
  }, [mouseX, mouseY, reduced]);

  function fade(delay: number) {
    return {
      initial: reduced ? { opacity: 0 } : { opacity: 0, y: 8 },
      animate: { opacity: 1, y: 0 },
      transition: { duration: 0.4, ease: ease.out, delay: reduced ? 0 : delay },
    };
  }

  return (
    <section ref={stageRef} className="relative overflow-hidden px-6">
      <motion.div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-20"
        style={{
          x: meshShiftX,
          y: meshShiftY,
          backgroundImage:
            "linear-gradient(to right, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px), linear-gradient(to bottom, color-mix(in srgb, var(--accent) 4%, transparent) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          maskImage:
            "radial-gradient(ellipse 60% 50% at 50% 35%, #000 25%, transparent 70%)",
          WebkitMaskImage:
            "radial-gradient(ellipse 60% 50% at 50% 35%, #000 25%, transparent 70%)",
        }}
      />

      <motion.div
        aria-hidden
        className="pointer-events-none absolute -left-32 top-10 -z-10 h-[420px] w-[420px] rounded-full"
        style={{
          x: orb1X,
          y: orb1Y,
          background:
            "radial-gradient(circle, rgba(45,212,191,0.18) 0%, transparent 65%)",
          filter: "blur(80px)",
        }}
        animate={reduced ? undefined : { scale: [1, 1.06, 1] }}
        transition={
          reduced
            ? undefined
            : { duration: 11, repeat: Infinity, ease: "easeInOut" }
        }
      />
      <motion.div
        aria-hidden
        className="pointer-events-none absolute -right-24 top-1/3 -z-10 h-[460px] w-[460px] rounded-full"
        style={{
          x: orb2X,
          y: orb2Y,
          background:
            "radial-gradient(circle, rgba(96,165,250,0.14) 0%, transparent 70%)",
          filter: "blur(90px)",
        }}
        animate={reduced ? undefined : { scale: [1, 1.08, 1] }}
        transition={
          reduced
            ? undefined
            : { duration: 13, repeat: Infinity, ease: "easeInOut", delay: 1.5 }
        }
      />

      <HeroBridge />

      <motion.span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 -z-10 h-px"
        style={{
          background:
            "linear-gradient(90deg, transparent, color-mix(in srgb, var(--accent) 50%, transparent), transparent)",
        }}
      />

      <div className="relative mx-auto max-w-[860px] pb-8 pt-20 text-center md:pb-10 md:pt-[120px]">
        <motion.div {...fade(0.05)} className="mb-7 flex justify-center">
          <span className="group relative inline-flex items-center gap-2 overflow-hidden rounded-pill border border-score/30 bg-score/10 px-3 py-1 text-[12px] font-medium tracking-wide text-text">
            <span
              aria-hidden
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  "linear-gradient(90deg, transparent, color-mix(in srgb, var(--score) 22%, transparent), transparent)",
                animation: reduced ? "none" : "hero-shimmer 4s linear infinite",
              }}
            />
            <Sparkles className="relative size-3.5 text-score" aria-hidden />
            <span className="relative">Skill scoring, not keyword matching</span>
          </span>
        </motion.div>

        <h1
          aria-label={HEADLINE.join(" ")}
          className="mx-auto max-w-[860px] text-[44px] font-semibold leading-[1.04] tracking-[-0.028em] text-text md:text-[72px]"
        >
          {HEADLINE.map((word, i) => (
            <motion.span
              key={`${word}-${i}`}
              aria-hidden
              initial={
                reduced
                  ? { opacity: 0 }
                  : { opacity: 0, y: 14, filter: "blur(6px)" }
              }
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{
                duration: 0.5,
                ease: ease.out,
                delay: reduced ? 0 : 0.1 + i * 0.045,
              }}
              style={{
                display: "inline-block",
                marginRight: "0.25em",
                position: "relative",
              }}
            >
              {word}
              {i === TRACED_WORD_INDEX && (
                <motion.span
                  aria-hidden
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{
                    duration: 0.7,
                    ease: ease.inOut,
                    delay: reduced ? 0 : 0.85,
                  }}
                  className="absolute -bottom-1 left-0 h-[3px] w-full origin-left rounded-full"
                  style={{
                    background:
                      "linear-gradient(90deg, var(--score), color-mix(in srgb, var(--score) 30%, transparent))",
                    boxShadow: "0 0 18px var(--score-glow)",
                  }}
                />
              )}
            </motion.span>
          ))}
        </h1>

        <motion.p
          {...fade(0.7)}
          className="mx-auto mt-7 max-w-[640px] text-[17px] leading-[1.7] text-text-muted md:text-[19px]"
        >
          Upload your resume, paste a job description, and get a real skill
          fit score, missing skills, and a step-by-step plan to close the gap.
        </motion.p>

        <motion.div
          {...fade(0.85)}
          className="mt-10 flex flex-wrap items-center justify-center gap-3"
        >
          <MagneticButton>
            <ButtonLink href="/analyze" size="lg" rightIcon={<ArrowRight />}>
              Analyze my resume
            </ButtonLink>
          </MagneticButton>
          <MagneticButton>
            <ButtonLink href="/#how-it-works" size="lg" variant="secondary">
              See how it works
            </ButtonLink>
          </MagneticButton>
        </motion.div>

        <motion.div
          {...fade(0.95)}
          className="mt-5 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[14px] text-text-muted"
        >
          <span>No signup required for your first report. Your resume stays private.</span>
        </motion.div>

        <motion.p
          {...fade(1.0)}
          className="mt-2 font-mono text-[12px] uppercase tracking-[0.14em] text-subtle"
        >
          PDF &middot; DOCX &middot; paste text
        </motion.p>
      </div>

      <div className="relative mx-auto max-w-[1200px] -mb-16 sm:-mb-20 md:-mb-24">
        <HeroDocs />
      </div>

    </section>
  );
}

function MagneticButton({ children }: { children: React.ReactNode }) {
  const reduced = useReducedMotion() ?? false;
  const ref = useRef<HTMLDivElement>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 200, damping: 18, mass: 0.4 });
  const sy = useSpring(y, { stiffness: 200, damping: 18, mass: 0.4 });

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    if (reduced) return;
    const node = ref.current;
    if (!node) return;
    const rect = node.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    x.set((e.clientX - cx) * 0.25);
    y.set((e.clientY - cy) * 0.25);
  }

  function onLeave() {
    x.set(0);
    y.set(0);
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={reduced ? undefined : { x: sx, y: sy }}
      className="inline-flex"
    >
      {children}
    </motion.div>
  );
}
