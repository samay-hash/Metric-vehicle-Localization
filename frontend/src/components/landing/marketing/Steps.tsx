
import {
  ArrowUpRight01Icon,
  BubbleChatIcon,
  CreditCardIcon,
  Share01Icon,
  Tick02Icon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { Link } from "react-router-dom";

import {
  ScrollReveal,
  StaggerContainer,
  StaggerItem,
} from "@/components/landing/animation/ScrollReveal";
import { Section } from "@/components/landing/marketing/parts/section";
import {
  IndexBars,
  SectionHeading,
} from "@/components/landing/marketing/parts/sectionHeading";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const steps = [
  {
    title: "Connect",
    body: "Point the system to your existing RTSP streams. No proprietary hardware required.",
    icon: CreditCardIcon,
  },
  {
    title: "Detect",
    body: "YOLOv8 Edge filters out 98% of the noise, ensuring only relevant activities trigger further analysis.",
    icon: BubbleChatIcon,
  },
  {
    title: "Investigate",
    body: "Local LLaVA VLM analyzes the flagged frames, understanding real-world intent securely on premise.",
    icon: Tick02Icon,
  },
  {
    title: "Act",
    body: "WebSockets deliver instant sub-100ms alerts, turning feeds red the exact moment a threat is confirmed.",
    icon: Share01Icon,
  },
];

export function Steps() {
  return (
    <Section
      id="steps"
      className="flex flex-col gap-10 md:gap-14 items-center"
    >
      <ScrollReveal direction="up" distance={20} className="w-full">
        <SectionHeading
          index={3}
          heading="How it works"
          subheading="Passive cameras to active intelligence."
          description="A fully automated pipeline from raw pixels to verified threat alerts."
          className="max-w-2xl mx-auto text-center items-center"
        >
          <Link to="/dashboard" className={buttonVariants({ size: "lg" })}>
            Enter Command Center
            <HugeiconsIcon icon={ArrowUpRight01Icon} data-icon="inline-end" />
          </Link>
        </SectionHeading>
      </ScrollReveal>

      <StaggerContainer
        staggerDelay={0.14}
        delayChildren={0.08}
        amount={0.15}
        className="grid w-full grid-cols-1 md:grid-cols-2 gap-4 md:gap-6"
      >
        {steps.map((step, index) => (
          <StaggerItem key={step.title} direction="up" distance={24}>
            <Card className="h-full justify-between p-5 sm:min-h-52 sm:p-7 md:min-h-56 md:p-8">
              <CardHeader className="flex items-center justify-between gap-4 px-0">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-dashed bg-background">
                  <HugeiconsIcon icon={step.icon} />
                </span>
                <CardAction>
                  <IndexBars index={index + 1} total={steps.length} />
                </CardAction>
              </CardHeader>
              <CardContent className="flex flex-col gap-2 px-0">
                <CardTitle className="text-2xl font-medium">
                  {step.title}
                </CardTitle>
                <CardDescription className="text-sm leading-body text-pretty md:text-base">
                  {step.body}
                </CardDescription>
              </CardContent>
            </Card>
          </StaggerItem>
        ))}
      </StaggerContainer>
    </Section>
  );
}
