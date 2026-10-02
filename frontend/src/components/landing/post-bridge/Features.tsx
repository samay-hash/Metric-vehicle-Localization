"use client";

import { ArrowRight01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { Icon } from "@iconify/react";
import { easeOut } from "motion";
import {
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
} from "motion/react";
import { useRef } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ART_FILTER,
  BODY,
  HEADER_GAP,
  OVERLINE,
  PANEL_MEDIA,
  PANEL_PADDING,
} from "./rhythm";
import Section from "./Section";
import SectionHeader from "./SectionHeader";

const blocks = [
  {
    eyebrow: "EDGE DEPLOYMENT (AWS T3)",
    title: "Filter out 98% of visual noise locally.",
    desc: "We deploy lightweight YOLOv8 models on cost effective AWS T3 instances near the edge. They process RTSP streams locally, dropping irrelevant frames like normal traffic and instantly flagging anomalies without saturating network bandwidth.",
    ctaPrimary: "View edge architecture",
    art: "/marketing/hero-panel.png",
    preview: "edge" as const,
  },
  {
    eyebrow: "CONTEXTUAL VLM (NVIDIA GPUs)",
    title: "Understand intent, not just pixels.",
    desc: "Flagged frames are securely routed to our on premise LLaVA model accelerated by NVIDIA GPUs (A100/T4). It analyzes the scene to verify threats, distinguishing between a normal late-night worker and a masked intruder lingering near the vault.",
    ctaPrimary: "Explore AI capabilities",
    art: "/marketing/cta-meadow.png",
    preview: "vlm" as const,
  },
  {
    eyebrow: "REAL-TIME TELEMETRY",
    title: "Sub 100ms instant alerts.",
    desc: "Watch the camera feeds turn red the exact millisecond a threat is confirmed by the GPU cluster. WebSocket technology delivers instant situational awareness to your Command Center dashboard.",
    ctaPrimary: "View live latency",
    art: "/marketing/features/studio-blooms.png",
    preview: "telemetry" as const,
  },
];

