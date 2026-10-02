"use client";

import {
  Analytics01Icon,
  ArrowUp02Icon,
  BookOpen01Icon,
  CheckmarkCircle01Icon,
  CodeIcon,
  Coins01Icon,
  CrownIcon,
  HeadphonesIcon,
  Hospital01Icon,
  Layers01Icon,
  Leaf01Icon,
  Location01Icon,
  Mail01Icon,
  Megaphone01Icon,
  News01Icon,
  PaintBoardIcon,
  QuillWrite01Icon,
  Search01Icon,
  SparklesIcon,
  Target01Icon,
  Tick02Icon,
  ToolsIcon,
  Train01Icon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";

import { useCallback, useLayoutEffect, useRef, useState } from "react";

import {
  ScrollReveal,
  StaggerContainer,
  StaggerItem,
} from "@/components/landing/animation/ScrollReveal";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionHeading } from "@/components/landing/marketing/parts/sectionHeading";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

type Agent = {
  icon: typeof SparklesIcon;
  name: string;
  role: string;
  lead?: boolean;
};

type ApprovalItem = {
  id: string;
  title: string;
  description: string;
  tag: string;
  leadIcon: typeof SparklesIcon;
  assignees: string;
  actionLabel: string;
};

type ChatMessage = {
  id: string;
  role: "user" | "agent";
  text: string;
};

type Squad = {
  id: string;
  pill: string;
  label: string;
  count: string;
  image: string;
  blurb: string;
  agents: Agent[];
  time: string;
  model: string;
  prompt: string;
  deliverableCount: string;
  missionTarget: string;
  brief: string;
  diagnostic: {
    badge: string;
    text: string;
  };
  approvals: ApprovalItem[];
  quickReplies: string[];
  statusNote: string;
  userName: string;
  userImage?: string;
  thread: ChatMessage[];
};

const squads: Squad[] = [
  {
    id: "sitegpt",
    pill: "Stage 1",
    label: "Baseline Approach",
    count: "Center-pixel sampling",
    image: "/marketing/squad-canvas-hills.jpg",
    blurb:
      "A simple baseline using the bounding box center pixel to sample depth from the DepthAnything v2 output.",
    agents: [
      { icon: SparklesIcon, name: "Input", role: "Image + Intrinsics", lead: true },
      { icon: Search01Icon, name: "DepthAny v2", role: "Relative Depth" },
      { icon: Analytics01Icon, name: "Center Sampler", role: "Depth Aggregation" },
      { icon: CodeIcon, name: "Pinhole Math", role: "X, Z Estimate" }
    ],
    time: "Baseline",
    model: "DepthAnything v2",
    prompt: "Sample depth at bounding box center",
    deliverableCount: "MAE_Z ~18.5m",
    missionTarget: "Establish Baseline Error",
    brief:
      "Center-pixel sampling is fast but highly susceptible to noise, especially if the center pixel falls on the windshield (reflecting the sky) or the road behind a truck.",
    diagnostic: {
      badge: "Baseline Metrics",
      text: "Shows significant error on far and occluded vehicles due to single-pixel noise.",
    },
    approvals: [
      {
        id: "sitegpt-1",
        title: "Identify Failure Cases",
        description: "Windshield reflections and bounding box misalignments cause severe depth spikes.",
        tag: "Analysis",
        leadIcon: QuillWrite01Icon,
        assignees: "Evaluator",
        actionLabel: "View Failures",
      }
    ],
    quickReplies: ["View Method A", "See Metrics"],
    statusNote: "Baseline established",
    userName: "Evaluator",
    thread: [
      { id: "sitegpt-m1", role: "user", text: "Run Method A (Center Pixel)" },
      {
        id: "sitegpt-m2",
        role: "agent",
        text: "Baseline execution complete. MAE_Z is high on occluded targets.",
      },
    ],
  },
  {
    id: "govpitch",
    pill: "Stage 2",
    label: "Improved Method",
    count: "Robust Aggregation",
    image: "/marketing/squad-canvas-canyon.jpg",
    blurb:
      "Improved sampling strategy that aggregates the lower half of the bounding box using a trimmed median to avoid windshield reflections and background noise.",
    agents: [
      {
        icon: SparklesIcon,
        name: "Lower-Half BBox",
        role: "Masking",
        lead: true,
      },
      { icon: Coins01Icon, name: "Trimmed Median", role: "Outlier Rejection" },
      { icon: Hospital01Icon, name: "Vehicle Prior", role: "Width ~1.8m" },
    ],
    time: "Improved",
    model: "DepthAnything + Prior",
    prompt: "Apply trimmed median on lower bounding box",
    deliverableCount: "MAE_Z ~5.7m",
    missionTarget: "Improve Depth Reliability",
    brief:
      "By isolating the vehicle body (lower half) and discarding the top and bottom 10% depth values, we recover a highly stable depth estimate robust to occlusions.",
    diagnostic: {
      badge: "Meaningful Improvement",
      text: "Significant reduction in MAE_Z and P90 tail errors.",
    },
    approvals: [
      {
        id: "govpitch-1",
        title: "Geometric Verification",
        description:
          "Combine depth output with a geometric width prior (~1.8m) for scale recovery.",
        tag: "Geometry",
        leadIcon: Hospital01Icon,
        assignees: "Pinhole Model",
        actionLabel: "Verify Scale",
      },
    ],
    quickReplies: ["View Method C", "See Ablation"],
    statusNote: "Experiment successful",
    userName: "Evaluator",
    thread: [
      { id: "govpitch-m1", role: "user", text: "Apply trimmed median and vehicle prior" },
      {
        id: "govpitch-m2",
        role: "agent",
        text: "Method C complete. Substantial error reduction achieved.",
      },
    ],
  }
];

