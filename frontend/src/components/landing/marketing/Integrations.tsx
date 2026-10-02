
import {
  type ComponentType,
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import {
  ScrollReveal,
  StaggerContainer,
  StaggerItem,
} from "@/components/landing/animation/ScrollReveal";
import {
  ClaudeIcon,
  CodexIcon,
  DiscordIcon,
  DropboxIcon,
  FigmaIcon,
  GitHubIcon,
  GmailIcon,
  GoogleCalendarIcon,
  GoogleDriveIcon,
  GoogleSheetsIcon,
  GrokIcon,
  HubSpotIcon,
  LinkedInIcon,
  NotionIcon,
  RedditIcon,
  SlackIcon,
  StripeIcon,
  TrelloIcon,
  WhatsAppIcon,
  ZoomIcon,
} from "@/components/landing/marketing/integration-icons";
import { Icon } from "@iconify/react";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionHeading } from "@/components/landing/marketing/parts/sectionHeading";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Category = "all" | "databases" | "deployment" | "storage" | "ai";

type Integration = {
  name: string;
  body: string;
  icon: ComponentType<{ className?: string }>;
  category: Exclude<Category, "all">;
};

const categories: { id: Category; label: string }[] = [
  { id: "all", label: "All" },
  { id: "databases", label: "Aggregation & Math" },
  { id: "deployment", label: "Geometry Engine" },
  { id: "storage", label: "Data I/O" },
  { id: "ai", label: "Depth Models" },
];


const VahanIcon = ({ className }: { className?: string }) => <Icon icon="lucide:car" className={className} />;
const PoliceIcon = ({ className }: { className?: string }) => <Icon icon="lucide:shield-check" className={className} />;
const FingerprintIcon = ({ className }: { className?: string }) => <Icon icon="lucide:fingerprint" className={className} />;
const CameraIcon = ({ className }: { className?: string }) => <Icon icon="lucide:cctv" className={className} />;
const ServerIcon = ({ className }: { className?: string }) => <Icon icon="lucide:server" className={className} />;
const HardDriveIcon = ({ className }: { className?: string }) => <Icon icon="lucide:hard-drive" className={className} />;
const BrainIcon = ({ className }: { className?: string }) => <Icon icon="lucide:brain" className={className} />;
const ScanIcon = ({ className }: { className?: string }) => <Icon icon="lucide:scan" className={className} />;
const CloudIcon = ({ className }: { className?: string }) => <Icon icon="lucide:cloud" className={className} />;
const CpuIcon = ({ className }: { className?: string }) => <Icon icon="lucide:cpu" className={className} />;
const integrations: Integration[] = [
  {
    name: "DepthAnything v2",
    body: "State-of-the-art monocular depth estimation foundation model.",
    icon: BrainIcon,
    category: "ai",
  },
  {
    name: "ZoeDepth",
    body: "Metric depth estimation model used for baseline comparisons.",
    icon: ScanIcon,
    category: "ai",
  },
  {
    name: "OpenCV",
    body: "Handles camera intrinsics unprojection and 3D spatial transformations.",
    icon: CameraIcon,
    category: "deployment",
  },
  {
    name: "NumPy",
    body: "Vectorized depth map sampling and trimmed median aggregations.",
    icon: CpuIcon,
    category: "databases",
  },
  {
    name: "Pandas",
    body: "Efficient evaluation dataset loading and predictions.csv writing.",
    icon: HardDriveIcon,
    category: "storage",
  },
  {
    name: "Matplotlib",
    body: "Generates annotated visualisations for debugging and submission.",
    icon: CloudIcon,
    category: "storage",
  },
];

const PREVIEW_COUNT = 9;

export function Integrations() {
  const [category, setCategory] = useState<Category>("all");
  const [expanded, setExpanded] = useState(false);
  const [indicator, setIndicator] = useState({ left: 0, width: 0 });
  const [indicatorReady, setIndicatorReady] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered =
    category === "all"
      ? integrations
      : integrations.filter((item) => item.category === category);
  const hasMore = filtered.length > PREVIEW_COUNT;
  const visible =
    expanded || !hasMore ? filtered : filtered.slice(0, PREVIEW_COUNT);

  const updateIndicator = useCallback(() => {
    const list = listRef.current;
    if (!list) return;
    const triggers = [
      ...list.querySelectorAll<HTMLElement>('[data-slot="tabs-trigger"]'),
    ];
    const active =
      triggers.find((tab) => tab.hasAttribute("data-active")) ??
      triggers[categories.findIndex((item) => item.id === category)];
    if (!active) return;
    const listBox = list.getBoundingClientRect();
    const tabBox = active.getBoundingClientRect();
    setIndicator({
      left: tabBox.left - listBox.left,
      width: tabBox.width,
    });
  }, [category]);

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
    <Section
      id="integrations"
      className="flex flex-col items-center gap-12 md:gap-16"
    >
      <ScrollReveal direction="up" distance={24}>
        <SectionHeading
          index={6}
          heading="Integrations"
          subheading="Plug and play with your existing infrastructure."
          description="Seamlessly integrates with national databases, VMS platforms, and command center comms."
          align="center"
        />
      </ScrollReveal>

      <ScrollReveal direction="up" distance={28} delay={0.1} className="w-full">
        <Tabs
          value={category}
          onValueChange={(value) => {
            const next = categories.find((item) => item.id === value);
            if (!next) return;
            setCategory(next.id);
            setExpanded(false);
          }}
          className="w-full items-center gap-10 md:gap-12"
        >
          <div className="-mx-5 flex w-[calc(100%+2.5rem)] justify-start overflow-x-auto px-5 [scrollbar-width:none] sm:-mx-6 sm:w-[calc(100%+3rem)] sm:px-6 md:-mx-10 md:w-[calc(100%+5rem)] md:justify-center md:px-10 [&::-webkit-scrollbar]:hidden">
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
              {categories.map((item) => (
                <TabsTrigger
                  key={item.id}
                  value={item.id}
                  className="z-10 shrink-0 rounded-full px-4 py-1.5 md:px-5 data-active:bg-transparent dark:data-active:bg-transparent"
                >
                  {item.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>

          <TabsContent
            key={category}
            value={category}
            className="flex w-full flex-col items-center gap-10 duration-300 animate-in fade-in-0 md:gap-12"
          >
            <StaggerContainer
              key={category}
              staggerDelay={0.08}
              delayChildren={0.04}
              className="grid w-full max-w-4xl grid-cols-1 gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3"
            >
              {visible.map((item) => (
                <StaggerItem
                  key={item.name}
                  direction="up"
                  distance={16}
                  duration={0.6}
                  className="flex items-start gap-3.5 md:gap-4"
                >
                  <span className="inline-flex size-12 shrink-0 items-center justify-center rounded-lg bg-muted">
                    <item.icon className="size-6" />
                  </span>
                  <span className="flex min-w-0 flex-col gap-1 pt-0.5">
                    <span className="font-medium">{item.name}</span>
                    <span className="text-sm leading-body text-muted-foreground">
                      {item.body}
                    </span>
                  </span>
                </StaggerItem>
              ))}
            </StaggerContainer>

            {hasMore ? (
              <Button
                type="button"
                variant="outline"
                size="lg"
                aria-expanded={expanded}
                onClick={() => setExpanded((value) => !value)}
              >
                {expanded ? "Show less" : "View all integrations"}
              </Button>
            ) : null}
          </TabsContent>
        </Tabs>
      </ScrollReveal>
    </Section>
  );
}
