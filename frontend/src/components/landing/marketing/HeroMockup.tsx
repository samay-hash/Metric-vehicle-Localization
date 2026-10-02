

function MacWindow() {
  return (
    <div className="overflow-hidden rounded-2xl bg-background md:rounded-[1.75rem]">
      <div className="flex items-center gap-1.5 px-4 py-3">
        <span className="size-2.5 rounded-full bg-[#ff5f57]" />
        <span className="size-2.5 rounded-full bg-[#febc2e]" />
        <span className="size-2.5 rounded-full bg-[#28c840]" />
      </div>
      <div className="w-full bg-muted">
        <img src="/anatomy.png" alt="Inferia Dashboard" className="w-full h-auto object-cover" />
      </div>
    </div>
  );
}

export function HeroMockup() {
  return (
    <div className="relative w-full overflow-hidden">
      <img
        src="/marketing/hero-canvas.jpg"
        alt=""
        
        
        sizes="(min-width: 1280px) 80rem, 100vw"
        className="absolute inset-0 h-full w-full object-cover"
      />
      <div className="relative flex justify-center px-5 py-8 sm:px-6 sm:py-10 md:px-10 md:py-14 lg:px-16 lg:py-16">
        <div className="w-full max-w-5xl">
          <MacWindow />
        </div>
      </div>
    </div>
  );
}
