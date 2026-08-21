"use client";

import {
  PET_ANIMATIONS,
  PET_ATLAS,
  type PetAnimationState,
} from "@/features/pet/pet-manifest";
import { PET_DISPLAY_SIZES } from "@/features/pet/use-draggable-pet";
import type { PetSize } from "@/features/preferences/preferences-store";

export function PetSprite({
  state,
  frame,
  size,
}: {
  state: PetAnimationState;
  frame: number;
  size: PetSize;
}) {
  const dimensions = PET_DISPLAY_SIZES[size];
  const spec = PET_ANIMATIONS[state];
  return (
    <span
      aria-hidden="true"
      data-pet-frame={frame}
      className="block bg-no-repeat"
      style={{
        width: dimensions.width,
        height: dimensions.height,
        backgroundImage: `url(${PET_ATLAS.src})`,
        backgroundSize: `${dimensions.width * PET_ATLAS.columns}px ${dimensions.height * PET_ATLAS.rows}px`,
        backgroundPosition: `${-frame * dimensions.width}px ${-spec.row * dimensions.height}px`,
      }}
    />
  );
}
