"use client";

import { Settings } from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useState } from "react";

import { PetSprite } from "@/components/pet/pet-sprite";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { resolvePetState } from "@/features/pet/pet-manifest";
import { usePetAnimation } from "@/features/pet/use-pet-animation";
import { useDraggablePet } from "@/features/pet/use-draggable-pet";
import { usePetRuntimeStore } from "@/features/pet/pet-runtime-store";
import { usePreferencesStore } from "@/features/preferences/preferences-store";
import { useRouter } from "@/i18n/navigation";

export function PetOverlay() {
  const t = useTranslations("pet");
  const router = useRouter();
  const pet = usePreferencesStore((state) => state.pet);
  const hasHydrated = usePreferencesStore((state) => state.hasHydrated);
  const taskId = usePetRuntimeStore((state) => state.taskId);
  const taskStatus = usePetRuntimeStore((state) => state.taskStatus);
  const currentStage = usePetRuntimeStore((state) => state.currentStage);
  const updatedAt = usePetRuntimeStore((state) => state.updatedAt);
  const runtime = { taskId, taskStatus, currentStage, updatedAt };
  const [completedRuntimeVersion, setCompletedRuntimeVersion] = useState(0);
  const openSettings = useCallback(() => router.push("/settings"), [router]);
  const draggable = useDraggablePet({
    size: pet.size,
    locked: pet.dragLocked,
    onClick: openSettings,
  });

  const completionFinished =
    runtime.taskStatus === "completed" &&
    completedRuntimeVersion === runtime.updatedAt;

  const animationState = resolvePetState({
    runtime,
    dragging: draggable.dragging,
    completionFinished,
  });
  const frame = usePetAnimation({
    state: animationState,
    motion: pet.motion,
    onComplete: () => setCompletedRuntimeVersion(runtime.updatedAt),
  });

  if (!hasHydrated) return null;

  if (!pet.visible) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label={t("openSettings")}
            onClick={openSettings}
            className="fixed bottom-5 left-5 z-40 grid h-10 w-10 place-items-center rounded-full border border-[var(--color-border-strong)] bg-[var(--color-surface)] text-[var(--color-text-muted)] shadow-[var(--shadow-float)] hover:text-[var(--color-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
          >
            <Settings aria-hidden="true" className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="right">{t("openSettings")}</TooltipContent>
      </Tooltip>
    );
  }

  if (!draggable.position) return null;

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          data-pet-state={animationState}
          aria-label={t("accessibleLabel", {
            state: t(`states.${animationState}`),
          })}
          className="fixed z-40 cursor-grab select-none rounded-xl bg-transparent p-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] active:cursor-grabbing"
          style={{
            left: draggable.position.x,
            top: draggable.position.y,
            touchAction: "none",
          }}
          {...draggable.pointerHandlers}
        >
          <PetSprite state={animationState} frame={frame} size={pet.size} />
        </button>
      </TooltipTrigger>
      <TooltipContent>{t("hint")}</TooltipContent>
    </Tooltip>
  );
}
