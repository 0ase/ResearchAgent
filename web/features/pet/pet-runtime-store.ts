"use client";

import { create } from "zustand";

import type { ReplayState } from "@/lib/events/types";
import type { PetRuntimeSnapshot } from "@/features/pet/pet-manifest";

type PetRuntimeState = PetRuntimeSnapshot & {
  syncReplayState: (state: ReplayState) => void;
  syncTaskSnapshot: (snapshot: {
    id: string;
    status: PetRuntimeSnapshot["taskStatus"];
    current_stage?: PetRuntimeSnapshot["currentStage"];
  }) => void;
  clearRuntime: () => void;
};

export const EMPTY_PET_RUNTIME: PetRuntimeSnapshot = {
  taskId: null,
  taskStatus: null,
  currentStage: null,
  updatedAt: 0,
};

export const usePetRuntimeStore = create<PetRuntimeState>((set) => ({
  ...EMPTY_PET_RUNTIME,
  syncReplayState: (state) =>
    set({
      taskId: state.taskId,
      taskStatus: state.taskStatus,
      currentStage: state.currentStage,
      updatedAt: Date.now(),
    }),
  syncTaskSnapshot: (snapshot) =>
    set({
      taskId: snapshot.id,
      taskStatus: snapshot.status,
      currentStage: snapshot.current_stage ?? null,
      updatedAt: Date.now(),
    }),
  clearRuntime: () => set({ ...EMPTY_PET_RUNTIME }),
}));

export function resetPetRuntimeStoreForTests() {
  usePetRuntimeStore.setState({ ...EMPTY_PET_RUNTIME });
}
