"use client";

import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type ContextTab = "evidence" | "papers" | "run";

export const UI_STORAGE_KEY = "research-agent.ui.v1";

type UiState = {
  isTaskSidebarOpen: boolean;
  isContextPanelOpen: boolean;
  contextTab: ContextTab;
  selectedObjectId: string | null;
  setTaskSidebarOpen: (open: boolean) => void;
  toggleTaskSidebar: () => void;
  setContextPanelOpen: (open: boolean) => void;
  toggleContextPanel: () => void;
  setContextTab: (tab: ContextTab) => void;
  selectObject: (id: string | null) => void;
};

const defaultUiState = {
  isTaskSidebarOpen: true,
  isContextPanelOpen: true,
  contextTab: "evidence",
  selectedObjectId: null,
} satisfies Pick<
  UiState,
  "isTaskSidebarOpen" | "isContextPanelOpen" | "contextTab" | "selectedObjectId"
>;

type PersistedUiState = Pick<UiState, "isTaskSidebarOpen">;

function parsePersistedUiState(value: unknown): PersistedUiState {
  const candidate =
    value && typeof value === "object" && "state" in value
      ? (value as { state: unknown }).state
      : value;
  return candidate &&
    typeof candidate === "object" &&
    "isTaskSidebarOpen" in candidate &&
    typeof candidate.isTaskSidebarOpen === "boolean"
    ? { isTaskSidebarOpen: candidate.isTaskSidebarOpen }
    : { isTaskSidebarOpen: defaultUiState.isTaskSidebarOpen };
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      ...defaultUiState,
      setTaskSidebarOpen: (open) => set({ isTaskSidebarOpen: open }),
      toggleTaskSidebar: () =>
        set((state) => ({
          isTaskSidebarOpen: !state.isTaskSidebarOpen,
        })),
      setContextPanelOpen: (open) => set({ isContextPanelOpen: open }),
      toggleContextPanel: () =>
        set((state) => ({ isContextPanelOpen: !state.isContextPanelOpen })),
      setContextTab: (tab) => set({ contextTab: tab }),
      selectObject: (id) => set({ selectedObjectId: id }),
    }),
    {
      name: UI_STORAGE_KEY,
      version: 1,
      storage: createJSONStorage(() => localStorage),
      skipHydration: true,
      partialize: ({ isTaskSidebarOpen }) => ({ isTaskSidebarOpen }),
      migrate: () => ({
        isTaskSidebarOpen: defaultUiState.isTaskSidebarOpen,
      }),
      merge: (persisted, current) => ({
        ...current,
        ...parsePersistedUiState(persisted),
      }),
    },
  ),
);

export function resetUiStore() {
  useUiStore.setState(defaultUiState);
}
