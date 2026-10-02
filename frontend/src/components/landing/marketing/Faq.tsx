
import { ArrowUpRight01Icon, HeadphonesIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";

import {
  ScrollReveal,
  StaggerContainer,
  StaggerItem,
} from "@/components/landing/animation/ScrollReveal";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionHeading } from "@/components/landing/marketing/parts/sectionHeading";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const faqs = [
  {
    question: "How do you estimate depth without LiDAR?",
    answer: "Using a pretrained monocular depth model (DepthAnything v2) and camera intrinsics to recover metric scale.",
  },
  {
    question: "How is X (lateral position) calculated?",
    answer: "Using pinhole camera geometry: X = (u - cx) * Z / fx",
  },
  {
    question: "What is 'confidence' here?",
    answer: "It is the expected metric reliability based on bounding box size, depth variance, distance, and edge proximity — not just the model's softmax score.",
  },
  {
    question: "Why use median instead of mean for depth?",
    answer: "Median is robust to bad pixels (like sky reflections or occluded regions in the bounding box). Experiment B showed a significant reduction in MAE_Z.",
  },
  {
    question: "How did you improve over the baseline?",
    answer: "Baseline: center pixel depth. Improved: lower-half bounding box median + camera geometry + vehicle size prior.",
  },
  {
    question: "Is a GPU required?",
    answer: "No. It is CPU-compatible. The pipeline runs at ~50ms per image on a CPU, taking ~20 seconds total for 250 images.",
  },
];

export function Faq() {
  return (
    <Section
      id="faq"
      className="grid gap-10 lg:grid-cols-2 lg:grid-rows-[auto_1fr] lg:gap-x-16 xl:gap-x-20"
    >
      <ScrollReveal direction="up" distance={20}>
        <SectionHeading
          index={9}
          heading="Technical FAQ"
          subheading="Questions?"
          description="Understanding the core choices behind the computer vision pipeline."
          className="max-w-md"
        />
      </ScrollReveal>

      <Accordion
        multiple={false}
        defaultValue={[faqs[0].question]}
        className="contents"
      >
        <StaggerContainer
          staggerDelay={0.14}
          delayChildren={0.08}
          amount={0.15}
          className="flex w-full flex-col gap-3.5 lg:row-span-2 md:gap-4"
        >
          {faqs.map((faq) => (
            <StaggerItem key={faq.question} direction="up" distance={24}>
              <AccordionItem value={faq.question}>
                <AccordionTrigger>{faq.question}</AccordionTrigger>
                <AccordionContent>{faq.answer}</AccordionContent>
              </AccordionItem>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </Accordion>

      <ScrollReveal
        direction="up"
        distance={20}
        delay={0.15}
        className="w-full max-w-xs lg:self-end"
      >
        <Card
          size="sm"
          className="w-full items-center justify-center p-6 text-center md:p-7"
        >
          <CardHeader className="w-full justify-items-center gap-1.5 px-0">
            <span className="flex size-10 items-center justify-center rounded-lg border border-dashed bg-background">
              <HugeiconsIcon icon={HeadphonesIcon} />
            </span>
            <CardTitle className="mt-1">More questions?</CardTitle>
            <CardDescription>Reach out anytime.</CardDescription>
          </CardHeader>
          <CardFooter className="w-full mt-2 px-0">
            <a
              href="#"
              className={buttonVariants({ className: "w-full" })}
            >
              Email Candidate
              <HugeiconsIcon icon={ArrowUpRight01Icon} data-icon="inline-end" />
            </a>
          </CardFooter>
        </Card>
      </ScrollReveal>
    </Section>
  );
}
