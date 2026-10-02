import {
  File01Icon,
  LockIcon,
  Mail01Icon,
  Search01Icon,
  SparklesIcon,
  Tick02Icon,
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

const features = [
  {
    eyebrow: "Depth Estimation",
    title: "Monocular Metric Depth",
    body: "Predict dense relative depth from single RGB images using foundation models, scaled into metric distance using camera intrinsics.",
    points: [
      "DepthAnything v2 foundation model",
      "Robust scale recovery via geometric priors",
      "Per-pixel depth maps without LiDAR",
    ],
    image: "/marketing/hero-canvas.jpg",
    imagePosition: "object-[center_40%]",
    overlay: <CloudComputerMockup />,
  },
  {
    eyebrow: "Spatial Mathematics",
    title: "Pinhole Camera Geometry",
    body: "Translate 2D image coordinates into 3D world space using exact camera calibration parameters.",
    points: [
      "Focal length (fx, fy) based unprojection",
      "Principal point (cx, cy) offset handling",
      "X = (u - cx) * Z / fx geometric conversion",
    ],
    image: "/marketing/squad-canvas-hills.jpg",
    imagePosition: "object-[70%_55%]",
    overlay: <AccessLoginsMockup />,
  },
  {
    eyebrow: "Data Cleaning",
    title: "Robust Depth Aggregation",
    body: "Avoid noisy pixel artifacts. Aggregate depth values smartly across vehicle bounding boxes.",
    points: [
      "Lower-half bounding box sampling",
      "Trimmed median to discard top 10% outliers",
      "Significant MAE reduction over center-pixel sampling",
    ],
    image: "/marketing/squad-canvas-waves.jpg",
    imagePosition: "object-[40%_70%]",
    overlay: <InboxMockup />,
  },
  {
    eyebrow: "Uncertainty Modeling",
    title: "Confidence Calibration",
    body: "Output metric reliability scores based on geometric and physical constraints, not just neural network logits.",
    points: [
      "Distance-weighted decay",
      "Bounding box pixel-density scoring",
      "Edge-proximity and occlusion penalties",
    ],
    image: "/marketing/squad-canvas-canyon.jpg",
    imagePosition: "object-[30%_60%]",
    overlay: <ParallelThreadsMockup />,
  },
];

function CheckMark() {
  return (
    <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-dashed">
      <HugeiconsIcon icon={Tick02Icon} className="size-4 text-brand" />
    </span>
  );
}

function MockupShell({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-[21rem] overflow-hidden rounded-2xl border border-border/50 bg-background/95 shadow-2xl backdrop-blur-md">
      {children}
    </div>
  );
}

function AgentMark({ icon, brand }: { icon: AgentIcon; brand?: boolean }) {
  return (
    <span className="flex size-6 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground">
      <HugeiconsIcon
        icon={icon}
        className={cn("size-3", brand ? "text-brand" : "text-foreground/80")}
      />
    </span>
  );
}

function CloudComputerMockup() {
  const files = [
    { name: "invoices_q3.pdf", status: "Saved" },
    { name: "retention_cohorts.csv", status: "Downloading" },
  ];

  return (
    <MockupShell>
      <div className="flex items-center gap-2 border-b border-border/60 px-3.5 py-2">
        <div className="flex shrink-0 items-center gap-1.5">
          <span className="size-2 rounded-full bg-[#ff5f57]" />
          <span className="size-2 rounded-full bg-[#febc2e]" />
          <span className="size-2 rounded-full bg-[#28c840]" />
        </div>
        <div className="flex min-w-0 flex-1 items-center justify-center gap-1.5 rounded-md bg-muted/60 px-2 py-1 font-mono text-[10px] text-muted-foreground">
          <HugeiconsIcon
            icon={LockIcon}
            className="size-2.5 shrink-0 text-brand"
          />
          <span className="truncate font-mono">app.chartmogul.com/exports</span>
        </div>
      </div>

      <div className="flex flex-col gap-2.5 px-3.5 py-2.5">
        <div>
          <div className="flex items-center justify-between gap-2 text-[11px]">
            <span className="font-medium">This week's invoices</span>
            <span className="font-mono text-muted-foreground">9 of 12</span>
          </div>
          <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-muted">
            <div className="h-full w-3/4 rounded-full bg-brand" />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          {files.map((file) => (
            <div
              key={file.name}
              className="flex items-center gap-2 text-[11px]"
            >
              <HugeiconsIcon
                icon={File01Icon}
                className="size-3 shrink-0 text-muted-foreground"
              />
              <span className="min-w-0 flex-1 truncate font-mono text-[10px]">
                {file.name}
              </span>
              <span
                className={cn(
                  "shrink-0 text-[10px]",
                  file.status === "Saved"
                    ? "text-muted-foreground"
                    : "text-brand",
                )}
              >
                {file.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </MockupShell>
  );
}

function AccessLoginsMockup() {
  const accounts = [
    {
      agent: "Jarvis",
      icon: SparklesIcon,
      app: "ChartMogul",
      status: "Signed in",
    },
    {
      agent: "Fury",
      icon: Search01Icon,
      app: "Search Console",
      status: "Signed in",
    },
    { agent: "Pepper", icon: Mail01Icon, app: "Gmail", status: "Signed in" },
  ];

  return (
    <MockupShell>
      <div className="flex items-center justify-between px-3.5 py-2">
        <p className="text-[13px] font-medium">Logins</p>
        <p className="font-mono text-[10px] text-muted-foreground">
          One session each
        </p>
      </div>

      <div className="flex flex-col divide-y divide-border border-t border-border">
        {accounts.map((account) => (
          <div
            key={account.agent}
            className="flex items-center gap-2 px-3.5 py-2"
          >
            <AgentMark icon={account.icon} brand={account.agent === "Jarvis"} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-[11px] font-medium">
                {account.agent}
              </p>
              <p className="truncate text-[10px] text-muted-foreground">
                {account.app}
              </p>
            </div>
            <span className={cn("shrink-0 text-[10px] text-brand")}>
              {account.status}
            </span>
          </div>
        ))}
      </div>
    </MockupShell>
  );
}

function InboxMockup() {
  const emails = [
    {
      from: "Maya Patel",
      subject: "Pricing page finally clicked",
      agent: "Pepper",
    },
    { from: "ChartMogul", subject: "Export ready: invoices", agent: "Jarvis" },
  ];

  return (
    <MockupShell>
      <div className="flex items-center justify-between px-3.5 py-2">
        <p className="text-[13px] font-medium">Inbox</p>
        <p className="font-mono text-[10px] text-muted-foreground">2 new</p>
      </div>

      <div className="flex flex-col divide-y divide-border border-t border-border">
        {emails.map((mail) => (
          <div
            key={mail.subject}
            className="flex items-center gap-2 px-3.5 py-2"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-[11px] font-medium">{mail.from}</p>
              <p className="truncate text-[10px] text-muted-foreground">
                {mail.subject}
              </p>
            </div>
            <span className="shrink-0 rounded-full border border-border/70 px-2 py-0.5 text-[10px] text-muted-foreground">
              {mail.agent}
            </span>
          </div>
        ))}
      </div>
    </MockupShell>
  );
}

function ParallelThreadsMockup() {
  const threads = [
    {
      title: "Outreach",
      detail: "Batch 4 of 10 is going out.",
      status: "Running",
    },
    { title: "Pricing audit", detail: "Three tables in.", status: "Streaming" },
  ];

  return (
    <MockupShell>
      <div className="flex items-center justify-between px-3.5 py-2">
        <p className="text-[13px] font-medium">Jarvis</p>
        <p className="font-mono text-[10px] text-muted-foreground">2 threads</p>
      </div>

      <div className="flex flex-col divide-y divide-border border-t border-border">
        {threads.map((thread) => (
          <div
            key={thread.title}
            className="flex items-center gap-2 px-3.5 py-2"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-[11px] font-medium">{thread.title}</p>
              <p className="truncate text-[10px] text-muted-foreground">
                {thread.detail}
              </p>
            </div>
            <span className={cn("shrink-0 text-[10px] text-brand")}>
              {thread.status}
            </span>
          </div>
        ))}
      </div>
    </MockupShell>
  );
}

function FeatureVisual({
  image,
  imagePosition,
  overlay,
  className,
}: {
  image: string;
  imagePosition: string;
  overlay: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative h-full min-h-64 min-w-0 overflow-hidden sm:min-h-80 lg:min-h-[32rem]",
        className,
      )}
    >
      <img
        src={image}
        alt=""
        
        sizes="(min-width: 1024px) 40vw, 92vw"
        className={cn("object-cover", imagePosition)}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-t from-background/25 via-transparent to-background/10"
      />
      <div className="absolute inset-x-4 top-1/2 w-auto -translate-y-1/2 sm:inset-x-6 md:inset-x-8 lg:inset-x-12">
        {overlay}
      </div>
    </div>
  );
}

export function Features() {
  return (
    <Section id="features" className="flex flex-col gap-12 md:gap-16">
      <ScrollReveal direction="up" distance={24}>
        <SectionHeading
          index={2}
          heading="Core Pipeline"
          subheading="A Robust Computer Vision Approach."
          description="A multi-stage pipeline designed for precise geometric localization without depth sensors or point clouds."
        />
      </ScrollReveal>

      {/* Shared sticky stack container: cards are direct siblings so they stick and stack together */}
      <div className="relative flex w-full min-w-0 flex-col [--stack-top:6rem] sm:[--stack-top:7rem] md:[--stack-top:8rem]">
        {features.map((feature, index) => {
          const imageOnLeft = index % 2 === 1;
          const isLast = index === features.length - 1;

          return (
            <div
              key={feature.title}
              className={cn(
                "w-full lg:sticky",
                !isLast && "mb-6 sm:mb-8 md:mb-12",
              )}
              style={{
                top: `calc(var(--stack-top) + ${index * 1.25}rem)`,
                zIndex: index + 1,
              }}
            >
              <Card className="grid w-full min-w-0 gap-0 py-0 lg:min-h-[34rem] lg:grid-cols-2">
                <div className="flex flex-col justify-between gap-8 p-5 sm:p-8 md:p-10 lg:p-12">
                  <CardHeader className="flex flex-col gap-0 px-0">
                    <p className="text-xs font-medium tracking-eyebrow text-muted-foreground uppercase">
                      {feature.eyebrow}
                    </p>
                    <CardTitle className="mt-3 font-heading text-2xl leading-title tracking-title md:mt-3.5 lg:text-4xl">
                      {feature.title}
                    </CardTitle>
                    <CardDescription className="mt-2.5 max-w-md text-base leading-body md:mt-3 md:text-lg">
                      {feature.body}
                    </CardDescription>
                  </CardHeader>
                  <CardFooter className="px-0">
                    <ul className="flex flex-col gap-3.5 md:gap-4">
                      {feature.points.map((point) => (
                        <li
                          key={point}
                          className="flex items-start gap-3 text-sm md:text-base"
                        >
                          <CheckMark />
                          {point}
                        </li>
                      ))}
                    </ul>
                  </CardFooter>
                </div>
                <FeatureVisual
                  image={feature.image}
                  imagePosition={feature.imagePosition}
                  overlay={feature.overlay}
                  className={imageOnLeft ? "lg:order-first" : undefined}
                />
              </Card>
            </div>
          );
        })}
      </div>
    </Section>
  );
}
