import { ArrowUpRight01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { Link } from "react-router-dom";

import { ScrollReveal } from "@/components/landing/animation/ScrollReveal";
import { Logo } from "@/components/landing/layout/Logo";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const columns = [
  {
    title: "Navigation",
    links: [
      { label: "Features", href: "#features" },
      { label: "How it works", href: "#steps" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", href: "#" },
      { label: "Terms of Service", href: "#" },
    ],
  },
  {
    title: "Support",
    links: [{ label: "Help Center", href: "#" }],
  },
];

function FooterLink({
  href,
  label,
  className,
}: {
  href: string;
  label: string;
  className?: string;
}) {
  const external = href.startsWith("http");
  return (
    <a
      href={href}
      className={cn(
        "text-sm text-muted-foreground transition-colors hover:text-brand",
        className,
      )}
      {...(external ? { target: "_blank", rel: "noreferrer" } : undefined)}
    >
      {label}
    </a>
  );
}

export function Footer() {
  return (
    <footer className="w-full bg-card text-card-foreground">
      <div className="border-t border-dashed px-5 py-12 text-center sm:px-6 sm:py-14 md:px-10 md:py-20">
        <ScrollReveal
          direction="up"
          distance={24}
          className="mx-auto flex w-full max-w-7xl flex-col items-center"
        >
          <div className="flex max-w-2xl flex-col items-center">
            <h2 className="font-heading text-3xl leading-display font-medium tracking-display text-balance sm:text-4xl md:text-5xl">
              Secure your city with zero data leakage.
            </h2>
            <p className="mt-3 max-w-xl text-base leading-body tracking-tight text-muted-foreground text-pretty md:mt-3.5 md:text-lg">
              Deploy locally. Scale effortlessly. Inferia AI monitors everything so you don't have to.
            </p>
          </div>
          <div className="mt-8 flex w-full max-w-md flex-col items-stretch gap-3 sm:max-w-none sm:flex-row sm:flex-wrap sm:items-center sm:justify-center sm:gap-3.5">
            <Link
              to="/dashboard"
              className={cn(buttonVariants({ size: "lg" }), "w-full sm:w-auto")}
            >
              Enter Command Center
              <HugeiconsIcon icon={ArrowUpRight01Icon} data-icon="inline-end" />
            </Link>
            <a
              href="mailto:support@sentinel.ai"
              className={cn(
                buttonVariants({ size: "lg", variant: "secondary" }),
                "w-full sm:w-auto",
              )}
            >
              Contact Support
              <HugeiconsIcon icon={ArrowUpRight01Icon} data-icon="inline-end" />
            </a>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Fully on premise architecture for maximum privacy.
          </p>
        </ScrollReveal>
      </div>

      <div className="border-t border-dashed">
        <div className="mx-auto w-full max-w-7xl">
          <div className="grid lg:grid-cols-2">
            <div className="flex flex-col gap-3.5 p-5 sm:p-6 md:p-10 lg:p-12">
              <Logo className="text-base" />
              <p className="max-w-xs text-sm leading-body text-muted-foreground text-pretty">
                A complete AI surveillance platform that filters noise at the edge and contextualizes threats locally.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-8 p-5 sm:grid-cols-3 sm:p-6 md:p-10 lg:p-12">
              {columns.map((column) => (
                <div key={column.title} className="flex flex-col gap-3">
                  <span className="text-sm font-medium">{column.title}</span>
                  {column.links.map((link) => (
                    <FooterLink key={link.label} {...link} />
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-2 border-t border-dashed px-5 py-4.5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6 md:px-10">
            <span>© 2026 Inferia AI - Gujarat Police.</span>
            <span>
              Built for city-wide scale and advanced safety.
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
