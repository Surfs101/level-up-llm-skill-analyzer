"use client";

import { motion, useReducedMotion } from "motion/react";

import { ease } from "@/lib/motion";

const X0 = 380;
const X1 = 1020;
const PYLON_W = 18;
const Y_TOP = 60;
const Y_DECK_TOP = 280;
const Y_DECK_BOTTOM = 294;
const Y_CTRL = 296;

function cableY(x: number) {
  const t = (x - X0) / (X1 - X0);
  return Y_TOP + (Y_CTRL - Y_TOP) * 2 * t * (1 - t);
}

const SUSPENDERS: number[] = [];
for (let x = X0 + 28; x < X1; x += 28) SUSPENDERS.push(x);

export default function HeroBridge() {
  const reduced = useReducedMotion() ?? false;

  return (
    <span
      aria-hidden
      className="pointer-events-none absolute inset-x-0 bottom-0 -z-10"
    >
      <svg
        viewBox="0 0 1400 320"
        className="block h-auto w-full"
        preserveAspectRatio="xMidYEnd meet"
      >
        <defs>
          <linearGradient id="bridge-cable" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--decor)" stopOpacity="0.08" />
            <stop offset="50%" stopColor="var(--decor)" stopOpacity="0.6" />
            <stop offset="100%" stopColor="var(--decor)" stopOpacity="0.08" />
          </linearGradient>
          <linearGradient id="bridge-deck" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--decor)" stopOpacity="0" />
            <stop offset="20%" stopColor="var(--decor)" stopOpacity="0.4" />
            <stop offset="80%" stopColor="var(--decor)" stopOpacity="0.4" />
            <stop offset="100%" stopColor="var(--decor)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Faint construction lines */}
        <motion.g
          initial={reduced ? undefined : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: reduced ? 0 : 0.2 }}
        >
          <line
            x1={X0 + PYLON_W / 2}
            y1={10}
            x2={X0 + PYLON_W / 2}
            y2={Y_DECK_TOP}
            stroke="var(--decor)"
            strokeOpacity="0.08"
            strokeDasharray="1 5"
            strokeWidth="0.5"
          />
          <line
            x1={X1 + PYLON_W / 2}
            y1={10}
            x2={X1 + PYLON_W / 2}
            y2={Y_DECK_TOP}
            stroke="var(--decor)"
            strokeOpacity="0.08"
            strokeDasharray="1 5"
            strokeWidth="0.5"
          />
          <line
            x1={20}
            y1={Y_DECK_TOP}
            x2={1380}
            y2={Y_DECK_TOP}
            stroke="var(--decor)"
            strokeOpacity="0.07"
            strokeDasharray="1 6"
            strokeWidth="0.5"
          />
        </motion.g>

        {/* Back-stays */}
        <motion.path
          d={`M -60 ${Y_DECK_TOP + 16} L ${X0 + PYLON_W / 2} ${Y_TOP}`}
          fill="none"
          stroke="var(--decor)"
          strokeOpacity="0.42"
          strokeWidth="1"
          strokeLinecap="round"
          initial={reduced ? undefined : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.7, ease: ease.out, delay: reduced ? 0 : 0.45 }}
        />
        <motion.path
          d={`M ${X1 + PYLON_W / 2} ${Y_TOP} L 1460 ${Y_DECK_TOP + 16}`}
          fill="none"
          stroke="var(--decor)"
          strokeOpacity="0.42"
          strokeWidth="1"
          strokeLinecap="round"
          initial={reduced ? undefined : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.7, ease: ease.out, delay: reduced ? 0 : 0.45 }}
        />

        {/* Main suspension cable */}
        <motion.path
          d={`M ${X0 + PYLON_W / 2} ${Y_TOP} Q 700 ${Y_CTRL} ${X1 + PYLON_W / 2} ${Y_TOP}`}
          fill="none"
          stroke="url(#bridge-cable)"
          strokeWidth="1.6"
          strokeLinecap="round"
          initial={reduced ? undefined : { pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1, ease: ease.out, delay: reduced ? 0 : 0.55 }}
        />

        {/* Suspender hangers */}
        <motion.g
          initial={reduced ? undefined : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: reduced ? 0 : 1.0 }}
        >
          {SUSPENDERS.map((x) => {
            const y = cableY(x);
            if (y >= Y_DECK_TOP - 1) return null;
            const fade = 1 - Math.abs((x - 700) / 320) * 0.6;
            return (
              <line
                key={x}
                x1={x}
                y1={y}
                x2={x}
                y2={Y_DECK_TOP}
                stroke="var(--decor)"
                strokeOpacity={(0.28 * fade).toFixed(3)}
                strokeWidth="0.7"
                strokeLinecap="round"
              />
            );
          })}
        </motion.g>

        {/* Pylons — pure outlines, no fill */}
        {[X0, X1].map((px, i) => (
          <motion.g
            key={px}
            initial={reduced ? undefined : { opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.6,
              ease: ease.out,
              delay: reduced ? 0 : 0.3 + i * 0.06,
            }}
          >
            <rect
              x={px}
              y={Y_TOP}
              width={PYLON_W}
              height={Y_DECK_TOP - Y_TOP}
              fill="none"
              stroke="var(--decor)"
              strokeOpacity="0.45"
              strokeWidth="1"
            />
            {/* Top crossbeam */}
            <rect
              x={px - 10}
              y={Y_TOP - 7}
              width={PYLON_W + 20}
              height={7}
              fill="none"
              stroke="var(--decor)"
              strokeOpacity="0.45"
              strokeWidth="1"
            />
            {/* Mid crossbeam */}
            <line
              x1={px - 5}
              y1={Y_TOP + 70}
              x2={px + PYLON_W + 5}
              y2={Y_TOP + 70}
              stroke="var(--decor)"
              strokeOpacity="0.32"
              strokeWidth="0.8"
            />
            {/* Lower crossbeam */}
            <line
              x1={px - 5}
              y1={Y_DECK_TOP - 30}
              x2={px + PYLON_W + 5}
              y2={Y_DECK_TOP - 30}
              stroke="var(--decor)"
              strokeOpacity="0.32"
              strokeWidth="0.8"
            />
            {/* Diagonal bracing */}
            <line
              x1={px}
              y1={Y_TOP + 70}
              x2={px + PYLON_W}
              y2={Y_DECK_TOP - 30}
              stroke="var(--decor)"
              strokeOpacity="0.18"
              strokeWidth="0.5"
            />
            <line
              x1={px + PYLON_W}
              y1={Y_TOP + 70}
              x2={px}
              y2={Y_DECK_TOP - 30}
              stroke="var(--decor)"
              strokeOpacity="0.18"
              strokeWidth="0.5"
            />
            {/* Cable anchor dot */}
            <circle
              cx={px + PYLON_W / 2}
              cy={Y_TOP - 7}
              r={1.6}
              fill="var(--decor)"
              fillOpacity="0.55"
            />
            {/* Drafting corner ticks */}
            {[
              [px - 1, Y_TOP - 7],
              [px + PYLON_W + 1, Y_TOP - 7],
              [px - 1, Y_DECK_TOP],
              [px + PYLON_W + 1, Y_DECK_TOP],
            ].map(([cx, cy], j) => (
              <line
                key={j}
                x1={cx as number}
                y1={cy as number}
                x2={(cx as number) + ((cx as number) > px + PYLON_W / 2 ? 3 : -3)}
                y2={cy as number}
                stroke="var(--decor)"
                strokeOpacity="0.25"
                strokeWidth="0.5"
              />
            ))}
          </motion.g>
        ))}

        {/* Deck — thin double line */}
        <motion.g
          initial={reduced ? undefined : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, ease: ease.out, delay: reduced ? 0 : 0.65 }}
        >
          <line
            x1={0}
            y1={Y_DECK_TOP}
            x2={1400}
            y2={Y_DECK_TOP}
            stroke="url(#bridge-deck)"
            strokeWidth="1.4"
          />
          <line
            x1={0}
            y1={Y_DECK_BOTTOM}
            x2={1400}
            y2={Y_DECK_BOTTOM}
            stroke="var(--decor)"
            strokeOpacity="0.14"
            strokeWidth="0.6"
            strokeDasharray="2 6"
          />
          {/* Deck-edge anchor markers */}
          {[60, 220, 1180, 1340].map((x) => (
            <g key={x}>
              <circle
                cx={x}
                cy={Y_DECK_TOP}
                r={0.9}
                fill="var(--decor)"
                fillOpacity="0.45"
              />
              <line
                x1={x}
                y1={Y_DECK_TOP - 3}
                x2={x}
                y2={Y_DECK_TOP + 3}
                stroke="var(--decor)"
                strokeOpacity="0.3"
                strokeWidth="0.5"
              />
            </g>
          ))}
        </motion.g>

      </svg>
    </span>
  );
}
