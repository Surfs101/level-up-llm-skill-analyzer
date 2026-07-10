export const ease = {
  out: [0.23, 1, 0.32, 1],          // strong ease-out for entries
  inOut: [0.77, 0, 0.175, 1],       // strong ease-in-out for on-screen movement
  drawer: [0.32, 0.72, 0, 1],       // iOS-like
} as const;

export const fadeUp = (delay = 0, reduceMotion = false) => ({
  initial: { opacity: 0, y: reduceMotion ? 0 : 8 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.25, ease: ease.out, delay },
});

export const stagger = (gap = 0.05) => ({
  animate: { transition: { staggerChildren: gap } },
});
