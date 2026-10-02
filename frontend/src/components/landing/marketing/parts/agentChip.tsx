import { SparklesIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";

import type { ComponentProps } from "react";

import { Badge } from "@/components/ui/badge";

type AgentChipProps = {
  emoji?: string;
  icon?: ComponentProps<typeof HugeiconsIcon>["icon"];
  name: string;
  role: string;
  lead?: boolean;
  image?: string;
};

export function AgentChip({
  emoji,
  icon,
  name,
  role,
  lead = false,
  image,
}: AgentChipProps) {
  return (
    <Badge variant="outline" className="gap-1.5 py-0.5">
      {image ? (
        <img
          src={image}
          alt=""
          width={16}
          height={16}
          className="size-4 rounded-full object-cover"
        />
      ) : icon ? (
        <HugeiconsIcon icon={icon} className="size-3.5 text-brand" />
      ) : (
        <span aria-hidden>{emoji}</span>
      )}
      <span className="font-medium">{name}</span>
      <span className="text-muted-foreground">{role}</span>
      {lead ? (
        <span
          role="img"
          className="inline-flex size-3.5 items-center justify-center rounded-full bg-brand/10 text-brand"
          title="Squad lead"
          aria-label="Squad lead"
        >
          <HugeiconsIcon icon={SparklesIcon} className="size-2.5" />
        </span>
      ) : null}
    </Badge>
  );
}
