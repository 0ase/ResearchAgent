"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { getResearchEvents } from "@/lib/api/client";
import { replayEvents } from "@/lib/events/reducer";
import type {
  ResearchEvent,
  ResearchStage,
  ReplayState,
} from "@/lib/events/types";
import { delayForCursor } from "@/features/replay/replay-clock";

export function useTaskReplay(
  taskId: string,
  options: { events?: ResearchEvent[] } = {},
) {
  const [cursor, setCursor] = useState(0);
  const [speed, setSpeed] = useState<1 | 2 | 4>(1);
  const [isPlaying, setIsPlaying] = useState(false);
  const query = useQuery({
    queryKey: ["research", "task", taskId, "replay-events"],
    queryFn: () => getResearchEvents(taskId),
    enabled: Boolean(taskId) && !options.events,
    retry: false,
  });
  const events = useMemo(
    () => options.events ?? query.data ?? [],
    [options.events, query.data],
  );
  const boundedCursor = Math.min(cursor, events.length);
  const playing = isPlaying && boundedCursor < events.length;

  useEffect(() => {
    if (!playing) return;
    const timer = window.setTimeout(
      () => setCursor((current) => Math.min(events.length, current + 1)),
      delayForCursor(events, boundedCursor, speed),
    );
    return () => window.clearTimeout(timer);
  }, [boundedCursor, events, playing, speed]);

  const state = useMemo<ReplayState>(
    () => replayEvents(taskId, events.slice(0, boundedCursor)),
    [boundedCursor, events, taskId],
  );

  const seek = (nextCursor: number) => {
    setCursor(Math.max(0, Math.min(events.length, Math.round(nextCursor))));
  };
  const seekSequence = (sequence: number) => {
    seek(events.filter((event) => event.sequence <= sequence).length);
  };
  const jumpToStage = (stage: ResearchStage) => {
    const index = events.findIndex((event) => event.stage === stage);
    if (index >= 0) seek(index + 1);
  };

  return {
    events,
    state,
    cursor,
    eventCursor: events[cursor - 1]?.sequence ?? 0,
    speed,
    setSpeed,
    isPlaying: playing,
    play: () => {
      if (boundedCursor < events.length) setIsPlaying(true);
    },
    pause: () => setIsPlaying(false),
    previous: () => {
      setIsPlaying(false);
      seek(boundedCursor - 1);
    },
    next: () => {
      setIsPlaying(false);
      seek(boundedCursor + 1);
    },
    seek,
    seekSequence,
    jumpToStage,
    isFinished: events.length > 0 && boundedCursor >= events.length,
    supported: events.length > 0,
    isLoading: !options.events && query.isPending,
    error: query.error,
  };
}
