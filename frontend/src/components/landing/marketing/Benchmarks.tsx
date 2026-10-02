import {
  CpuIcon,
  FlashIcon,
  Target01Icon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";

import {
  ScrollReveal,
  StaggerContainer,
  StaggerItem,
} from "@/components/landing/animation/ScrollReveal";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionHeading } from "@/components/landing/marketing/parts/sectionHeading";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const metrics = [
  {
    title: "Scalability",
    stat: "190 FPS",
    substat: "5,720 frames / 30s",
    body: "CPU load stabilized at just 26.4%. The system leaves massive compute headroom and can easily handle 30-40 cameras concurrently on a single node.",
    icon: CpuIcon,
  },
  {
    title: "Latency",
    stat: "5.2 ms",
    substat: "Per-frame inference",
    body: "The baseline YOLO real time tracking filters out visual noise instantly, processing city traffic at ultra-low latency.",
    icon: FlashIcon,
  },
  {
    title: "Accuracy",
    stat: "94%",
    substat: "Contextual Accuracy",
    body: "True anomalies are analyzed asynchronously by our Local VLM, verifying real-world threat intent in ~1.5s securely on premise.",
    icon: Target01Icon,
  },
];

export function Benchmarks() {
  return (
    <Section id="benchmarks" className="flex flex-col gap-12 md:gap-16">
      <ScrollReveal direction="up" distance={24}>
        <SectionHeading
          index={5}
          heading="Performance Benchmarks"
          subheading="Built for massive scale."
          description="Real-world performance data from our dual layer AI pipeline running on edge hardware."
        />
      </ScrollReveal>

      <StaggerContainer
        staggerDelay={0.14}
        delayChildren={0.08}
        amount={0.15}
        className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8"
      >
        {metrics.map((metric) => (
          <StaggerItem key={metric.title} direction="up" distance={24}>
            <Card className="h-full flex flex-col justify-between p-6 sm:p-8 overflow-hidden relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-brand/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              
              <CardHeader className="flex flex-col gap-4 px-0 pt-0 pb-6 border-b border-dashed border-border/60">
                <div className="flex items-center justify-between">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-dashed bg-background shadow-2xs">
                    <HugeiconsIcon icon={metric.icon} className="size-5 text-brand" />
                  </span>
                  <span className="text-xs font-medium tracking-eyebrow text-muted-foreground uppercase">
                    {metric.title}
                  </span>
                </div>
                
                <div className="flex flex-col gap-1">
                  <CardTitle className="font-heading text-4xl leading-title font-medium tracking-title lg:text-5xl">
                    {metric.stat}
                  </CardTitle>
                  <span className="font-mono text-sm text-brand font-medium">
                    {metric.substat}
                  </span>
                </div>
              </CardHeader>
              
              <CardContent className="px-0 pt-6 pb-0 flex-1">
                <p className="text-base leading-body text-muted-foreground text-pretty">
                  {metric.body}
                </p>
              </CardContent>
            </Card>
          </StaggerItem>
        ))}
      </StaggerContainer>
    </Section>
  );
}
