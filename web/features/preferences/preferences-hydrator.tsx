"use client";

import { useEffect } from "react";

import { usePreferencesStore } from "@/features/preferences/preferences-store";

export function PreferencesHydrator() {
  useEffect(() => {
    void usePreferencesStore.persist.rehydrate();
  }, []);

  return null;
}