function ChatFace({
  name,
  image,
  icon,
}: {
  name: string;
  image?: string;
  icon?: Agent["icon"];
}) {
  return (
    <Avatar size="sm" className="overflow-hidden ring-2 ring-background">
      {image ? <AvatarImage src={image} alt="" /> : null}
      <AvatarFallback>
        {icon ? (
          <HugeiconsIcon icon={icon} size={12} className="size-3" />
        ) : (
          name.slice(0, 1)
        )}
      </AvatarFallback>
    </Avatar>
  );
}

function SquadChat({ squad }: { squad: Squad }) {
  const lead = squad.agents.find((agent) => agent.lead) ?? squad.agents[0];
  const userMessage = squad.thread.find((message) => message.role === "user");
  const agentMessage = squad.thread.find((message) => message.role === "agent");
  const approval = squad.approvals[0];

  return (
    <div className="relative z-10 flex w-full max-w-[21rem] flex-col overflow-hidden rounded-2xl border border-border/50 bg-background/95 shadow-2xl backdrop-blur-md">
      <div className="flex shrink-0 items-center gap-2 border-b border-border/60 px-3.5 py-2">
        <span className="flex shrink-0 items-center gap-1.5" aria-hidden>
          <span className="size-2 rounded-full bg-[#ff5f57]" />
          <span className="size-2 rounded-full bg-[#febc2e]" />
          <span className="size-2 rounded-full bg-[#28c840]" />
        </span>
        <p className="min-w-0 flex-1 truncate text-center font-mono text-[10px] text-muted-foreground">
          Mission Control · {squad.pill}
        </p>
        <span className="shrink-0 font-mono text-[10px] text-muted-foreground">
          {squad.time}
        </span>
      </div>

      <div className="flex shrink-0 items-center gap-2 px-3.5 pt-2.5 pb-2">
        <ChatFace name={lead.name} icon={lead.icon} />
        <div className="min-w-0 flex-1 leading-tight">
          <p className="truncate text-[13px] font-medium">{lead.name}</p>
          <p className="truncate text-[10px] text-muted-foreground">
            {lead.role}
          </p>
        </div>
        <Badge variant="secondary" className="shrink-0 font-mono text-[10px]">
          {squad.count}
        </Badge>
      </div>

      <div className="flex min-h-0 flex-col gap-2 px-3.5 py-2.5">
        {userMessage ? (
          <p className="max-w-[85%] self-end rounded-2xl rounded-br-md bg-primary px-2.5 py-1.5 text-xs leading-snug text-primary-foreground">
            {userMessage.text}
          </p>
        ) : null}
        {agentMessage ? (
          <p className="max-w-[85%] rounded-2xl rounded-bl-md border border-border/60 bg-card px-2.5 py-1.5 text-xs leading-snug shadow-sm">
            {agentMessage.text}
          </p>
        ) : null}

        {approval ? (
          <div className="flex items-center gap-2 rounded-xl border border-border/60 bg-card px-2.5 py-2 shadow-sm">
            <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-muted">
              <HugeiconsIcon
                icon={approval.leadIcon}
                size={13}
                className="size-3"
              />
            </span>
            <p className="min-w-0 flex-1 truncate text-xs font-medium">
              {approval.title}
            </p>
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[10px] font-medium text-primary-foreground">
              <HugeiconsIcon icon={Tick02Icon} size={11} className="size-2.5" />
              Approve
            </span>
          </div>
        ) : null}
      </div>

      <div className="shrink-0 border-t border-border/60 bg-background/60 px-3.5 py-2.5">
        <div className="flex items-center gap-2 rounded-full border border-border/70 bg-muted/50 py-1 pr-1 pl-2.5">
          <span className="min-w-0 flex-1 truncate text-[11px] text-muted-foreground">
            Reply to {lead.name}…
          </span>
          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <HugeiconsIcon icon={ArrowUp02Icon} size={13} className="size-3" />
          </span>
        </div>
      </div>
    </div>
  );
}

