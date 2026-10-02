import { NewTwitterIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";


import { ScrollReveal } from "@/components/landing/animation/ScrollReveal";
import { ReviewAvatar } from "@/components/landing/marketing/parts/reviewAvatar";
import { Section } from "@/components/landing/marketing/parts/section";
import { SectionHeading } from "@/components/landing/marketing/parts/sectionHeading";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const pressStrip = [
  {
    label: "The Next New Thing",
    href: "https://youtu.be/_ISs5FavbJ4",
  },
  {
    label: "Profitable Founder",
    href: "https://youtu.be/0LnLn2MK62A",
  },
  {
    label: "Bootstrapped Giants",
    href: "https://bootstrappedgiants.com/p/this-bootstrapper-built-an-ai-workforce",
  },
];

const featured = {
  name: "Udayan Walvekar",
  handle: "@udayan_w",
  bio: "Co-Founder & CEO, GrowthX",
  quote:
    "India's first OpenClaw Buildathon. Your Bangalore host is @pbteja1998, who built a 10-agent system called Inferia AI that generated $15K in 3 days.",
  href: "https://x.com/udayan_w/status/2017780212042522692",
  avatarUrl:
    "https://pbs.twimg.com/profile_images/1905507726937280512/L5ZlTTlF_400x400.jpg",
};

const quotes = [
  {
    name: "Nader Dabit",
    handle: "@dabit3",
    bio: "DevRel",
    quote:
      "If you're using @openclaw this writeup will probably make your setup 10x more powerful and productive.",
    href: "https://x.com/dabit3/status/2018029884430233903",
    avatarUrl:
      "https://pbs.twimg.com/profile_images/1951619597695672321/c1FsysWP_400x400.jpg",
  },
  {
    name: "Thomas Power",
    handle: "@thomaspower",
    bio: "Network architect",
    quote:
      'What you\'ve really done here is move AI from "tool" to "team infrastructure." Most people are still using one assistant like a search box. You\'ve architected continuity, memory, delegation, and accountability. That\'s the shift.',
    href: "https://x.com/thomaspower/status/2020129056453263714",
    avatarUrl:
      "https://pbs.twimg.com/profile_images/1714603152459055104/P89TiypZ_400x400.jpg",
  },
  {
    name: "Ryan Carson",
    handle: "@ryancarson",
    bio: "Founder, Treehouse",
    quote:
      "This is exactly what I was looking for. Getting this spun up locally. Will report back.",
    href: "https://x.com/ryancarson/status/2019405458881257533",
    avatarUrl:
      "https://pbs.twimg.com/profile_images/2016785876261679104/LJFhaQ17_400x400.jpg",
  },
  {
    name: "Nathaniel Whittemore",
    handle: "@nlw",
    bio: "AI Daily Brief",
    quote:
      "Yo @pbteja1998 are you releasing Inferia AI? Deciding if I need to build a version for myself.",
    href: "https://x.com/nlw/status/2019525188061393281",
    avatarUrl:
      "https://pbs.twimg.com/profile_images/1610015898739277824/1nTQMKpr_400x400.jpg",
  },
  {
    name: "Marc Lou",
    handle: "@marclou",
    bio: "Maker, ShipFast",
    quote:
      "I think @pbteja1998 is going to show us what's possible with its MissionControl project, a team of AI agents talking to each other.",
    href: "https://x.com/marclou/status/2020449036977983948",
    avatarUrl: "https://unavatar.io/x/marclou",
  },
  {
    name: "Ali Karami",
    handle: "@alikarami__",
    bio: "Builder",
    quote:
      "AI agents are easy to spin up. Visibility is the hard part. So I built BatCave, my realtime mission control, inspired by @pbteja1998. Live monitoring, task pipeline, model orchestration, realtime sync.",
    href: "https://x.com/alikarami__/status/2023895116771971418",
    avatarUrl:
      "https://pbs.twimg.com/profile_images/1884246366055972864/9nOzfzDc_400x400.jpg",
  },
  {
    name: "xtomleex",
    handle: "r/openclaw",
    bio: "Reddit",
    quote:
      "Anyone using missioncontrolhq.ai? He has 100's of users, with a cool dashboard. Seems like there's a market for prebuilt teams that are high functioning even if the pricing is 100 dollars.",
    href: "https://www.reddit.com/r/openclaw/",
  },
];

const rows = [
  { id: "left", items: quotes.slice(0, 3), reverse: false },
  { id: "right", items: quotes.slice(3), reverse: true },
];

type Review = (typeof quotes)[number];

function AuthorBar({
  name,
  handle,
  bio,
  avatarUrl,
}: Pick<Review, "name" | "handle" | "bio" | "avatarUrl">) {
  return (
    <div className="flex w-full min-w-0 items-center rounded-full border border-dashed bg-background py-1 pr-1 pl-1.5">
      <ReviewAvatar name={name} handle={handle} src={avatarUrl} />
      <span className="flex min-w-0 flex-1 flex-col px-3">
        <span className="truncate font-medium">{name}</span>
        <span className="truncate text-xs tracking-eyebrow text-muted-foreground uppercase">
          {bio}
        </span>
      </span>
      <span
        aria-hidden
        className={buttonVariants({ size: "icon", variant: "outline" })}
      >
        <HugeiconsIcon icon={NewTwitterIcon} />
      </span>
    </div>
  );
}

function ReviewCard({ name, handle, bio, quote, href, avatarUrl }: Review) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="flex w-[min(22rem,calc(100vw-2.5rem))] shrink-0 sm:w-[22rem] md:w-[24rem]"
    >
      <Card className="flex h-full w-full flex-col justify-between p-6 md:p-7">
        <div className="flex flex-col gap-3">
          <p className="text-xs font-medium tracking-eyebrow text-muted-foreground uppercase">
            {handle}
          </p>
          <p className="font-heading text-xl leading-heading tracking-heading text-pretty">
            "{quote}"
          </p>
        </div>
        <div className="mt-5">
          <AuthorBar
            name={name}
            handle={handle}
            bio={bio}
            avatarUrl={avatarUrl}
          />
        </div>
      </Card>
    </a>
  );
}

