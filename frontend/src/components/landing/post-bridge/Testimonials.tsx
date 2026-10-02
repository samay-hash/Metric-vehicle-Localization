import { ArrowUpRight01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Reveal from "./motion/Reveal";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { BODY, CARD_PADDING, GRID_GAP, HEADER_GAP } from "./rhythm";
import Section from "./Section";
import SectionHeader from "./SectionHeader";
import VideoPlayer from "./VideoPlayer";

type Source = "x" | "producthunt";

type Media =
  | { kind: "image"; src: string; width: number; height: number; alt: string }
  | {
      kind: "video";
      src: string;
      poster: string;
      width: number;
      height: number;
      alt: string;
    };

type Testimonial = {
  name: string;
  handle: string;
  text: string;
  highlight: string;
  initials: string;
  avatar: string;
  source: Source;
  url: string;
  media?: Media;
};

const testimonials: Testimonial[] = [
  {
    name: "Marcus Thorne",
    handle: "Director of Security, Global Bank",
    text: "Inferia AI has completely transformed our floor monitoring. The dual layer edge filtering saves us massive bandwidth.",
    highlight: "transformed our floor monitoring",
    initials: "MT",
    avatar: "/marketing/founders/bhanu.jpg",
    source: "x",
    url: "#",
  },
  {
    name: "Sarah Jenkins",
    handle: "Chief of Police, Metro PD",
    text: "Being able to use semantic search to instantly locate threats across 40 cameras has saved us hundreds of man-hours.",
    highlight: "saved us hundreds of man-hours",
    initials: "SJ",
    avatar: "/marketing/founders/bhanu.jpg",
    source: "x",
    url: "#",
  },
  {
    name: "David Chen",
    handle: "CTO, SecureFacilities",
    text: "Deploying a VLM directly on premise was our biggest requirement. Inferia AI delivered with 94% contextual accuracy natively.",
    highlight: "delivered with 94% contextual accuracy natively",
    initials: "DC",
    avatar: "/marketing/founders/bhanu.jpg",
    source: "x",
    url: "#",
  },
  {
    name: "Elena Rodriguez",
    handle: "Head of IT, Grand Hotel",
    text: "The WebSocket alerts are genuinely instant. We see the feeds turn red before the incident even fully escalates.",
    highlight: "genuinely instant",
    initials: "ER",
    avatar: "/marketing/founders/bhanu.jpg",
    source: "x",
    url: "#",
  },
  {
    name: "Julian",
    handle: "Security Analyst",
    text: "Inferia AI is amazing, makes my life reviewing footage so much easier!",
    highlight: "so much easier",
    initials: "JU",
    avatar: "/marketing/founders/bhanu.jpg",
    source: "x",
    url: "#",
  },
  {
    name: "Nil Ni",
    handle: "Retail Owner",
    text: "Thank u for making this!!!! All current products with similar accuracy are too expensive and require cloud connectivity.",
    highlight: "require cloud connectivity",
    initials: "NN",
    avatar: "/marketing/founders/bhanu.jpg",
    source: "producthunt",
    url: "#",
  },
];

const sourceLabel: Record<Source, string> = {
  x: "X",
  producthunt: "Product Hunt",
};

function Mark({ children }: { children: React.ReactNode }) {
  return (
    <mark
      className="rounded-[0.28em] bg-primary/14 px-[0.24em] py-[0.05em] leading-[1.45] font-medium text-foreground decoration-clone dark:bg-primary/22 dark:text-foreground"
      style={{ boxDecorationBreak: "clone", WebkitBoxDecorationBreak: "clone" }}
    >
      {children}
    </mark>
  );
}

function SourceIcon({
  source,
  className,
}: {
  source: Source;
  className?: string;
}) {
  if (source === "producthunt") {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="currentColor"
        aria-hidden
        className={cn("text-[#DA552F]", className)}
      >
        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0Zm1.6 14.4h-3.4V18H7.8V6h5.8a4.2 4.2 0 1 1 0 8.4Zm0-6H10.2V12h3.4a1.8 1.8 0 0 0 0-3.6Z" />
      </svg>
    );
  }
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
      className={className}
    >
      <path d="M18.9 3H21.8L14.3 11.5L23 21H16.9L12.2 14.9L6.8 21H3.9L12 11.9L3.7 3H9.9L14.1 8.6L18.9 3ZM17.9 19.2H19.5L8.9 4.7H7.1L17.9 19.2Z" />
    </svg>
  );
}

function Quote({ text, highlight }: { text: string; highlight?: string }) {
  if (!highlight || !text.includes(highlight)) return <>&ldquo;{text}&rdquo;</>;
  const idx = text.indexOf(highlight);
  const before = text.slice(0, idx);
  const after = text.slice(idx + highlight.length);
  return (
    <>
      &ldquo;{before}
      <Mark>{highlight}</Mark>
      {after}&rdquo;
    </>
  );
}

/**
 * Sits flush at the top of the card — no frame, no inset.
 */
