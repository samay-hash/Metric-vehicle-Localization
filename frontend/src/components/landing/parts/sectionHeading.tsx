import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export const MARKETING_SECTION_TOTAL = 9;

export function IndexBars({ index, total }: { index: number; total: number }) {
  return (
    <span className="flex gap-0.5" aria-hidden>
      {Array.from({ length: total }, (_, bar) => (
        <span
          key={`bar-${bar + 1}`}
          className={cn("h-3 w-0.5", bar < index ? "bg-brand" : "bg-border")}
        />
      ))}
    </span>
  );
}

export function SectionBadge({
  children,
  index,
  total = MARKETING_SECTION_TOTAL,
}: {
  children: ReactNode;
  index: number;
  total?: number;
}) {
  return (
    <Badge variant="outline">
      <IndexBars index={index} total={total} />
      {children}
    </Badge>
  );
}

type SectionHeadingProps = {
  heading: string;
  subheading: ReactNode;
  description: ReactNode;
  index: number;
  align?: "start" | "center";
  className?: string;
  children?: ReactNode;
};

export function SectionHeading({
  heading,
  subheading,
  description,
  index,
  align = "start",
  className,
  children,
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "flex max-w-3xl flex-col",
        align === "center" && "mx-auto items-center text-center",
        className,
      )}
    >
      <div
        className={cn("flex flex-col", align === "center" && "items-center")}
      >
        <SectionBadge index={index}>{heading}</SectionBadge>
        <h2 className="mt-3.5 max-w-3xl font-heading text-3xl leading-heading font-medium tracking-heading text-balance sm:text-4xl md:mt-4 md:text-5xl">
          {subheading}
        </h2>
        <p className="mt-3 max-w-xl text-base leading-body tracking-tight text-muted-foreground text-pretty md:text-lg">
          {description}
        </p>
      </div>
      {children ? <div className="mt-8 md:mt-10">{children}</div> : null}
    </div>
  );
}
