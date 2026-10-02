"use client";

import { motion } from "motion/react";
import { HugeiconsIcon } from "@hugeicons/react";
import { Search01Icon, Target01Icon } from "@hugeicons/core-free-icons";
import { cn } from "@/lib/utils";
import Section from "./Section";
import { SOFT_CHIP } from "./rhythm";

function FeatureCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="absolute inset-x-5 top-1/2 -translate-y-1/2 scale-[0.90] rounded-[1.25rem] border bg-card p-4 shadow-2xl shadow-black/10 sm:inset-x-8 sm:p-5">
      {children}
    </div>
  );
}

function CameraPreview() {
  return (
    <FeatureCard>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm leading-5 font-medium">Node Processing</p>
        <span className={SOFT_CHIP}>
          <HugeiconsIcon icon={Target01Icon} className="size-3" />
          Active
        </span>
      </div>
      <div className="mt-4 flex flex-col gap-2">
         <div className="flex justify-between text-xs text-muted-foreground border-b border-border pb-2">
            <span>Frames Analyzed</span>
            <span className="font-mono text-foreground">5,720</span>
         </div>
         <div className="flex justify-between text-xs text-muted-foreground border-b border-border pb-2">
            <span>False Positives Dropped</span>
            <span className="font-mono text-foreground">98.4%</span>
         </div>
         <div className="flex justify-between text-xs text-muted-foreground pt-1">
            <span>Current Latency</span>
            <span className="font-mono text-brand">5.2ms</span>
         </div>
      </div>
    </FeatureCard>
  );
}

function VLMPreview() {
  return (
    <FeatureCard>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm leading-5 font-medium">Context Analysis</p>
        <span className={SOFT_CHIP}>
          <HugeiconsIcon icon={Search01Icon} className="size-3" />
          Verified
        </span>
      </div>
      <div className="mt-4 p-3 bg-secondary/50 rounded-xl">
        <p className="text-xs leading-5 text-foreground">
          "A person in a dark hoodie is lingering near the backdoor entrance for over 5 minutes."
        </p>
      </div>
    </FeatureCard>
  );
}

function WebSocketsPreview() {
  return (
    <FeatureCard>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm leading-5 font-medium">Live Feed</p>
        <span className={cn(SOFT_CHIP, "bg-red-500/10 text-red-500")}>
          Critical Alert
        </span>
      </div>
      <p className="mt-4 text-sm leading-6 text-muted-foreground">
        Connection established. Streaming telemetry at 190 FPS across 40 nodes.
      </p>
    </FeatureCard>
  );
}

const steps = [
  {
    step: "STEP 1",
    title: "Connect your cameras",
    desc: "Point the system to your existing RTSP streams. No proprietary hardware required.",
    art: "/marketing/cta-meadow.png",
    preview: <CameraPreview />,
  },
  {
    step: "STEP 2",
    title: "Filter out the noise",
    desc: "YOLOv8 Edge drops 98% of false positives instantly, sending only genuine anomalies to the VLM.",
    art: "/marketing/hero-panel.png",
    preview: <VLMPreview />,
  },
  {
    step: "STEP 3",
    title: "Get instant alerts",
    desc: "WebSockets deliver real time threat notifications the exact millisecond a danger is confirmed.",
    art: "/marketing/features/studio-blooms.png",
    preview: <WebSocketsPreview />,
  },
];

export function PostBridgeSteps() {
  return (
    <Section id="how-it-works" className="pt-16 pb-8">
      <div className="text-center mb-16">
        <h2 className="font-heading text-4xl font-medium tracking-tight md:text-5xl lg:text-6xl text-foreground">
          Three steps.
        </h2>
        <p className="mt-4 text-3xl font-medium tracking-tight text-muted-foreground md:text-4xl lg:text-5xl">
          Then you're fully secured.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8 max-w-7xl mx-auto">
        {steps.map((step, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="flex flex-col bg-secondary/50 rounded-[2rem] overflow-hidden border border-border/50"
          >
            <div className="relative h-64 w-full overflow-hidden rounded-t-[2rem]">
              <img
                src={step.art}
                alt=""
                className="absolute inset-0 h-full w-full object-cover"
              />
              {step.preview}
            </div>
            <div className="p-8 flex-1 flex flex-col">
              <span className="text-[0.65rem] font-bold tracking-widest text-muted-foreground uppercase mb-3">
                {step.step}
              </span>
              <h3 className="text-2xl font-medium tracking-tight text-foreground mb-3">
                {step.title}
              </h3>
              <p className="text-muted-foreground leading-relaxed text-sm">
                {step.desc}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </Section>
  );
}
