import { ArrowUpRight01Icon, Tick02Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { Link } from "react-router-dom";

import { ScrollReveal } from "@/components/landing/animation/ScrollReveal";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionHeading } from "@/components/landing/marketing/parts/sectionHeading";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const features = [
  "Pretrained DepthAnything v2 (MIT License)",
  "No external API — fully local inference",
  "CPU-compatible, GPU-optional",
  "Ablation study with 3 methods compared",
  "MAE_Z, AbsRel_Z, P90, MAE_X reported",
  "10+ annotated visualisations included",
];

function CheckMark() {
  return (
    <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-dashed">
      <HugeiconsIcon icon={Tick02Icon} className="size-4 text-brand" />
    </span>
  );
}

export function Pricing() {
  return (
    <Section id="pricing" className="flex flex-col gap-12 md:gap-16">
      <ScrollReveal direction="up" distance={24}>
        <SectionHeading
          index={8}
          heading="Submission"
          subheading="Open Source. Reproducible."
          description="Full pipeline, experiments, and failure analysis included."
        />
      </ScrollReveal>

      <ScrollReveal direction="up" distance={28} delay={0.1}>
        <Card className="grid w-full min-w-0 gap-0 py-0 lg:grid-cols-2">
          <div className="flex flex-col justify-between gap-8 p-5 sm:p-8 md:p-10 lg:p-12">
            <CardHeader className="flex flex-col gap-0 px-0">
              <p className="text-xs font-medium tracking-eyebrow text-muted-foreground uppercase">
                Challenge
              </p>
              <div className="mt-3 flex items-baseline gap-2 md:mt-3.5">
                <CardTitle className="font-heading text-5xl leading-display tracking-display sm:text-6xl md:text-7xl">
                  $0
                </CardTitle>
                <span className="text-base text-muted-foreground md:text-lg">
                  / forever
                </span>
              </div>
              <CardDescription className="mt-2.5 max-w-md text-base leading-body md:mt-3 md:text-lg">
                Completely offline prediction pipeline with reproducible experiments and clear geometry-driven logic.
              </CardDescription>
            </CardHeader>
            <CardFooter className="flex-col items-start gap-3.5 px-0">
              <Link
                to="/dashboard"
                className={buttonVariants({ size: "lg" })}
              >
                View Dashboard
                <HugeiconsIcon
                  icon={ArrowUpRight01Icon}
                  data-icon="inline-end"
                />
              </Link>
              <p className="max-w-sm text-sm text-muted-foreground text-pretty">
                Inspect the pipeline code, run the evaluation command, and review the failure cases in visualisations.
              </p>
            </CardFooter>
          </div>

          <div className="flex flex-col justify-center border-t border-dashed p-5 sm:p-8 lg:border-t-0 lg:border-l md:p-10 lg:p-12">
            <ul className="flex flex-col gap-3.5 md:gap-4">
              {features.map((feature) => (
                <li
                  key={feature}
                  className="flex items-start gap-3 text-sm md:text-base"
                >
                  <CheckMark />
                  {feature}
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </ScrollReveal>
    </Section>
  );
}
