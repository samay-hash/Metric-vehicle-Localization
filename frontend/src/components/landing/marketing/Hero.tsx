import {
  ArrowRight01Icon,
  ArrowUpRight01Icon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { Link } from "react-router-dom";

import { ScrollReveal } from "@/components/landing/animation/ScrollReveal";
import { HeroMockup } from "@/components/landing/marketing/HeroMockup";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionBadge } from "@/components/landing/marketing/parts/sectionHeading";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function Hero() {
  return (
    <Section
      id="hero"
      flushTop
      flushX
      flushBottom
      className="flex flex-col items-center pt-24 text-center sm:pt-28 md:pt-36 lg:pt-44"
    >
      <div className="flex w-full flex-col items-center px-5 sm:px-6 md:px-10">
        <ScrollReveal
          direction="up"
          distance={24}
          duration={0.7}
          className="flex max-w-3xl flex-col items-center"
        >
          <SectionBadge index={1}>Roostr CV</SectionBadge>
          <h1 className="mt-3.5 font-heading text-4xl leading-display font-medium tracking-display text-balance sm:text-5xl md:mt-5 md:text-6xl lg:text-7xl">
            Metric Vehicle Localization.{" "}
            <span className="sm:block">From a Single Camera.</span>
          </h1>
          <p className="mt-3 flex max-w-xl flex-col gap-3 text-base leading-body tracking-tight text-muted-foreground text-pretty md:mt-3.5 md:text-lg">
            <span>
              Estimate exact 3D vehicle positions from monocular RGB images. No LiDAR. No depth camera. Pure computer vision geometry.
            </span>
            <span className="text-sm md:text-base">
              Monocular Depth • Camera Intrinsics • Robust Aggregation
            </span>
          </p>
        </ScrollReveal>

        <ScrollReveal
          direction="up"
          distance={20}
          duration={0.7}
          delay={0.15}
          className="mt-3 flex w-full max-w-md flex-col items-center gap-3 sm:max-w-none"
        >
          <div className="flex w-full flex-col items-stretch gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-center mt-6">

            <a
              href="#features"
              className={cn(
                buttonVariants({ size: "lg", variant: "secondary" }),
                "w-full sm:w-auto",
              )}
            >
              See how it works
              <HugeiconsIcon icon={ArrowUpRight01Icon} data-icon="inline-end" />
            </a>
          </div>
        </ScrollReveal>
      </div>

      <ScrollReveal
        direction="up"
        distance={32}
        duration={0.8}
        delay={0.25}
        className="mt-14 flex w-full flex-col gap-12 md:mt-20 md:gap-16"
      >
        <HeroMockup />
      </ScrollReveal>
    </Section>
  );
}
