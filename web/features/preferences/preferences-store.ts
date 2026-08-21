"use client";

import { z } from "zod";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export const ACADEMIC_SOURCES = [
  "arxiv",
  "semantic_scholar",
  "pubmed",
  "crossref",
] as const;

export type AcademicSource = (typeof ACADEMIC_SOURCES)[number];
export type PetSize = "small" | "medium" | "large";
export type PetMotion = "system" | "full" | "reduced" | "static";

export type AppPreferencesV1 = {
  version: 1;
  research: {
    maxPapers: number;
    sources: AcademicSource[];
  };
  pet: {
    visible: boolean;
    size: PetSize;
    motion: PetMotion;
    dragLocked: boolean;
    position: { xRatio: number; yRatio: number };
  };
};

const appPreferencesSchema = z.object({
  version: z.literal(1),
  research: z.object({
    maxPapers: z.number().int().min(1).max(50),
    sources: z.array(z.enum(ACADEMIC_SOURCES)).min(1),
  }),
  pet: z.object({
    visible: z.boolean(),
    size: z.enum(["small", "medium", "large"]),
    motion: z.enum(["system", "full", "reduced", "static"]),
    dragLocked: z.boolean(),
    position: z.object({
      xRatio: z.number().min(0).max(1),
      yRatio: z.number().min(0).max(1),
    }),
  }),
});

export const DEFAULT_APP_PREFERENCES: AppPreferencesV1 = {
  version: 1,
  research: {
    maxPapers: 20,
    sources: [...ACADEMIC_SOURCES],
  },
  pet: {
    visible: true,
    size: "medium",
    motion: "system",
    dragLocked: false,
    position: { xRatio: 1, yRatio: 1 },
  },
};

type PreferencesState = AppPreferencesV1 & {
  hasHydrated: boolean;
  setHasHydrated: (value: boolean) => void;
  setResearchPreferences: (research: AppPreferencesV1["research"]) => void;
  setPetPreferences: (pet: Omit<AppPreferencesV1["pet"], "position">) => void;
  setPetPosition: (position: AppPreferencesV1["pet"]["position"]) => void;
  resetPetPosition: () => void;
  resetPreferences: () => void;
};

function parsePersistedPreferences(value: unknown): AppPreferencesV1 {
  const candidate =
    value && typeof value === "object" && "state" in value
      ? (value as { state: unknown }).state
      : value;
  const result = appPreferencesSchema.safeParse(candidate);
  return result.success ? result.data : DEFAULT_APP_PREFERENCES;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      ...DEFAULT_APP_PREFERENCES,
      hasHydrated: false,
      setHasHydrated: (value) => set({ hasHydrated: value }),
      setResearchPreferences: (research) => set({ research }),
      setPetPreferences: (pet) =>
        set((state) => ({ pet: { ...pet, position: state.pet.position } })),
      setPetPosition: (position) =>
        set((state) => ({ pet: { ...state.pet, position } })),
      resetPetPosition: () =>
        set((state) => ({
          pet: {
            ...state.pet,
            position: DEFAULT_APP_PREFERENCES.pet.position,
          },
        })),
      resetPreferences: () =>
        set({ ...DEFAULT_APP_PREFERENCES, hasHydrated: true }),
    }),
    {
      name: "research-agent.preferences.v1",
      version: 1,
      storage: createJSONStorage(() => localStorage),
      skipHydration: true,
      partialize: ({ version, research, pet }) => ({ version, research, pet }),
      migrate: () => DEFAULT_APP_PREFERENCES,
      merge: (persisted, current) => ({
        ...current,
        ...parsePersistedPreferences(persisted),
      }),
      onRehydrateStorage: () => (state) => state?.setHasHydrated(true),
    },
  ),
);

export function resetPreferencesStoreForTests() {
  usePreferencesStore.setState({
    ...DEFAULT_APP_PREFERENCES,
    hasHydrated: true,
  });
}
