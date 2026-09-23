import { beforeEach, describe, expect, it } from "vitest";

import { resetUiStore, UI_STORAGE_KEY, useUiStore } from "@/stores/ui-store";

describe("UI store", () => {
  beforeEach(() => {
    resetUiStore();
    localStorage.clear();
  });

  it("toggles the task sidebar independently", () => {
    useUiStore.getState().toggleTaskSidebar();

    expect(useUiStore.getState().isTaskSidebarOpen).toBe(false);
    expect(useUiStore.getState().isContextPanelOpen).toBe(true);
    expect(
      JSON.parse(localStorage.getItem(UI_STORAGE_KEY) ?? "{}"),
    ).toMatchObject({
      state: { isTaskSidebarOpen: false },
      version: 1,
    });
  });

  it("restores the persisted task sidebar state", async () => {
    localStorage.setItem(
      UI_STORAGE_KEY,
      JSON.stringify({
        state: { isTaskSidebarOpen: false },
        version: 1,
      }),
    );

    await useUiStore.persist.rehydrate();

    expect(useUiStore.getState().isTaskSidebarOpen).toBe(false);
  });

  it("falls back to an open sidebar when persisted data is invalid", async () => {
    localStorage.setItem(
      UI_STORAGE_KEY,
      JSON.stringify({
        state: { isTaskSidebarOpen: "closed" },
        version: 1,
      }),
    );

    await useUiStore.persist.rehydrate();

    expect(useUiStore.getState().isTaskSidebarOpen).toBe(true);
  });
});
