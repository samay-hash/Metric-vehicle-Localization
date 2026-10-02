import {
  ArrowUpRight01Icon,
  Cancel01Icon,
  Menu01Icon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useLenis } from "lenis/react";
import { motion, useReducedMotion } from "motion/react";
import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

import { Logo } from "@/components/landing/layout/Logo";
import { Button, buttonVariants } from "@/components/ui/button";
import { LiquidMetalButton } from "@/components/ui/liquid-metal-button";
import { cn } from "@/lib/utils";

const links = [
  { label: "Pipeline", href: "#features" },
  { label: "Experiments", href: "#timeline" },
  { label: "Results", href: "#pricing" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const reduceMotion = useReducedMotion();
  const navigate = useNavigate();

  useLenis(({ scroll }) => {
    setScrolled(scroll > 32);
  });

  useEffect(() => {
    setScrolled(window.scrollY > 32);
  }, []);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    const collapse = () => {
      if (media.matches) setOpen(false);
    };
    collapse();
    media.addEventListener("change", collapse);
    return () => media.removeEventListener("change", collapse);
  }, []);

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: -16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: reduceMotion ? 0 : 0.7,
        ease: [0.22, 1, 0.36, 1],
      }}
      className={cn(
        "fixed inset-x-0 z-50 transition-[top] duration-300",
        scrolled ? "top-3" : "top-0",
      )}
    >
      <div className="mx-auto w-full max-w-7xl px-5 sm:px-6 md:px-10">
        <header
          className={cn(
            "w-full px-3 transition-[padding,background-color,border-radius] duration-300 md:px-4",
            open
              ? "rounded-2xl border border-dashed bg-background py-2"
              : scrolled
                ? "rounded-full border border-dashed bg-background py-2"
                : "bg-transparent py-4 md:py-5",
          )}
        >
          <nav className="grid grid-cols-[1fr_auto] items-center gap-3 lg:grid-cols-[1fr_auto_1fr]">
            <Logo className="justify-self-start" />

            <div className="hidden items-center text-sm lg:flex">
              {links.map((link, index) => (
                <span key={link.href} className="flex items-center">
                  {index > 0 ? (
                    <span className="px-3 text-muted-foreground" aria-hidden>
                      •
                    </span>
                  ) : null}
                  <a
                    href={link.href}
                    className="text-foreground transition-colors hover:text-brand"
                  >
                    {link.label}
                  </a>
                </span>
              ))}
            </div>

            <div className="flex items-center justify-end gap-2">
              <LiquidMetalButton
                onClick={() => navigate("/dashboard")}
                size="sm"
                borderWidth={2}
                className="hidden sm:inline-flex"
                metalConfig={{ speed: 0, colorBack: "#0ea5e9", colorTint: "#38bdf8" }}
              >
                <span className="flex items-center gap-2">
                  CV Results
                  <HugeiconsIcon
                    icon={ArrowUpRight01Icon}
                    className="size-4"
                  />
                </span>
              </LiquidMetalButton>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="lg:hidden"
                aria-label={open ? "Close menu" : "Open menu"}
                aria-expanded={open}
                aria-controls="mobile-menu"
                onClick={() => setOpen((value) => !value)}
              >
                <HugeiconsIcon icon={open ? Cancel01Icon : Menu01Icon} />
              </Button>
            </div>
          </nav>

          <div
            id="mobile-menu"
            inert={!open}
            className={cn(
              "grid transition-[grid-template-rows,opacity] duration-150 ease-out lg:hidden",
              open
                ? "grid-rows-[1fr] opacity-100"
                : "grid-rows-[0fr] opacity-0",
            )}
          >
            <div className="overflow-hidden">
              <div className="mt-3 flex flex-col gap-1 border-t border-dashed pt-3">
                {links.map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    onClick={() => setOpen(false)}
                    className="px-2 py-2 text-sm"
                  >
                    {link.label}
                  </a>
                ))}
                <LiquidMetalButton
                  onClick={() => {
                    setOpen(false);
                    navigate("/dashboard");
                  }}
                  size="sm"
                  borderWidth={2}
                  className="mt-1 sm:hidden w-full"
                  metalConfig={{ speed: 0, colorBack: "#0ea5e9", colorTint: "#38bdf8" }}
                >
                  <span className="flex items-center justify-center gap-2">
                    CV Results
                    <HugeiconsIcon
                      icon={ArrowUpRight01Icon}
                      className="size-4"
                    />
                  </span>
                </LiquidMetalButton>
              </div>
            </div>
          </div>
        </header>
      </div>
    </motion.div>
  );
}
