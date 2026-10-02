"use client";

import {
  File01Icon,
  LockIcon,
  Search01Icon,
  SparklesIcon,
  Tick02Icon,
  Location01Icon,
  DocumentValidationIcon,
  RouteIcon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import type { ComponentProps, ReactNode } from "react";

import { ScrollReveal } from "@/components/landing/animation/ScrollReveal";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionHeading } from "@/components/landing/marketing/parts/sectionHeading";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

type AgentIcon = ComponentProps<typeof HugeiconsIcon>["icon"];

function MapTopologyMockup() {
  return (
    <div className="absolute inset-x-4 top-1/2 -translate-y-1/2 md:inset-x-8 xl:inset-x-12">
      <div className="mx-auto max-w-[22rem] overflow-hidden rounded-[1.25rem] border bg-background/90 p-4 shadow-2xl shadow-black/10 backdrop-blur-xl sm:p-5">
        <div className="flex items-center gap-3 border-b border-dashed pb-4">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-red-500/10 text-red-500">
            <HugeiconsIcon icon={Location01Icon} className="size-4" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight">Active Topology</span>
            <span className="text-xs text-muted-foreground">City Center Grid</span>
          </div>
          <div className="ml-auto flex items-center gap-1.5 rounded-full bg-red-500/10 px-2 py-0.5 text-[0.65rem] font-bold text-red-600">
            <span className="relative flex size-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75"></span>
              <span className="relative inline-flex size-1.5 rounded-full bg-red-500"></span>
            </span>
            Alert Triggered
          </div>
        </div>
        <div className="relative mt-4 h-32 w-full rounded-lg bg-zinc-100 dark:bg-zinc-800/50 overflow-hidden">
          {/* Abstract Map Lines */}
          <div className="absolute top-1/2 left-0 h-px w-full bg-zinc-300 dark:bg-zinc-700"></div>
          <div className="absolute top-0 left-1/3 h-full w-px bg-zinc-300 dark:bg-zinc-700"></div>
          <div className="absolute top-1/4 left-0 h-px w-full bg-zinc-300 dark:bg-zinc-700 transform rotate-45"></div>
          
          {/* Node 1 */}
          <div className="absolute top-[40%] left-[25%] size-3 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
          {/* Node 2 */}
          <div className="absolute top-[20%] left-[60%] size-3 rounded-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
          {/* Node 3 (Alert) */}
          <div className="absolute top-[60%] left-[50%] size-4 rounded-full bg-red-500 shadow-[0_0_15px_rgba(239,68,68,0.8)] z-10 flex items-center justify-center">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75"></span>
          </div>
        </div>
      </div>
    </div>
  );
}

