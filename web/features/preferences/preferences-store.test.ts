import { beforeEach, describe, expect, it } from "vitest";

import {
  DEFAULT_APP_PREFERENCES,
  resetPreferencesStoreForTests,
  usePreferencesStore,
} from "@/features/preferences/preferences-store";

describe("preferences store", () => {
  beforeEach(() => {
    localStorage.clear();
    resetPreferencesStoreForTests();
  });

  it("updates defaults independently from the pet position", () => {
    const store = usePreferencesStore.getState();
    store.setPetPosition({ xRatio: 0.2, yRatio: 0.4 });
    store.setPetPreferences({
      visible: false,
      size: "large",
      motion: "static",
      dragLocked: true,
    });
    store.setResearchPreferences({ maxPapers: 12, sources: ["arxiv"] });

    expect(usePreferencesStore.getState().research).toEqual({
      maxPapers: 12,
      sources: ["arxiv"],
    });
    expect(usePreferencesStore.getState().pet.position).toEqual({
      xRatio: 0.2,
      yRatio: 0.4,
    });
  });

  it("falls back safely when persisted data is invalid or from an old version", async () => {
    usePreferencesStore.setState({
      research: { maxPapers: 3, sources: ["crossref"] },
    });
    localStorage.setItem(
      "research-agent.preferences.v1",
      JSON.stringify({
        state: {
          version: 0,
          research: { maxPapers: 500, sources: [] },
          pet: { visible: "yes" },
        },
        version: 0,
      }),
    );
    await usePreferencesStore.persist.rehydrate();

    expect(usePreferencesStore.getState().research).toEqual(
      DEFAULT_APP_PREFERENCES.research,
    );
    expect(usePreferencesStore.getState().pet).toEqual(
      DEFAULT_APP_PREFERENCES.pet,
    );
  });

  it("rejects damaged data even when its storage version is current", async () => {
    localStorage.setItem(
      "research-agent.preferences.v1",
      JSON.stringify({
        state: {
          version: 1,
          research: { maxPapers: -1, sources: [] },
          pet: {
            visible: true,
            size: "giant",
            motion: "full",
            dragLocked: false,
            position: { xRatio: 5, yRatio: 5 },
          },
        },
        version: 1,
      }),
    );

    await usePreferencesStore.persist.rehydrate();

    expect(usePreferencesStore.getState()).toMatchObject(
      DEFAULT_APP_PREFERENCES,
    );
  });

  it("restores every preference to its documented default", () => {
    usePreferencesStore.getState().setResearchPreferences({
      maxPapers: 7,
      sources: ["pubmed"],
    });
    usePreferencesStore.getState().resetPreferences();
    expect(usePreferencesStore.getState()).toMatchObject(
      DEFAULT_APP_PREFERENCES,
    );
  });
});
