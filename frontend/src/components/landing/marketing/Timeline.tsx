import {
  Camera01Icon,
  ComputerIcon,
  MapIcon,
  Search01Icon,
  Tick02Icon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import type { ComponentProps } from "react";

import {
  ScrollReveal,
  StaggerContainer,
  StaggerItem,
} from "@/components/landing/animation/ScrollReveal";
import { AgentChip } from "@/components/landing/marketing/parts/agentChip";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionHeading } from "@/components/landing/marketing/parts/sectionHeading";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type TimelineEntry = {
  stamp: string;
  agent: {
    emoji?: string;
    icon?: ComponentProps<typeof HugeiconsIcon>["icon"];
    name: string;
    role: string;
    image?: string;
    lead?: boolean;
  };
  title: string;
  body?: string;
  tag?: string;
  quote?: string;
  quoteAuthor?: string;
};

const entries: TimelineEntry[] = [
  {
    stamp: "0 ms",
    agent: { icon: Camera01Icon, name: "Dataset", role: "Input" },
    title: "RGB + BBox + Intrinsics",
    body: "A single RGB frame is loaded along with the target vehicle's bounding box and pinhole camera calibration parameters.",
  },
  {
    stamp: "12 ms",
    agent: { icon: Search01Icon, name: "DepthAny", role: "Vision" },
    title: "Relative Depth Estimation",
    quote: '"Dense relative depth map generated. Shape: 512x512"',
    quoteAuthor: "Foundation Model",
  },
  {
    stamp: "45 ms",
    agent: { icon: ComputerIcon, name: "Aggregator", role: "Filter" },
    title: "Robust BBox Sampling",
    body: "The depth map is cropped to the lower half of the vehicle bounding box and a trimmed median is applied to reject outliers and recover the scale (Z).",
    tag: "Scale Recovery",
  },
  {
    stamp: "50 ms",
    agent: { icon: MapIcon, name: "Geometry", role: "Math" },
    title: "X Position & Confidence",
    quote: '"X = (u-cx)*Z/fx | X: +2.31m | Z: 31.82m | Conf: 0.92"',
    quoteAuthor: "Geometric Engine",
    tag: "Final Output",
  },
];

const founderStats = [
  { value: "MAE_Z", label: "Forward Distance Accuracy" },
  { value: "~50ms", label: "Per-image inference time" },
  { value: "3-stage", label: "Baseline → Improved → Ablation" },
];