function MediaFrame({ media }: { media: Media }) {
  return (
    <div
      className="relative w-full"
      style={{ aspectRatio: media.width / media.height }}
    >
      {media.kind === "video" ? (
        <VideoPlayer src={media.src} poster={media.poster} label={media.alt} />
      ) : (
        <img
          src={media.src}
          alt={media.alt}
          sizes="(max-width: 768px) 92vw, (max-width: 1024px) 44vw, 380px"
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}
    </div>
  );
}

function Author({ t }: { t: Testimonial }) {
  return (
    <a
      href={t.url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Read ${t.name}'s post on ${sourceLabel[t.source]}`}
      className="group/author -mx-2 -mb-1 flex items-center gap-3 rounded-[12px] px-2 py-2 transition-colors hover:bg-foreground/[0.045] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary dark:hover:bg-white/[0.05]"
    >
      <span className="relative shrink-0">
        <Avatar className="size-11 after:border-black/[0.08] dark:after:border-white/10">
          <AvatarImage src={t.avatar} alt="" />
          <AvatarFallback className="bg-card text-xs font-semibold tracking-wide text-foreground">
            {t.initials}
          </AvatarFallback>
        </Avatar>

        <span
          className="absolute -right-1 -bottom-1 grid size-[21px] place-items-center rounded-full bg-background shadow-[0_1px_2px_rgba(0,0,0,0.12)] ring-2 ring-secondary"
          title={sourceLabel[t.source]}
        >
          <SourceIcon source={t.source} className="size-[11px]" />
        </span>
      </span>

      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm leading-5 font-semibold text-foreground">
          {t.name}
        </span>
        <span className="mt-0.5 block truncate text-xs leading-4 text-muted-foreground">
          {t.handle}
        </span>
      </span>
      <HugeiconsIcon
        icon={ArrowUpRight01Icon}
        className="size-4 shrink-0 text-muted-foreground transition-colors duration-200 ease-out group-hover/author:text-foreground"
      />
    </a>
  );
}

function Card({ t }: { t: Testimonial }) {
  return (
    <div className="flex break-inside-avoid flex-col overflow-hidden rounded-card border-0 bg-secondary dark:bg-secondary">
      {t.media ? <MediaFrame media={t.media} /> : null}

      <div className={cn("flex flex-1 flex-col", CARD_PADDING)}>
        <span
          aria-hidden
          className="select-none font-heading text-[42px] font-bold leading-none tracking-[-0.04em] text-primary"
        >
          “
        </span>

        <p className={`mt-3 text-foreground ${BODY}`}>
          <Quote text={t.text} highlight={t.highlight} />
        </p>

        <div className="mt-4 border-t border-foreground/[0.07] dark:border-white/[0.06]" />

        <div className="pt-3">
          <Author t={t} />
        </div>
      </div>
    </div>
  );
}

const CARD_WIDTH = 390;
const CHARS_PER_LINE = 44;
const LINE_HEIGHT = 28; 
const CARD_CHROME = 190; 

function estimateHeight(t: Testimonial) {
  const lines = Math.ceil(t.text.length / CHARS_PER_LINE);
  const media = t.media ? CARD_WIDTH / (t.media.width / t.media.height) : 0;
  return CARD_CHROME + lines * LINE_HEIGHT + media;
}

export function PostBridgeTestimonials() {
  const cols: Array<typeof testimonials> = [[], [], []];
  const heights = [0, 32, 0]; 
  testimonials.forEach((t) => {
    const target = heights.indexOf(Math.min(...heights));
    cols[target].push(t);
    heights[target] += estimateHeight(t) + 16;
  });

  return (
    <Section id="reviews" className="relative">
      <SectionHeader
        eyebrow="Testimonials"
        title="Trusted by security teams."
        titleMuted="Here's what they say."
      />

      <div
        className={cn(
          HEADER_GAP,
          GRID_GAP,
          "columns-1 space-y-3 md:columns-2 md:space-y-4 lg:hidden",
        )}
      >
        {testimonials.map((t, idx) => (
          <Reveal
            key={`${t.name}-${t.handle}`}
            delay={(idx % 3) * 0.06}
            className="break-inside-avoid"
          >
            <Card t={t} />
          </Reveal>
        ))}
      </div>

      <div
        className={cn(
          HEADER_GAP,
          GRID_GAP,
          "hidden lg:grid lg:grid-cols-3 lg:items-start",
        )}
      >
        {cols.map((col, colIdx) => (
          <div
            key={colIdx}
            className={cn("flex flex-col", GRID_GAP, colIdx === 1 && "lg:mt-8")}
          >
            {col.map((t, idx) => (
              <Reveal key={`${t.name}-${t.handle}`} delay={(idx % 3) * 0.06}>
                <Card t={t} />
              </Reveal>
            ))}
          </div>
        ))}
      </div>

      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-0 h-28 bg-gradient-to-b from-transparent via-background/70 to-background"
      />
    </Section>
  );
}
