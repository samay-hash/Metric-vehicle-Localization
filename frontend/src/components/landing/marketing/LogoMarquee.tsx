

const logos = [
  { name: "Slack", src: "/marketing/logos/slack.svg" },
  { name: "Notion", src: "/marketing/logos/notion.svg" },
  { name: "GitHub", src: "/marketing/logos/github.svg" },
  { name: "Stripe", src: "/marketing/logos/stripe.svg" },
  { name: "Linear", src: "/marketing/logos/linear.svg" },
  { name: "OpenAI", src: "/marketing/logos/openai.svg" },
  { name: "Anthropic", src: "/marketing/logos/anthropic.svg" },
  { name: "Vercel", src: "/marketing/logos/vercel.svg" },
  { name: "HubSpot", src: "/marketing/logos/hubspot.svg" },
  { name: "Discord", src: "/marketing/logos/discord.svg" },
  { name: "Zoom", src: "/marketing/logos/zoom.svg" },
] as const;

function LogoRow({ copy }: { copy: number }) {
  return (
    <ul className="flex gap-2" aria-hidden={copy === 1 || undefined}>
      {logos.map((logo) => (
        <li
          key={`${copy}-${logo.name}`}
          className="flex h-20 w-44 shrink-0 items-center justify-center rounded-xl border border-dashed bg-card px-6"
        >
          <span className="relative h-6 w-full max-w-[8.5rem]">
            <img
              src={logo.src}
              alt={copy === 1 ? "" : logo.name}
              
              sizes="136px"
              className="absolute inset-0 h-full w-full object-contain brightness-0 dark:invert"
              
            />
          </span>
        </li>
      ))}
    </ul>
  );
}

export function LogoMarquee() {
  return (
    <div className="flex w-full flex-col items-center gap-6 px-5 pb-12 sm:px-6 sm:pb-16 md:gap-8 md:px-10 md:pb-24">
      <p className="text-xs font-medium tracking-eyebrow text-muted-foreground uppercase">
        Works with the tools you already use
      </p>
      <div className="w-full overflow-hidden rounded-2xl border border-dashed p-2">
        <div className="group overflow-hidden">
          <div className="animate-marquee flex w-max gap-2 pr-2 group-hover:[animation-play-state:paused]">
            <LogoRow copy={0} />
            <LogoRow copy={1} />
          </div>
        </div>
      </div>
    </div>
  );
}
