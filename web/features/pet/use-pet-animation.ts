"use client";

import { useEffect, useRef, useState } from "react";

import {
  PET_ANIMATIONS,
  type PetAnimationState,
} from "@/features/pet/pet-manifest";
import type { PetMotion } from "@/features/preferences/preferences-store";

export function usePetAnimation({
  state,
  motion,
  onComplete,
}: {
  state: PetAnimationState;
  motion: PetMotion;
  onComplete?: () => void;
}) {
  const [playback, setPlayback] = useState<{
    state: PetAnimationState;
    motion: PetMotion;
    frame: number;
  }>(() => ({
    state,
    motion,
    frame: motion === "static" ? PET_ANIMATIONS[state].posterFrame : 0,
  }));
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    const spec = PET_ANIMATIONS[state];
    let disposed = false;
    const systemReduced =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const shouldBeStatic = motion === "static" || systemReduced;
    queueMicrotask(() => {
      if (!disposed) {
        setPlayback({
          state,
          motion,
          frame: shouldBeStatic ? spec.posterFrame : 0,
        });
      }
    });
    if (shouldBeStatic || spec.frameCount <= 1) {
      if (!spec.loop) {
        const timeout = window.setTimeout(
          () => onCompleteRef.current?.(),
          spec.frameDurationMs * spec.frameCount * (spec.repeat ?? 1),
        );
        return () => {
          disposed = true;
          window.clearTimeout(timeout);
        };
      }
      return () => {
        disposed = true;
      };
    }

    let animationFrame = 0;
    let previousTime: number | null = null;
    let elapsed = 0;
    let completedLoops = 0;
    let finished = false;
    const frameDuration =
      motion === "reduced" ? spec.frameDurationMs * 2 : spec.frameDurationMs;

    const tick = (time: number) => {
      if (document.visibilityState === "hidden") {
        previousTime = time;
        animationFrame = requestAnimationFrame(tick);
        return;
      }

      if (previousTime !== null) elapsed += time - previousTime;
      previousTime = time;

      if (elapsed >= frameDuration) {
        const steps = Math.floor(elapsed / frameDuration);
        elapsed %= frameDuration;
        setPlayback((current) => {
          let next =
            current.state === state && current.motion === motion
              ? current.frame
              : 0;
          for (let index = 0; index < steps; index += 1) {
            if (next < spec.frameCount - 1) {
              next += 1;
              continue;
            }
            completedLoops += 1;
            if (spec.loop || completedLoops < (spec.repeat ?? 1)) {
              next = 0;
            } else {
              finished = true;
              next = spec.frameCount - 1;
              break;
            }
          }
          return { state, motion, frame: next };
        });
      }

      if (finished) {
        onCompleteRef.current?.();
        return;
      }
      animationFrame = requestAnimationFrame(tick);
    };

    animationFrame = requestAnimationFrame(tick);
    return () => {
      disposed = true;
      cancelAnimationFrame(animationFrame);
    };
  }, [motion, state]);

  return playback.state === state && playback.motion === motion
    ? playback.frame
    : motion === "static"
      ? PET_ANIMATIONS[state].posterFrame
      : 0;
}
