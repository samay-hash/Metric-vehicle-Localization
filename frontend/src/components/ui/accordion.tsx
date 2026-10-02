import { Accordion as AccordionPrimitive } from "@base-ui/react/accordion";

import { cn } from "@/lib/utils";

function Accordion({ className, ...props }: AccordionPrimitive.Root.Props) {
  return (
    <AccordionPrimitive.Root
      data-slot="accordion"
      className={cn("flex w-full flex-col gap-4", className)}
      {...props}
    />
  );
}

function AccordionItem({ className, ...props }: AccordionPrimitive.Item.Props) {
  return (
    <AccordionPrimitive.Item
      data-slot="accordion-item"
      className={cn(
        "overflow-hidden rounded-2xl border border-dashed bg-card",
        className,
      )}
      {...props}
    />
  );
}

function AccordionTrigger({
  className,
  children,
  ...props
}: AccordionPrimitive.Trigger.Props) {
  return (
    <AccordionPrimitive.Header className="flex">
      <AccordionPrimitive.Trigger
        data-slot="accordion-trigger"
        className={cn(
          "group/accordion-trigger relative flex flex-1 items-center justify-between gap-6 px-5 py-4 text-left text-base leading-title font-medium tracking-tight outline-none aria-disabled:pointer-events-none aria-disabled:opacity-50 md:px-6 md:py-4.5 md:text-lg",
          className,
        )}
        {...props}
      >
        {children}
        <span className="flex size-6 shrink-0 items-center justify-center rounded-full border border-dashed">
          <span
            data-slot="accordion-trigger-icon"
            className="relative size-3 origin-center transition-transform duration-200 ease-out group-hover/accordion-trigger:rotate-45 in-[[data-slot=accordion-trigger][aria-expanded=true]]:rotate-0!"
            aria-hidden
          >
            <span className="absolute top-1/2 left-0 h-0.5 w-full -translate-y-1/2 rounded-full bg-current" />
            <span className="absolute top-0 left-1/2 h-full w-0.5 -translate-x-1/2 rounded-full bg-current transition-transform duration-200 ease-out group-aria-expanded/accordion-trigger:scale-y-0" />
          </span>
        </span>
      </AccordionPrimitive.Trigger>
    </AccordionPrimitive.Header>
  );
}

function AccordionContent({
  className,
  children,
  ...props
}: AccordionPrimitive.Panel.Props) {
  return (
    <AccordionPrimitive.Panel
      data-slot="accordion-content"
      className="overflow-hidden px-5 text-sm leading-body text-muted-foreground data-open:animate-accordion-down data-closed:animate-accordion-up md:px-6"
      {...props}
    >
      <div
        className={cn(
          "h-(--accordion-panel-height) pt-0 pb-4 data-ending-style:h-0 data-starting-style:h-0 [&_a]:underline [&_a]:underline-offset-3 [&_a]:hover:text-foreground [&_p:not(:last-child)]:mb-4 md:pb-4.5",
          className,
        )}
      >
        {children}
      </div>
    </AccordionPrimitive.Panel>
  );
}

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent };
