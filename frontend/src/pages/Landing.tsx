import { SmoothScroll } from "@/components/landing/layout/SmoothScroll";
import { Navbar } from "@/components/landing/marketing/Navbar";
import { Footer } from "@/components/landing/marketing/Footer";

import { PostBridgeHero } from "@/components/landing/post-bridge/Hero";
import { PostBridgeFeatures } from "@/components/landing/post-bridge/Features";
import { PostBridgeSteps } from "@/components/landing/post-bridge/Steps";
import { Squads } from "@/components/landing/marketing/Squads";
import { Integrations } from "@/components/landing/marketing/Integrations";

import { Timeline } from "@/components/landing/marketing/Timeline";
import { Pricing } from "@/components/landing/marketing/Pricing";
import { Faq } from "@/components/landing/marketing/Faq";

export default function Landing() {
  return (
    <SmoothScroll>
      <div className="relative flex min-h-full flex-1 flex-col bg-background font-sans text-foreground">
        <Navbar />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 z-10 flex justify-center"
        >
          <div className="h-full w-full max-w-7xl border-x border-dashed border-border" />
        </div>
        <div className="relative flex flex-1 flex-col [&>*+*]:-mt-px">
          <main className="flex flex-1 flex-col [&>*+*]:-mt-px">
            <PostBridgeHero />
            <PostBridgeSteps />
            <PostBridgeFeatures />
            <Timeline />
            <Squads />
            <Integrations />
            <Pricing />
            <Faq />
          </main>
          <Footer />
        </div>
      </div>
    </SmoothScroll>
  );
}
