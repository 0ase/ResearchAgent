import type { ResearchStage, TaskStatus } from "@/lib/events/types";

export type PetAnimationState =
  "idle" | ResearchStage | "dragging" | "completed" | "failed";

export type PetAnimationSpec = {
  row: number;
  frameCount: number;
  frameDurationMs: number;
  loop: boolean;
  repeat?: number;
  posterFrame: number;
};

export const PET_ATLAS = {
  src: "/pets/research-bot/spritesheet.webp",
  cellWidth: 192,
  cellHeight: 208,
  columns: 8,
  rows: 11,
} as const;

export const PET_ANIMATIONS = {
  idle: {
    row: 0,
    frameCount: 6,
    frameDurationMs: 260,
    loop: true,
    posterFrame: 0,
  },
  orchestrate: {
    row: 1,
    frameCount: 8,
    frameDurationMs: 200,
    loop: true,
    posterFrame: 3,
  },
  search: {
    row: 2,
    frameCount: 8,
    frameDurationMs: 140,
    loop: true,
    posterFrame: 3,
  },
  filter: {
    row: 3,
    frameCount: 6,
    frameDurationMs: 180,
    loop: true,
    posterFrame: 2,
  },
  read: {
    row: 4,
    frameCount: 8,
    frameDurationMs: 220,
    loop: true,
    posterFrame: 3,
  },
  analyze: {
    row: 5,
    frameCount: 8,
    frameDurationMs: 180,
    loop: true,
    posterFrame: 3,
  },
  synthesize: {
    row: 6,
    frameCount: 8,
    frameDurationMs: 160,
    loop: true,
    posterFrame: 3,
  },
  critic: {
    row: 7,
    frameCount: 6,
    frameDurationMs: 220,
    loop: true,
    posterFrame: 2,
  },
  dragging: {
    row: 8,
    frameCount: 4,
    frameDurationMs: 120,
    loop: true,
    posterFrame: 1,
  },
  completed: {
    row: 9,
    frameCount: 8,
    frameDurationMs: 120,
    loop: false,
    repeat: 2,
    posterFrame: 7,
  },
  failed: {
    row: 10,
    frameCount: 6,
    frameDurationMs: 260,
    loop: true,
    posterFrame: 2,
  },
} as const satisfies Record<PetAnimationState, PetAnimationSpec>;

export type PetRuntimeSnapshot = {
  taskId: string | null;
  taskStatus: TaskStatus | null;
  currentStage: ResearchStage | null;
  updatedAt: number;
};

const failureStatuses = new Set<TaskStatus>([
  "cancelling",
  "failed",
  "cancelled",
  "interrupted",
]);

export function resolvePetState({
  runtime,
  dragging,
  completionFinished,
}: {
  runtime: PetRuntimeSnapshot;
  dragging: boolean;
  completionFinished: boolean;
}): PetAnimationState {
  if (dragging) return "dragging";
  if (runtime.taskStatus && failureStatuses.has(runtime.taskStatus)) {
    return "failed";
  }
  if (runtime.taskStatus === "completed") {
    return completionFinished ? "idle" : "completed";
  }
  if (runtime.taskStatus === "running" && runtime.currentStage) {
    return runtime.currentStage;
  }
  return "idle";
}