export function Squads() {
  const [activeId, setActiveId] = useState(squads[0].id);
  const [indicator, setIndicator] = useState({ left: 0, width: 0 });
  const [indicatorReady, setIndicatorReady] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const squad = squads.find((item) => item.id === activeId) ?? squads[0];

  const updateIndicator = useCallback(() => {
    const list = listRef.current;
    if (!list) return;
    const triggers = [
      ...list.querySelectorAll<HTMLElement>('[data-slot="tabs-trigger"]'),
    ];
    const active =
      triggers.find((tab) => tab.hasAttribute("data-active")) ??
      triggers[squads.findIndex((item) => item.id === activeId)];
    if (!active) return;
    const listBox = list.getBoundingClientRect();
    const tabBox = active.getBoundingClientRect();
    setIndicator({
      left: tabBox.left - listBox.left,
      width: tabBox.width,
    });
  }, [activeId]);

  useLayoutEffect(() => {
    updateIndicator();
    const frame = requestAnimationFrame(() => setIndicatorReady(true));
    const list = listRef.current;
    const observer =
      list && typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(updateIndicator)
        : null;
    if (list && observer) observer.observe(list);
    window.addEventListener("resize", updateIndicator);
    return () => {
      cancelAnimationFrame(frame);
      observer?.disconnect();
      window.removeEventListener("resize", updateIndicator);
    };
  }, [updateIndicator]);

  return (
    <Section id="squads" className="flex flex-col gap-12 md:gap-16">
      <ScrollReveal direction="up" distance={24}>
        <SectionHeading
          index={5}
          heading="Experiments"
          subheading="Proving improvements with ablations."
          description="Explore the different methodology stages evaluated on the development set."
        />
      </ScrollReveal>

      <ScrollReveal direction="up" distance={28} delay={0.1}>
        <Tabs
          value={squad.id}
          onValueChange={setActiveId}
          className="w-full gap-10 md:gap-12"
        >
          <div className="-mx-5 flex w-[calc(100%+2.5rem)] overflow-x-auto px-5 [scrollbar-width:none] sm:-mx-6 sm:w-[calc(100%+3rem)] sm:px-6 md:-mx-10 md:w-[calc(100%+5rem)] md:px-10 [&::-webkit-scrollbar]:hidden">
            <TabsList
              ref={listRef}
              className="relative h-auto group-data-horizontal/tabs:h-9 rounded-full px-1.5 py-1"
            >
              <span
                aria-hidden
                className="pointer-events-none absolute top-0.5 left-0 z-0 h-[calc(100%-4px)] rounded-full bg-background shadow-sm motion-reduce:transition-none"
                style={{
                  width: indicator.width,
                  transform: `translateX(${indicator.left}px)`,
                  opacity: indicator.width ? 1 : 0,
                  transition: indicatorReady
                    ? "transform 280ms cubic-bezier(0.32, 0.72, 0, 1), width 280ms cubic-bezier(0.32, 0.72, 0, 1)"
                    : "none",
                }}
              />
              {squads.map((item) => (
                <TabsTrigger
                  key={item.id}
                  value={item.id}
                  className="z-10 shrink-0 rounded-full px-4 py-1.5 md:px-5 data-active:bg-transparent dark:data-active:bg-transparent"
                >
                  {item.pill}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          <div className="grid w-full">
            {squads.map((item) => {
              const isActive = item.id === squad.id;

              return (
                <div
                  key={item.id}
                  className={cn(
                    "col-start-1 row-start-1 grid w-full items-stretch gap-8 lg:grid-cols-12 lg:gap-10",
                    isActive ? "z-10" : "invisible pointer-events-none",
                  )}
                  aria-hidden={!isActive}
                >
                  <div className="flex flex-col justify-between gap-6 lg:col-span-6">
                    <div className="flex flex-col gap-3 md:gap-3.5">
                      <div className="flex items-center gap-3">
                        <Badge
                          variant="outline"
                          className="gap-1.5 font-mono text-xs"
                        >
                          <span className="size-1.5 shrink-0 rounded-full bg-brand" />
                          {item.count}
                        </Badge>
                        <span className="text-xs font-medium tracking-eyebrow text-muted-foreground uppercase">
                          Active Edge Nodes
                        </span>
                      </div>
                      <h3 className="font-heading text-3xl font-medium leading-title tracking-title text-foreground md:text-4xl lg:text-5xl">
                        {item.label}
                      </h3>
                      <p className="max-w-xl text-base leading-body text-muted-foreground md:text-lg">
                        {item.blurb}
                      </p>
                    </div>

                    <div className="flex flex-col gap-3.5 border-t border-dashed pt-6">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium tracking-eyebrow text-muted-foreground uppercase">
                          Active AI Modules
                        </span>
                        <span className="font-mono text-xs text-muted-foreground">
                          {item.agents.length} modules
                        </span>
                      </div>

                      <StaggerContainer
                        staggerDelay={0.08}
                        delayChildren={0.04}
                        className="grid grid-cols-2 gap-2.5 sm:grid-cols-3"
                      >
                        {item.agents.map((agent) => (
                          <StaggerItem
                            key={agent.name}
                            direction="up"
                            distance={16}
                            duration={0.6}
                            className="flex items-center gap-2.5 rounded-xl border border-dashed bg-card/60 p-2.5 transition-colors hover:border-foreground/20 hover:bg-card"
                          >
                            <span className="flex size-7.5 shrink-0 items-center justify-center rounded-lg border border-dashed bg-background text-foreground shadow-2xs">
                              <HugeiconsIcon
                                icon={agent.icon}
                                className={cn(
                                  "size-3.5",
                                  agent.lead
                                    ? "text-brand"
                                    : "text-foreground/80",
                                )}
                              />
                            </span>
                            <div className="flex min-w-0 flex-1 flex-col leading-tight">
                              <div className="flex items-center justify-between gap-1">
                                <span className="truncate text-xs font-medium text-foreground">
                                  {agent.name}
                                </span>
                                {agent.lead ? (
                                  <HugeiconsIcon
                                    icon={CrownIcon}
                                    className="size-3 shrink-0 text-brand"
                                  />
                                ) : null}
                              </div>
                              <span className="truncate text-[10px] text-muted-foreground">
                                {agent.role}
                              </span>
                            </div>
                          </StaggerItem>
                        ))}
                      </StaggerContainer>

                      <div className="mt-2 flex items-center gap-2.5 border-t border-dashed pt-4 text-xs text-muted-foreground">
                        <span className="flex size-5 shrink-0 items-center justify-center rounded-full border border-dashed">
                          <HugeiconsIcon
                            icon={Tick02Icon}
                            className="size-3 text-brand"
                          />
                        </span>
                        <span>
                          No alerts escalated without verification ·{" "}
                          <strong className="font-medium text-foreground">
                            {item.statusNote}
                          </strong>
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="lg:col-span-6">
                    <div className="relative flex h-full min-h-[20rem] w-full items-center justify-center overflow-hidden rounded-2xl px-5 py-8 sm:min-h-[22rem] sm:px-8 md:min-h-[24rem] md:rounded-3xl">
                      <img
                        key={item.image}
                        src={item.image}
                        alt=""
                        className="absolute inset-0 h-full w-full object-cover object-center"
                      />
                      <div
                        aria-hidden
                        className="pointer-events-none absolute inset-0 bg-gradient-to-t from-background/35 via-transparent to-background/10"
                      />
                      <div className="relative flex w-full justify-center">
                        <SquadChat squad={item} />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Tabs>
      </ScrollReveal>
    </Section>
  );
}
