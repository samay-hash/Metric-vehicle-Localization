"use client";

import {
  PauseIcon,
  PlayIcon,
  VolumeHighIcon,
  VolumeOffIcon,
} from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type VideoPlayerProps = {
  src: string;
  poster?: string;
  type?: string;
  label: string;
  className?: string;
  fit?: "cover" | "contain";
};

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function VideoPlayer({
  src,
  poster,
  type = "video/mp4",
  label,
  className,
  fit = "cover",
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [started, setStarted] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const togglePlay = useCallback(() => {
    const el = videoRef.current;
    if (!el) return;
    if (el.paused) {
      void el.play();
    } else {
      el.pause();
    }
  }, []);

  const toggleMute = useCallback(() => {
    const el = videoRef.current;
    if (!el) return;
    el.muted = !el.muted;
    setMuted(el.muted);
  }, []);

  const seek = useCallback((next: number) => {
    const el = videoRef.current;
    if (!el) return;
    el.currentTime = next;
    setTime(next);
  }, []);

  return (
    <div
      className={cn(
        "group/video relative isolate size-full overflow-hidden bg-card",
        className,
      )}
    >
      {/* biome-ignore lint/a11y/useMediaCaption: no caption file for this clip */}
      <video
        ref={videoRef}
        className={cn(
          "absolute inset-0 size-full",
          fit === "contain" ? "object-contain" : "object-cover",
        )}
        poster={poster}
        preload="metadata"
        playsInline
        aria-label={label}
        onPlay={() => {
          setPlaying(true);
          setStarted(true);
        }}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
        onDurationChange={(event) =>
          setDuration(event.currentTarget.duration || 0)
        }
        onClick={togglePlay}
      >
        <source src={src} type={type} />
      </video>

      {!playing ? (
        <button
          type="button"
          onClick={togglePlay}
          aria-label={started ? `Resume ${label}` : `Play ${label}`}
          className="absolute inset-0 z-10 grid place-items-center bg-foreground/8 transition-colors hover:bg-foreground/10"
        >
          <span className="grid size-14 place-items-center rounded-full bg-primary text-primary-foreground shadow-[0_12px_32px_-12px_oklch(0.54_0.13_153.45/0.9)] transition-transform duration-200 ease-out hover:scale-105 active:scale-95">
            <HugeiconsIcon icon={PlayIcon} className="size-6 translate-x-px" />
          </span>
        </button>
      ) : null}

      <div
        className={cn(
          "pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-center gap-2 bg-gradient-to-t from-foreground/70 to-transparent px-3 pt-10 pb-3 transition-opacity duration-200",
          playing
            ? "opacity-0 group-hover/video:pointer-events-auto group-hover/video:opacity-100 group-focus-within/video:pointer-events-auto group-focus-within/video:opacity-100"
            : started
              ? "pointer-events-auto opacity-100"
              : "opacity-0",
        )}
      >
        <button
          type="button"
          onClick={togglePlay}
          aria-label={playing ? "Pause" : "Play"}
          className="grid size-8 shrink-0 place-items-center rounded-full text-white transition-colors hover:bg-white/15"
        >
          <HugeiconsIcon
            icon={playing ? PauseIcon : PlayIcon}
            className="size-4"
          />
        </button>

        <span className="min-w-[4.5rem] text-[11px] leading-4 tabular-nums text-white/80">
          {formatTime(time)} / {formatTime(duration)}
        </span>

        <input
          type="range"
          min={0}
          max={duration || 0}
          step={0.1}
          value={time}
          aria-label="Seek"
          onChange={(event) => seek(Number(event.target.value))}
          className="h-1 min-w-0 flex-1 cursor-pointer appearance-none rounded-full bg-white/25 accent-primary [&::-webkit-slider-thumb]:size-3 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white"
        />

        <button
          type="button"
          onClick={toggleMute}
          aria-label={muted ? "Unmute" : "Mute"}
          className="grid size-8 shrink-0 place-items-center rounded-full text-white transition-colors hover:bg-white/15"
        >
          <HugeiconsIcon
            icon={muted ? VolumeOffIcon : VolumeHighIcon}
            className="size-4"
          />
        </button>
      </div>
    </div>
  );
}