export function Timeline() {
  return (
    <>
      <Section id="timeline" className="flex flex-col gap-12 md:gap-16">
        <ScrollReveal direction="up" distance={24}>
          <SectionHeading
            index={4}
            heading="Pipeline"
            subheading="Anatomy of a Prediction"
            description="From the moment a frame is loaded to the final CSV output. See how the localization pipeline works."
          />
        </ScrollReveal>

        {/* Hero Quote Card - Moved up, removed image, changed text */}
        <ScrollReveal direction="up" distance={28} duration={0.75} className="w-full max-w-5xl mx-auto">
          <Card className="overflow-hidden border border-dashed border-border/60 bg-muted/30">
            <CardContent className="flex flex-col justify-between gap-6 p-6 sm:p-8 md:p-10 lg:p-12">
              <blockquote className="font-heading text-xl leading-heading tracking-heading text-pretty md:text-2xl lg:text-[1.75rem] lg:leading-heading text-center max-w-4xl mx-auto">
                <span className="font-medium text-foreground">
                  Solving metric depth without hardware sensors.
                </span>{" "}
                <span className="text-muted-foreground">
                  We built a deterministic vision pipeline combining modern foundation models with classical camera geometry. This approach scales seamlessly across arbitrary camera views.
                </span>
              </blockquote>
            </CardContent>
            <CardFooter className="grid grid-cols-3 items-center justify-center gap-4 border-t border-dashed border-border/60 bg-muted/50 p-5 sm:gap-6 sm:p-8 md:p-10 lg:p-8">
              {founderStats.map((stat) => (
                <div key={stat.label} className="flex flex-col items-center text-center gap-1">
                  <p className="font-heading text-2xl leading-title font-medium tracking-title text-brand sm:text-3xl md:text-4xl">
                    {stat.value}
                  </p>
                  <p className="text-xs leading-snug text-muted-foreground font-medium uppercase tracking-widest mt-1 sm:text-sm">
                    {stat.label}
                  </p>
                </div>
              ))}
            </CardFooter>
          </Card>
        </ScrollReveal>

        {/* Mission Log - Open Timeline Flow */}
        <div className="flex flex-col gap-8 md:gap-12 mt-4 max-w-5xl mx-auto w-full">
          <div className="flex flex-col gap-6">
            <ScrollReveal
              direction="up"
              distance={16}
              className="flex flex-wrap items-center justify-between gap-4 border-b border-dashed pb-5"
            >
              <div className="flex flex-wrap items-center gap-3">
                <HugeiconsIcon icon={Camera01Icon} className="size-5 text-muted-foreground" />
                <span className="font-heading text-lg font-medium">Inference Pipeline</span>
                <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                  ~50 milliseconds
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs text-muted-foreground">
                  Mission target:
                </span>
                <span className="rounded-full bg-muted px-2.5 py-0.5 font-mono text-xs font-medium text-muted-foreground">
                  Metric Localization
                </span>
              </div>
            </ScrollReveal>

            <StaggerContainer
              staggerDelay={0.12}
              delayChildren={0.1}
              amount={0.1}
              className="grid gap-6 md:grid-cols-4 md:gap-8"
            >
              {entries.map((entry, index) => {
                const isFirst = index === 0;
                const isLast = index === entries.length - 1;

                return (
                  <StaggerItem
                    key={entry.stamp}
                    direction="up"
                    distance={24}
                    className="group relative flex flex-col items-start gap-4"
                  >
                    <div
                      className={cn(
                        "relative z-10 flex size-10 md:size-12 shrink-0 items-center justify-center rounded-full border border-dashed bg-card shadow-2xs",
                        isFirst && "border-brand/60 bg-card",
                        isLast && "border-brand/60 bg-card text-brand",
                        !isFirst && !isLast && "border-border",
                      )}
                    >
                      {isLast ? (
                        <HugeiconsIcon
                          icon={Tick02Icon}
                          className="size-4 text-brand md:size-5"
                        />
                      ) : isFirst ? (
                        <span className="size-2.5 rounded-full bg-brand" />
                      ) : (
                        <span className="size-2 rounded-full bg-muted-foreground/40 transition-colors group-hover:bg-brand" />
                      )}
                    </div>

                    <div className="flex min-w-0 flex-1 flex-col w-full">
                      <div className="flex flex-wrap items-center gap-2 md:gap-3 mb-2">
                        <span className="font-mono text-[11px] font-semibold tracking-tight text-muted-foreground">
                          {entry.stamp}
                        </span>
                        <AgentChip {...entry.agent} />
                      </div>

                      <h3 className="font-heading text-base md:text-lg leading-title font-medium tracking-title">
                        {entry.title}
                      </h3>

                      {entry.body ? (
                        <p className="mt-2 text-sm leading-body text-muted-foreground text-pretty">
                          {entry.body}
                        </p>
                      ) : null}

                      {entry.quote ? (
                        <div className="mt-3 w-full rounded-xl border border-dashed border-border bg-card/60 p-3 text-xs leading-body">
                          <span className="font-medium text-foreground italic">
                            {entry.quote}
                          </span>
                        </div>
                      ) : null}
                    </div>
                  </StaggerItem>
                );
              })}
            </StaggerContainer>
          </div>
        </div>

        {/* Architecture Image */}
        <ScrollReveal direction="up" distance={24} duration={0.8} delay={0.2} className="relative w-full max-w-5xl mx-auto mt-4">
           <div className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-xl p-2 lg:p-4">
             <div className="absolute inset-0 bg-gradient-to-t from-background/40 via-background/0 to-background/0 z-10 pointer-events-none rounded-2xl" />
             <img src="/anatomy.png" alt="Inferia Architecture Diagram" className="w-full max-h-[600px] object-contain rounded-xl border border-border shadow-sm" />
           </div>
        </ScrollReveal>
      </Section>
    </>
  );
}