function MarqueeRow({ items, reverse }: { items: Review[]; reverse: boolean }) {
  return (
    <div className="group overflow-hidden">
      <div
        className={cn(
          "flex w-max gap-4 pr-4",
          reverse ? "animate-marquee-reverse" : "animate-marquee",
          "group-hover:[animation-play-state:paused]",
        )}
      >
        {[0, 1].map((copy) => (
          <div key={copy} className="flex gap-4" aria-hidden={copy === 1}>
            {items.map((item) => (
              <ReviewCard key={`${copy}-${item.handle}`} {...item} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function Testimonials() {
  return (
    <Section id="reviews" className="flex flex-col gap-12 md:gap-16">
      <ScrollReveal direction="up" distance={24}>
        <SectionHeading
          index={7}
          heading="Reviews"
          subheading="Public posts, not quotes we collected."
          description={
            <>
              Thomas Power called it the shift from tool to team infrastructure.
              Interviews:{" "}
              {pressStrip.map((item, index) => (
                <span key={item.label}>
                  <a
                    href={item.href}
                    target="_blank"
                    rel="noreferrer"
                    className="underline underline-offset-4 hover:text-foreground"
                  >
                    {item.label}
                  </a>
                  {index < pressStrip.length - 1 ? ", " : "."}
                </span>
              ))}
            </>
          }
          align="center"
        />
      </ScrollReveal>

      <div className="flex flex-col gap-3 md:gap-4">
        <ScrollReveal direction="up" distance={28} delay={0.1}>
          <Card className="grid gap-0 overflow-hidden py-0 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
            <div className="relative h-full min-h-72 bg-muted sm:min-h-80 lg:min-h-[28rem]">
              <img
                src={featured.avatarUrl}
                alt={featured.name}
                
                
                sizes="(min-width: 1024px) 40vw, 100vw"
                className="object-cover object-center"
              />
            </div>
            <div className="flex flex-col justify-between">
              <CardContent className="flex-1 p-5 sm:p-8 md:p-10">
                <p className="font-heading text-xl leading-heading tracking-heading text-pretty sm:text-2xl md:text-3xl">
                  "{featured.quote}"
                </p>
              </CardContent>
              <CardFooter className="mt-auto justify-between gap-4 border-t border-dashed p-5 pt-4 sm:p-8 sm:pt-4 md:p-10 md:pt-5">
                <div className="flex flex-col gap-1">
                  <span className="font-heading text-lg leading-title tracking-title">
                    {featured.name}
                  </span>
                  <span className="text-xs tracking-eyebrow text-muted-foreground uppercase">
                    {featured.bio}
                  </span>
                </div>
                <a
                  href={featured.href}
                  target="_blank"
                  rel="noreferrer"
                  aria-label="Read the original post on X"
                  className={buttonVariants({
                    size: "icon",
                    variant: "outline",
                  })}
                >
                  <HugeiconsIcon icon={NewTwitterIcon} />
                </a>
              </CardFooter>
            </div>
          </Card>
        </ScrollReveal>

        <ScrollReveal
          direction="up"
          distance={20}
          delay={0.15}
          className="flex flex-col gap-3 [mask-image:linear-gradient(to_right,transparent,black_6%,black_94%,transparent)]"
        >
          {rows.map((row) => (
            <MarqueeRow key={row.id} items={row.items} reverse={row.reverse} />
          ))}
        </ScrollReveal>
      </div>
    </Section>
  );
}
