import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PET_ANIMATIONS } from "@/features/pet/pet-manifest";
import type { PetAnimationState } from "@/features/pet/pet-manifest";
import { usePetAnimation } from "@/features/pet/use-pet-animation";

describe("usePetAnimation", () => {
  afterEach(() => vi.useRealTimers());

  it("uses poster frames in static mode and completes two celebration rounds", () => {
    vi.useFakeTimers();
    const onComplete = vi.fn();
    const { result, rerender } = renderHook(
      ({ state }: { state: PetAnimationState }) =>
        usePetAnimation({ state, motion: "static", onComplete }),
      { initialProps: { state: "completed" as PetAnimationState } },
    );

    expect(result.current).toBe(PET_ANIMATIONS.completed.posterFrame);
    act(() => {
      vi.advanceTimersByTime(
        PET_ANIMATIONS.completed.frameDurationMs *
          PET_ANIMATIONS.completed.frameCount *
          2,
      );
    });
    expect(onComplete).toHaveBeenCalledTimes(1);

    rerender({ state: "idle" });
    expect(result.current).toBe(PET_ANIMATIONS.idle.posterFrame);
  });
});
