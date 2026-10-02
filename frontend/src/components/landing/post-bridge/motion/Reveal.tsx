"use client";

import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

const EASE = "easeOut" as const;

type RevealProps = {
  children: ReactNode;
  className?: string;
  /** Seconds to hold before the reveal starts — used to stagger siblings. */
  delay?: number;
  /** Travel distance in px. Set to 0 for elements that shouldn't shift. */
  y?: number;
};

/**
 * Scroll-triggered entrance used by every section, so the whole page enters
 * with one motion vocabulary: short travel, one easing curve, plays once.
 * Honours prefers-reduced-motion by fading only.
 */
export default function Reveal({
  children,
  className,
  delay = 0,
  y = 18,
}: RevealProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: reduceMotion ? 0 : y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.55, delay, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}
