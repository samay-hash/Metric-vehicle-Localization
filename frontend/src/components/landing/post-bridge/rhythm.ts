/**
 * The marketing page's shared spacing and type tokens.
 *
 * `Section` owns the page's outer rhythm (gutters + section padding); this file
 * owns the rhythm *inside* a section. Every value here is used in more than one
 * component — if a spacing or type decision only applies once, it stays inline
 * at the call site.
 *
 * These are plain string literals so Tailwind's scanner still picks the classes
 * up from this file.
 */

/** Gap between a `SectionHeader` and the body it introduces. */
export const HEADER_GAP = "mt-12 md:mt-16";

/** Gap between cards or tiles in any grid on the page. */
export const GRID_GAP = "gap-3 md:gap-4";

/** Padding inside a standalone card or tile. */
export const CARD_PADDING = "p-6";

/** Padding for the copy column of a full-width panel. */
export const PANEL_PADDING =
  "px-6 py-8 sm:px-8 md:px-9 md:py-9 lg:px-10 lg:py-10";

/** Media column of a full-width panel — steps with `PANEL_PADDING`. */
export const PANEL_MEDIA =
  "min-h-[280px] sm:min-h-[340px] md:min-h-[420px] lg:min-h-[480px]";

/**
 * Color grade for painterly art. Source florals sit too cyan for the
 * brand; this rotates them toward emerald without washing them out.
 */
export const ART_FILTER =
  "object-cover object-center [filter:hue-rotate(-34deg)_saturate(0.82)_brightness(1.02)_contrast(1.05)]";

/** Heading inside a panel — one step below `SectionHeader`'s h2. */
export const PANEL_HEADING =
  "font-heading text-[1.375rem] leading-[1.2] font-medium tracking-[-0.025em] text-balance md:text-[1.625rem]";

/** Quiet label above a heading. Matches `SectionHeader`'s eyebrow exactly. */
export const EYEBROW = "text-sm leading-5 text-muted-foreground";

/** All-caps strip label ("Featured on", "Post to", pricing group headings). */
export const OVERLINE =
  "text-[0.6875rem] leading-4 font-semibold tracking-[0.12em] uppercase";

/** Default paragraph size for body copy inside panels and cards. */
export const BODY = "text-[0.9375rem] leading-7 text-pretty";

/** Solid mint status chip used on floating product cards. */
export const SOFT_CHIP =
  "inline-flex shrink-0 items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-1 text-[0.6875rem] leading-4 font-medium text-primary";