function EventCatchingMockup() {
  return (
    <div className="absolute inset-x-4 top-1/2 -translate-y-1/2 md:inset-x-8 xl:inset-x-12">
      <div className="mx-auto max-w-[22rem] overflow-hidden rounded-[1.25rem] border bg-background/90 p-4 shadow-2xl shadow-black/10 backdrop-blur-xl sm:p-5">
        <div className="flex items-center gap-3 border-b border-dashed pb-4">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-blue-500/10 text-blue-500">
            <HugeiconsIcon icon={SparklesIcon} className="size-4" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight">Event Captured</span>
            <span className="text-xs text-muted-foreground">05s Pre-roll | 05s Post-roll</span>
          </div>
        </div>
        <div className="mt-4 flex flex-col gap-2">
          <div className="flex w-full items-center gap-2">
            <span className="w-12 text-[0.65rem] font-medium text-muted-foreground">11:42:01</span>
            <div className="h-1.5 flex-1 rounded-full bg-zinc-100 dark:bg-zinc-800"></div>
          </div>
          <div className="flex w-full items-center gap-2">
            <span className="w-12 text-[0.65rem] font-medium text-brand">11:42:03</span>
            <div className="relative h-1.5 flex-1 rounded-full bg-brand/20">
              <div className="absolute left-1/4 h-full w-1/2 rounded-full bg-brand"></div>
            </div>
            <span className="text-[0.6rem] font-bold text-brand uppercase tracking-wider">Anomaly</span>
          </div>
          <div className="flex w-full items-center gap-2">
            <span className="w-12 text-[0.65rem] font-medium text-muted-foreground">11:42:05</span>
            <div className="h-1.5 flex-1 rounded-full bg-zinc-100 dark:bg-zinc-800"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReportMockup() {
  return (
    <div className="absolute inset-x-4 top-1/2 -translate-y-1/2 md:inset-x-8 xl:inset-x-12">
      <div className="mx-auto max-w-[20rem] -rotate-2 overflow-hidden rounded-[1.25rem] border bg-background p-4 shadow-2xl shadow-black/10 transition-transform hover:rotate-0 sm:p-5">
        <div className="flex items-center gap-3 border-b border-dashed pb-4">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-500">
            <HugeiconsIcon icon={DocumentValidationIcon} className="size-4" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold tracking-tight">Incident_Report.pdf</span>
            <span className="text-xs text-muted-foreground">Generated instantly</span>
          </div>
        </div>
        <div className="mt-5 space-y-3 opacity-60">
          <div className="h-2 w-3/4 rounded-full bg-muted-foreground/30"></div>
          <div className="h-2 w-full rounded-full bg-muted-foreground/20"></div>
          <div className="h-2 w-5/6 rounded-full bg-muted-foreground/20"></div>
          <div className="mt-4 flex gap-2">
            <div className="h-12 w-20 rounded bg-muted-foreground/20"></div>
            <div className="h-12 w-20 rounded bg-muted-foreground/20"></div>
          </div>
          <div className="h-2 w-1/2 rounded-full bg-muted-foreground/30 mt-4"></div>
        </div>
      </div>
    </div>
  );
}

const features = [
  {
    eyebrow: "Live Awareness",
    title: "Interactive 2D Topology",
    body: "Upload a map of your city, bank layout, or campus. The moment an anomaly is detected, the exact camera node starts blinking red on the map.",
    points: [
      "Custom 2D Map overlays",
      "Instant visual pinging on threat detection",
      "Click any node for a live RTSP feed overlay",
    ],
    image: "/marketing/hero-canvas.jpg",
    imagePosition: "object-[center_40%]",
    overlay: <MapTopologyMockup />,
  },
  {
    eyebrow: "Intelligent Indexing",
    title: "Smart Event Catching",
    body: "Don't scrub through hours of empty footage. The edge node automatically clips 5 seconds before and after any suspicious event.",
    points: [
      "Auto-clipping of pre/post roll footage",
      "Drastically reduces storage overhead",
      "Only significant events are sent to the command center",
    ],
    image: "/marketing/squad-canvas-hills.jpg",
    imagePosition: "object-[70%_55%]",
    overlay: <EventCatchingMockup />,
  },
  {
    eyebrow: "Compliance Ready",
    title: "Automated Report Gen",
    body: "Every verified incident automatically compiles into a law enforcement ready PDF report with timestamps, location, and key frames.",
    points: [
      "Zero manual paperwork for operators",
      "Includes exact geolocation and timestamp metadata",
      "Ready to attach directly to an FIR or incident log",
    ],
    image: "/marketing/squad-canvas-canyon.jpg",
    imagePosition: "object-[30%_60%]",
    overlay: <ReportMockup />,
  },
];

export function MissionFeatures() {
  return (
    <Section id="features" className="flex flex-col gap-12 md:gap-16">
      <ScrollReveal direction="up" distance={24}>
        <SectionHeading
          index={4}
          heading="Beyond standard CCTV."
          subheading="Features that turn footage into intelligence."
          description="We built capabilities that usually cost millions and bundled them directly into the edge layer."
        />
      </ScrollReveal>

      <div className="relative flex w-full min-w-0 flex-col [--stack-top:6rem] sm:[--stack-top:7rem] md:[--stack-top:8rem]">
        {features.map((feature, index) => {
          const imageOnLeft = index % 2 === 1;
          const isLast = index === features.length - 1;

          return (
            <div
              key={feature.title}
              className={cn(
                "sticky top-[var(--stack-top)] flex w-full flex-col gap-6 md:min-h-[32rem] md:flex-row md:items-stretch lg:min-h-[36rem]",
                isLast ? "mb-0" : "mb-24 lg:mb-32",
              )}
            >
              <div
                className={cn(
                  "flex w-full flex-col justify-center gap-8 md:w-1/2 lg:w-[45%]",
                  imageOnLeft ? "md:order-2 md:pl-12 lg:pl-16" : "md:pr-12 lg:pr-16",
                )}
              >
                <div className="flex flex-col gap-3.5">
                  <span className="text-xs font-bold tracking-eyebrow text-brand uppercase">
                    {feature.eyebrow}
                  </span>
                  <h3 className="font-heading text-3xl font-medium leading-title tracking-tight md:text-4xl lg:text-5xl lg:leading-[1.1]">
                    {feature.title}
                  </h3>
                  <p className="mt-2 text-base text-muted-foreground lg:text-lg">
                    {feature.body}
                  </p>
                </div>
                <div className="flex flex-col gap-4">
                  {feature.points.map((point) => (
                    <div key={point} className="flex items-start gap-3">
                      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand">
                        <HugeiconsIcon icon={Tick02Icon} className="size-3.5" />
                      </span>
                      <span className="text-sm font-medium">{point}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div
                className={cn(
                  "relative flex min-h-[22rem] w-full flex-col overflow-hidden rounded-3xl bg-muted md:min-h-0 md:w-1/2 lg:w-[55%]",
                  imageOnLeft ? "md:order-1" : "",
                )}
              >
                <img
                  src={feature.image}
                  alt=""
                  className={cn(
                    "absolute inset-0 h-full w-full object-cover",
                    feature.imagePosition,
                  )}
                />
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 bg-gradient-to-t from-background/35 via-transparent to-background/10"
                />
                {feature.overlay}
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
