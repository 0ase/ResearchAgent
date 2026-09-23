"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { PetSize } from "@/features/preferences/preferences-store";
import { usePreferencesStore } from "@/features/preferences/preferences-store";

export const PET_DISPLAY_SIZES = {
  small: { width: 72, height: 78 },
  medium: { width: 96, height: 104 },
  large: { width: 120, height: 130 },
} as const;

const SAFE_MARGIN = 24;
const DRAG_THRESHOLD = 6;

type PixelPosition = { x: number; y: number };

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), Math.max(minimum, maximum));
}

export function ratiosToPixels(
  position: { xRatio: number; yRatio: number },
  size: PetSize,
  viewport = { width: window.innerWidth, height: window.innerHeight },
): PixelPosition {
  const dimensions = PET_DISPLAY_SIZES[size];
  const widthRange = Math.max(
    0,
    viewport.width - dimensions.width - SAFE_MARGIN * 2,
  );
  const heightRange = Math.max(
    0,
    viewport.height - dimensions.height - SAFE_MARGIN * 2,
  );
  return {
    x: clamp(
      SAFE_MARGIN + position.xRatio * widthRange,
      0,
      viewport.width - dimensions.width,
    ),
    y: clamp(
      SAFE_MARGIN + position.yRatio * heightRange,
      0,
      viewport.height - dimensions.height,
    ),
  };
}

export function pixelsToRatios(
  position: PixelPosition,
  size: PetSize,
  viewport = { width: window.innerWidth, height: window.innerHeight },
) {
  const dimensions = PET_DISPLAY_SIZES[size];
  const widthRange = Math.max(
    0,
    viewport.width - dimensions.width - SAFE_MARGIN * 2,
  );
  const heightRange = Math.max(
    0,
    viewport.height - dimensions.height - SAFE_MARGIN * 2,
  );
  return {
    xRatio: widthRange
      ? clamp((position.x - SAFE_MARGIN) / widthRange, 0, 1)
      : 0,
    yRatio: heightRange
      ? clamp((position.y - SAFE_MARGIN) / heightRange, 0, 1)
      : 0,
  };
}

export function useDraggablePet({
  size,
  locked,
  onClick,
}: {
  size: PetSize;
  locked: boolean;
  onClick: () => void;
}) {
  const storedPosition = usePreferencesStore((state) => state.pet.position);
  const setStoredPosition = usePreferencesStore(
    (state) => state.setPetPosition,
  );
  const [position, setPosition] = useState<PixelPosition | null>(null);
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    origin: PixelPosition;
    moved: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);

  const syncPosition = useCallback(() => {
    setPosition(ratiosToPixels(storedPosition, size));
  }, [size, storedPosition]);

  useEffect(() => {
    let disposed = false;
    queueMicrotask(() => {
      if (!disposed) syncPosition();
    });
    window.addEventListener("resize", syncPosition);
    return () => {
      disposed = true;
      window.removeEventListener("resize", syncPosition);
    };
  }, [syncPosition]);

  const onPointerDown = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>) => {
      if (event.button !== 0 || !position) return;
      event.currentTarget.setPointerCapture(event.pointerId);
      dragRef.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        origin: position,
        moved: false,
      };
    },
    [position],
  );

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId || locked) return;
      const deltaX = event.clientX - drag.startX;
      const deltaY = event.clientY - drag.startY;
      if (Math.hypot(deltaX, deltaY) > DRAG_THRESHOLD) {
        drag.moved = true;
        setDragging(true);
      }
      if (!drag.moved) return;
      const dimensions = PET_DISPLAY_SIZES[size];
      setPosition({
        x: clamp(
          drag.origin.x + deltaX,
          0,
          window.innerWidth - dimensions.width,
        ),
        y: clamp(
          drag.origin.y + deltaY,
          0,
          window.innerHeight - dimensions.height,
        ),
      });
    },
    [locked, size],
  );

  const finishPointer = useCallback(
    (event: React.PointerEvent<HTMLButtonElement>) => {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId) return;
      dragRef.current = null;
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
      if (drag.moved && position) {
        setStoredPosition(pixelsToRatios(position, size));
      }
      suppressClickRef.current = drag.moved || event.type === "pointercancel";
      setDragging(false);
    },
    [position, setStoredPosition, size],
  );

  return {
    dragging,
    position,
    pointerHandlers: {
      onPointerDown,
      onPointerMove,
      onPointerUp: finishPointer,
      onPointerCancel: finishPointer,
      onClick: (event: React.MouseEvent<HTMLButtonElement>) => {
        if (suppressClickRef.current) {
          event.preventDefault();
          suppressClickRef.current = false;
          return;
        }
        onClick();
      },
    },
  };
}
