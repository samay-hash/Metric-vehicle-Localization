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
  type Variants,
} from "motion/react";
import { useRef } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { LiquidMetalButton } from "@/components/ui/liquid-metal-button";
import { Card, CardContent } from "@/components/ui/card";
import { PLATFORM_ICON, platforms } from "./platforms";
import { ART_FILTER, OVERLINE } from "./rhythm";
import Section from "./Section";

const agents = [
  { icon: "lucide:shield-alert", color: "#ef4444", label: "Security" },
  { icon: "carbon:video", color: "#6b7280", label: "CCTV" },
  { icon: "lucide:message-square", color: "#3b82f6", label: "Chat" },
  { icon: "devicon:python", color: "#3776AB", label: "Python" },
  { icon: "devicon:pytorch", color: "#EE4C2C", label: "PyTorch" },
  { icon: "simple-icons:docker", color: "#2496ED", label: "Docker" },
];

const EASE = "easeOut" as const;

const stack: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};

export function PostBridgeHero() {
  const reduceMotion = useReducedMotion();
  const stageRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: stageRef,
    offset: ["start start", "end start"],
  });
  const stageY = useTransform(
    scrollYProgress,
    [0, 1],
    reduceMotion ? [0, 0] : [0, 56],
    { ease: easeOut },
  );

  const rise: Variants = {
    hidden: { opacity: 0, y: reduceMotion ? 0 : 16 },
    show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: EASE } },
  };

  return (
    <Section className="overflow-hidden" containerClassName="relative pt-64 sm:pt-80 md:pt-96 lg:pt-[240px]">
      <motion.div
        initial="hidden"
        animate="show"
        variants={stack}
        className="relative mx-auto mt-4 md:mt-6 lg:mt-8 w-full min-w-0 max-w-5xl text-center"
      >
        <motion.div
          variants={rise}
          className="flex flex-wrap items-center justify-center gap-3.5 md:gap-4"
        >
          {agents.map((a) => (
            <span
              key={a.label}
              aria-label={a.label}
              title={a.label}
              className="inline-flex cursor-pointer items-center justify-center opacity-90 transition-all duration-200 hover:scale-110 hover:opacity-100"
            >
              <Icon
                icon={a.icon}
                className="size-5 md:size-6"
                style={{ color: a.color }}
              />
            </span>
          ))}
        </motion.div>

        <motion.h1
          variants={rise}
          className="font-heading mx-auto mt-6 w-full min-w-0 max-w-4xl text-[2rem] leading-[1.04] font-semibold tracking-[-0.035em] text-pretty text-foreground sm:text-[2.5rem] sm:text-balance md:mt-7 md:max-w-none md:text-[3.25rem] md:leading-[1.02] lg:text-[3.75rem] xl:text-[4.25rem]"
        >
          Metric Vehicle Localization
          <span className="block sm:whitespace-nowrap">
            <span className="text-muted-foreground font-normal">from a</span>{" "}
            <span className="font-normal text-muted-foreground">
              single RGB image
            </span>
          </span>
        </motion.h1>

        <motion.p
          variants={rise}
          className="mx-auto mt-5 max-w-xl text-[1.0625rem] leading-8 text-pretty text-muted-foreground md:mt-6 md:text-[1.125rem]"
        >
          Estimate exact 3D vehicle positions using monocular depth, camera intrinsics, and robust geometry. No LiDAR required.
        </motion.p>

        <motion.div
          variants={rise}
          className="mt-9 flex justify-center md:mt-10"
        >
          <LiquidMetalButton
            size="md"
            borderWidth={2}
            className="w-full sm:w-auto [&_svg]:transition-transform [&_svg]:duration-200 hover:[&_svg]:translate-x-0.5"
            metalConfig={{ speed: 0.5, colorBack: "#10b981", colorTint: "#34d399" }}
          >
            <span className="flex items-center gap-2">
              View Pipeline
              <HugeiconsIcon icon={ArrowRight01Icon} className="size-5" />
            </span>
          </LiquidMetalButton>
        </motion.div>



        <motion.div
          variants={rise}
          className="mt-9 flex flex-wrap items-center justify-center gap-x-3 gap-y-2 md:mt-10"
        >
          <div className="flex -space-x-2">
            <Avatar className="size-8 border-2 border-background">
              <AvatarImage src="/marketing/founders/bhanu.jpg" alt="Security Chief" />
              <AvatarFallback className="text-xs">AK</AvatarFallback>
            </Avatar>
            <Avatar className="size-8 border-2 border-background">
              <AvatarImage src="/marketing/founders/bhanu.jpg" alt="Security Director" />
              <AvatarFallback className="text-xs">ND</AvatarFallback>
            </Avatar>
            <Avatar className="size-8 border-2 border-background">
              <AvatarImage src="/marketing/founders/bhanu.jpg" alt="Admin" />
              <AvatarFallback className="text-xs">AB</AvatarFallback>
            </Avatar>
          </div>
          <span className="text-sm leading-5 font-medium text-foreground">
            Built for <span className="font-semibold">Roostr</span>{" "}
            <span className="font-normal text-muted-foreground">
              CV Engineering Challenge
            </span>
          </span>
        </motion.div>
      </motion.div>

      <motion.div
        ref={stageRef}
        style={{ y: stageY }}
        initial={{ opacity: 0, y: reduceMotion ? 0 : 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.35, ease: EASE }}
        className="relative mx-auto -mt-4 w-full md:-mt-4 lg:-mt-4 xl:-mt-2"
      >
        <div className="relative overflow-hidden rounded-panel px-4 py-8 sm:px-8 sm:py-10 md:px-12 md:py-12 lg:px-16 lg:py-16 xl:px-20 xl:pt-20 xl:pb-10">
          <Card className="relative min-w-0 gap-0 overflow-hidden bg-card/20 rounded-card border border-border/50 bg-card py-0 shadow-[0_24px_64px_-20px_rgba(24,24,27,0.35)] md:rounded-panel md:shadow-[0_28px_72px_-24px_rgba(24,24,27,0.38)] lg:rounded-[1.75rem]">
            <CardContent className="p-0">
              <img
                src="/landingdash.png"
                alt="Sentinel AI dashboard"
                className="h-auto w-full"
              />
            </CardContent>
          </Card>
        </div>
      </motion.div>
    </Section>
  );
}
