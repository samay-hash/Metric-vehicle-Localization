import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

type SectionProps = ComponentProps<"section"> & {
  flushTop?: boolean;
  flushX?: boolean;
  flushBottom?: boolean;
};

export function Section({
  className,
  flushTop = false,
  flushX = false,
  flushBottom = false,
  children,
  ...props
}: SectionProps) {
  return (
    <section
      className={cn(
        "scroll-mt-24 border-b border-dashed",
        !flushTop && "border-t",
      )}
      {...props}
    >
      <div
        className={cn(
          "mx-auto w-full max-w-7xl",
          flushX ? "px-0" : "px-5 sm:px-6 md:px-10",
          flushBottom
            ? "pt-16 sm:pt-20 md:pt-28 lg:pt-32"
            : "py-16 sm:py-20 md:py-28 lg:py-32",
          className,
        )}
      >
        {children}
      </div>
    </section>
  );
}
