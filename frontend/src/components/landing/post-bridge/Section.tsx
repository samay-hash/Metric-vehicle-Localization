import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type SectionProps = {
  id?: string;
  children: ReactNode;
  /** Applied to the <section> element. */
  className?: string;
  /** Applied to the inner container — use for one-off padding overrides. */
  containerClassName?: string;
};

/**
 * The page's single source of horizontal and vertical rhythm. Every marketing
 * section renders through this so gutters and section padding step at exactly
 * the same breakpoints, at every screen size.
 */
export default function Section({
  id,
  children,
  className,
  containerClassName,
}: SectionProps) {
  return (
    <section id={id} className={cn("scroll-mt-20", className)}>
      <div
        className={cn(
          "mx-auto w-full min-w-0 max-w-7xl px-5 sm:px-6 lg:px-8",
          "py-16 md:py-20 lg:py-24 xl:py-28 2xl:py-32",
          containerClassName,
        )}
      >
        {children}
      </div>
    </section>
  );
}
