"use client";

import { ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";

export function ReplayControls({
  isPlaying,
  speed,
  onPlay,
  onPause,
  onPrevious,
  onNext,
  onSpeedChange,
}: {
  isPlaying: boolean;
  speed: 1 | 2 | 4;
  onPlay: () => void;
  onPause: () => void;
  onPrevious: () => void;
  onNext: () => void;
  onSpeedChange: (speed: 1 | 2 | 4) => void;
}) {
  const t = useTranslations("replay");
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        aria-label={t("previous")}
        size="icon"
        variant="ghost"
        onClick={onPrevious}
      >
        <ChevronLeft aria-hidden="true" className="h-4 w-4" />
      </Button>
      <Button
        aria-label={isPlaying ? t("pause") : t("play")}
        size="icon"
        variant="primary"
        onClick={isPlaying ? onPause : onPlay}
      >
        {isPlaying ? (
          <Pause aria-hidden="true" className="h-4 w-4" />
        ) : (
          <Play aria-hidden="true" className="h-4 w-4" />
        )}
      </Button>
      <Button
        aria-label={t("next")}
        size="icon"
        variant="ghost"
        onClick={onNext}
      >
        <ChevronRight aria-hidden="true" className="h-4 w-4" />
      </Button>
      <div
        className="ml-2 flex items-center gap-1 rounded-[var(--radius-control)] border border-[var(--color-border)] p-1"
        aria-label={t("speed")}
      >
        {[1, 2, 4].map((value) => (
          <button
            key={value}
            type="button"
            aria-label={t("speedValue", { value })}
            aria-pressed={speed === value}
            onClick={() => onSpeedChange(value as 1 | 2 | 4)}
            className="rounded px-2 py-1 text-xs text-[var(--color-text-muted)] aria-pressed:bg-[var(--color-primary-subtle)] aria-pressed:text-[var(--color-primary-hover)]"
          >
            {value}×
          </button>
        ))}
      </div>
    </div>
  );
}
