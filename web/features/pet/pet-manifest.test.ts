import { describe, expect, it } from "vitest";

import {
  PET_ANIMATIONS,
  PET_ATLAS,
  resolvePetState,
  type PetRuntimeSnapshot,
} from "@/features/pet/pet-manifest";
import { RESEARCH_STAGES, type TaskStatus } from "@/lib/events/types";

function runtime(
  taskStatus: TaskStatus | null,
  currentStage: PetRuntimeSnapshot["currentStage"] = null,
): PetRuntimeSnapshot {
  return { taskId: "task-1", taskStatus, currentStage, updatedAt: 1 };
}

describe("pet manifest", () => {
  it.each(RESEARCH_STAGES)("maps the %s research stage", (stage) => {
    expect(
      resolvePetState({
        runtime: runtime("running", stage),
        dragging: false,
        completionFinished: false,
      }),
    ).toBe(stage);
  });

  it.each(["cancelling", "failed", "cancelled", "interrupted"] as const)(
    "maps %s to failed",
    (status) => {
      expect(
        resolvePetState({
          runtime: runtime(status, "search"),
          dragging: false,
          completionFinished: false,
        }),
      ).toBe("failed");
    },
  );

  it("applies dragging and completion priorities", () => {
    expect(
      resolvePetState({
        runtime: runtime("failed", "critic"),
        dragging: true,
        completionFinished: false,
      }),
    ).toBe("dragging");
    expect(
      resolvePetState({
        runtime: runtime("completed"),
        dragging: false,
        completionFinished: false,
      }),
    ).toBe("completed");
    expect(
      resolvePetState({
        runtime: runtime("completed"),
        dragging: false,
        completionFinished: true,
      }),
    ).toBe("idle");
  });

  it("keeps every animation inside the atlas", () => {
    const rows = new Set<number>();
    for (const spec of Object.values(PET_ANIMATIONS)) {
      expect(spec.row).toBeGreaterThanOrEqual(0);
      expect(spec.row).toBeLessThan(PET_ATLAS.rows);
      expect(spec.frameCount).toBeGreaterThan(0);
      expect(spec.frameCount).toBeLessThanOrEqual(PET_ATLAS.columns);
      expect(spec.posterFrame).toBeLessThan(spec.frameCount);
      rows.add(spec.row);
    }
    expect(rows.size).toBe(PET_ATLAS.rows);
  });
});
