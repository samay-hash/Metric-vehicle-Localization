"use client";

import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";
import { BODY, EYEBROW } from "./rhythm";

const EASE = "easeOut" as const;

type SectionHeaderProps = {
  /** Small label above the heading, preceded by a brand rule. */
  eyebrow: string;
  /** First heading line — rendered in foreground. */
  title: string;
  /** Second heading line — rendered muted, for the "question / answer" cadence. */
  titleMuted?: string;
  /** Supporting copy below the heading. */
  description?: string;
  align?: "left" | "center";
  className?: string;
};

export default function SectionHeader({
  eyebrow,
  title,
  titleMuted,
  description,
  align = "center",
  className,
}: SectionHeaderProps) {
  const centered = align === "center";
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={{ opacity: 0, y: reduceMotion ? 0 : 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.4 }}
      transition={{ duration: 0.55, ease: EASE }}
      className={cn(
        "w-full min-w-0 max-w-2xl",
        centered ? "mx-auto text-center" : "text-left",
        className,
      )}
    >
      {/* Rule and label share the muted tone — the eyebrow is a quiet label,
          not an accent, so it stays out of the headline's way. */}
      <p
        className={cn(
          "flex items-center gap-2.5",
          EYEBROW,
          centered && "justify-center",
        )}
      >
        <span className="h-[5px] w-2.5 shrink-0 rounded-full bg-muted-foreground" />
        {eyebrow}
      </p>

      {/* Same display treatment as ReadyCTA so every large heading on the page
          is one type style: medium first line, regular muted second line. */}
      <h2 className="font-heading mt-4 w-full text-[1.875rem] leading-[1.08] font-medium tracking-[-0.032em] text-balance sm:text-[2.25rem] md:text-[2.5rem] md:leading-[1.06] lg:text-[2.75rem]">
        {title}
        {titleMuted && (
          <span className="block font-normal text-muted-foreground">
            {titleMuted}
          </span>
        )}
      </h2>

      {description && (
        <p
          className={cn(
            BODY,
            "mt-5 text-muted-foreground md:text-base md:leading-8",
            // Left-aligned headers get a shorter measure; centered ones already
            // inherit the wrapper's max-w-2xl.
            !centered && "max-w-xl",
          )}
        >
          {description}
        </p>
      )}
    </motion.div>
  );
}
