"use client";

import { create } from "zustand";

export type ContextTab = "evidence" | "papers" | "run";

type UiState = {
  isTaskSidebarOpen: boolean;
  isContextPanelOpen: boolean;
  contextTab: ContextTab;
  selectedObjectId: string | null;
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

export const useUiStore = create<UiState>((set) => ({
  ...defaultUiState,
  setContextPanelOpen: (open) => set({ isContextPanelOpen: open }),
  toggleContextPanel: () =>
    set((state) => ({ isContextPanelOpen: !state.isContextPanelOpen })),
  setContextTab: (tab) => set({ contextTab: tab }),
  selectObject: (id) => set({ selectedObjectId: id }),
}));

export function resetUiStore() {
  useUiStore.setState(defaultUiState);
}
