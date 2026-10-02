
import { useMemo, useState } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function fallbackSrc(handle: string, name: string) {
  if (handle.startsWith("r/")) {
    return `https://unavatar.io/reddit/${encodeURIComponent(name)}`;
  }
  return `https://unavatar.io/x/${encodeURIComponent(handle.replace(/^@/, ""))}`;
}

export function ReviewAvatar({
  name,
  handle,
  src,
  className,
}: {
  name: string;
  handle: string;
  src?: string;
  className?: string;
}) {
  const sources = useMemo(
    () => [src, fallbackSrc(handle, name)].filter(Boolean) as string[],
    [handle, name, src],
  );
  const [index, setIndex] = useState(0);
  const current = sources[index];

  return (
    <Avatar className={cn("size-12", className)}>
      {current ? (
        <AvatarImage
          src={current}
          alt=""
          onError={() => setIndex((value) => value + 1)}
        />
      ) : null}
      <AvatarFallback>{initials(name)}</AvatarFallback>
    </Avatar>
  );
}
