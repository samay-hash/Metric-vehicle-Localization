/**
 * The supported platforms, in one order, with one icon set.
 *
 * Hero, Integrations and Pricing each render this list; keeping it here stops
 * the three strips from drifting apart in order, label or icon family (Pricing
 * previously mixed `fa6-brands` into an otherwise `simple-icons` row).
 */
export const platforms = [
  { label: "Twitter/X", icon: "simple-icons:x", color: "#000000" },
  { label: "Instagram", icon: "simple-icons:instagram", color: "#E4405F" },
  { label: "LinkedIn", icon: "simple-icons:linkedin", color: "#0A66C2" },
  { label: "Facebook", icon: "simple-icons:facebook", color: "#1877F2" },
  { label: "TikTok", icon: "simple-icons:tiktok", color: "#000000" },
  { label: "YouTube", icon: "simple-icons:youtube", color: "#FF0000" },
  { label: "Bluesky", icon: "simple-icons:bluesky", color: "#1185FE" },
  { label: "Threads", icon: "simple-icons:threads", color: "#000000" },
  { label: "Pinterest", icon: "simple-icons:pinterest", color: "#E60023" },
  { label: "Google Business", icon: "simple-icons:google", color: "#4285F4" },
] as const;

/** Icon size for the flat platform strips in Hero and Pricing. */
export const PLATFORM_ICON = "size-[22px] md:size-6";