function FloatingEdgeCard() {
  return (
    <div className="absolute inset-x-5 top-1/2 -translate-y-1/2 scale-[0.90] rounded-[1.25rem] border bg-card p-5 shadow-2xl shadow-black/10 sm:inset-x-8 sm:p-7 lg:scale-100 xl:scale-[1.05]">
      <div className="flex items-center justify-between mb-6">
        <p className="text-[0.9rem] font-bold text-foreground">Node Status</p>
        <span className="inline-flex items-center rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[0.65rem] font-bold tracking-wide text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400">
          Active
        </span>
      </div>
      <div className="flex flex-col gap-4">
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:camera" className="size-3.5 text-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Camera 01: Main Gate</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">Ingesting RTSP at 190 FPS.</span>
          </div>
        </div>
        <hr className="border-border/60 my-1" />
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:cpu" className="size-3.5 text-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Edge AI</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">YOLOv8 real time filtering active.</span>
          </div>
        </div>
        <hr className="border-border/60 my-1" />
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:database" className="size-3.5 text-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Bandwidth</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">98% of visual noise successfully dropped.</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function FloatingVLMCard() {
  return (
    <div className="absolute inset-x-5 top-1/2 -translate-y-1/2 scale-[0.90] rounded-[1.25rem] border bg-card p-5 shadow-2xl shadow-black/10 sm:inset-x-8 sm:p-7 lg:scale-100 xl:scale-[1.05]">
      <div className="flex items-center justify-between mb-6">
        <p className="text-[0.9rem] font-bold text-foreground">VLM Analysis</p>
        <span className="inline-flex items-center rounded-full bg-blue-500/15 px-2.5 py-0.5 text-[0.65rem] font-bold tracking-wide text-blue-600 dark:bg-blue-500/20 dark:text-blue-400">
          On-Premise
        </span>
      </div>
      <div className="flex flex-col gap-4">
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:scan-eye" className="size-3.5 text-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Scene Context</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">Person detected near vault corridor.</span>
          </div>
        </div>
        <hr className="border-border/60 my-1" />
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:shield-alert" className="size-3.5 text-red-500" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Threat Intent</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">Covered face identified during after-hours.</span>
          </div>
        </div>
        <hr className="border-border/60 my-1" />
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:check-circle-2" className="size-3.5 text-emerald-500" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Confidence</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">94% threat verified. Pushing alert.</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function FloatingTelemetryCard() {
  return (
    <div className="absolute inset-x-5 top-1/2 -translate-y-1/2 scale-[0.90] rounded-[1.25rem] border bg-card p-5 shadow-2xl shadow-black/10 sm:inset-x-8 sm:p-7 lg:scale-100 xl:scale-[1.05]">
      <div className="flex items-center justify-between mb-6">
        <p className="text-[0.9rem] font-bold text-foreground">WebSocket Stream</p>
        <span className="inline-flex items-center rounded-full bg-red-500/15 px-2.5 py-0.5 text-[0.65rem] font-bold tracking-wide text-red-600 dark:bg-red-500/20 dark:text-red-400">
          Live
        </span>
      </div>
      <div className="flex flex-col gap-4">
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:zap" className="size-3.5 text-yellow-500" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Latency</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">Inference at ~5.2ms per frame.</span>
          </div>
        </div>
        <hr className="border-border/60 my-1" />
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:activity" className="size-3.5 text-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Connection</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">Sub 100ms full duplex sync active.</span>
          </div>
        </div>
        <hr className="border-border/60 my-1" />
        <div className="flex gap-4">
          <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-secondary/80 border border-border/50">
            <Icon icon="lucide:bell-ring" className="size-3.5 text-brand" />
          </div>
          <div className="flex flex-col">
            <span className="text-[0.8rem] font-bold text-foreground">Alerts</span>
            <span className="text-[0.8rem] leading-relaxed text-muted-foreground mt-0.5">Real time alerts pushed to command center.</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeaturePreview({
  kind,
}: {
  kind: (typeof blocks)[number]["preview"];
}) {
  if (kind === "edge") return <FloatingEdgeCard />;
  if (kind === "vlm") return <FloatingVLMCard />;
  if (kind === "telemetry") return <FloatingTelemetryCard />;
  return null;
}

type FeatureBlock = (typeof blocks)[number];

function StickyFeatureCard({
  block,
  index,
  total,
}: {
  block: FeatureBlock;
  index: number;
  total: number;
}) {
  const ref = useRef<HTMLElement>(null);
  const reduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });

  const scale = useTransform(
    scrollYProgress,
    [0, 1],
    reduceMotion ? [1, 1] : [1, 0.94],
    { ease: easeOut },
  );
  const overlay = useTransform(
    scrollYProgress,
    [0, 1],
    reduceMotion ? [0, 0] : [0, 0.18],
    { ease: easeOut },
  );

  return (
    <article
      ref={ref}
      className="sticky"
      style={{
        top: `calc(5.75rem + ${index * 1.0}rem)`,
        zIndex: index + 1,
      }}
    >
      <motion.div
        style={{ scale, transformOrigin: "top center" }}
        className={cn(
          "relative grid items-center overflow-hidden rounded-[2rem] bg-zinc-50 dark:bg-zinc-900/40 border border-border/50 md:grid-cols-2",
          index < total - 1 && "mb-6 md:mb-10 lg:mb-14",
        )}
      >
        <div
          className={cn(
            "flex min-w-0 flex-col py-12 px-8 sm:p-14 lg:p-20",
            index % 2 === 1 && "md:order-2",
          )}
        >
          <p className={`text-muted-foreground font-bold tracking-widest text-[0.7rem] uppercase`}>
            {block.eyebrow}
          </p>
          <h3 className="font-heading mt-4 text-[2rem] leading-[1.1] font-medium tracking-tight text-balance md:text-[2.5rem]">
            {block.title}
          </h3>
          <p className={`mt-5 max-w-[54ch] text-muted-foreground leading-relaxed text-[1.05rem]`}>
            {block.desc}
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button
              size="lg"
              className="rounded-full bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-[0.95rem] shadow-lg shadow-emerald-900/20 [&_svg]:transition-transform [&_svg]:duration-200 hover:[&_svg]:translate-x-1"
            >
              {block.ctaPrimary}
              <HugeiconsIcon icon={ArrowRight01Icon} data-icon="inline-end" className="ml-1 size-4" />
            </Button>
          </div>
        </div>

        <div
          className={cn(
            "relative h-full overflow-hidden min-h-[400px] md:min-h-[600px] bg-muted",
          )}
        >
          {block.art && (
            <img
              src={block.art}
              alt=""
              className={`absolute inset-0 h-full w-full object-cover object-center ${ART_FILTER}`}
            />
          )}
          <FeaturePreview kind={block.preview} />
        </div>

        <motion.div
          aria-hidden
          style={{ opacity: overlay }}
          className="pointer-events-none absolute inset-0 bg-background"
        />
      </motion.div>
    </article>
  );
}

export function PostBridgeFeatures() {
  return (
    <Section id="features" className="pt-8 pb-16">
      <SectionHeader
        eyebrow="Capabilities"
        title="Unified Intelligence."
        titleMuted="Track threats across any camera."
      />

      <div className={`${HEADER_GAP} relative`}>
        {blocks.map((block, index) => (
          <StickyFeatureCard
            key={block.title}
            block={block}
            index={index}
            total={blocks.length}
          />
        ))}
      </div>
    </Section>
  );
}
