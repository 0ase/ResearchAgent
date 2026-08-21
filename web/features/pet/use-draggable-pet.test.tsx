import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  pixelsToRatios,
  ratiosToPixels,
  useDraggablePet,
} from "@/features/pet/use-draggable-pet";
import {
  resetPreferencesStoreForTests,
  usePreferencesStore,
} from "@/features/preferences/preferences-store";

function Harness({ onOpen }: { onOpen: () => void }) {
  const draggable = useDraggablePet({
    size: "medium",
    locked: false,
    onClick: onOpen,
  });
  return (
    <button
      type="button"
      data-ready={draggable.position ? "true" : "false"}
      {...draggable.pointerHandlers}
    >
      pet
    </button>
  );
}

describe("useDraggablePet", () => {
  beforeEach(() => {
    resetPreferencesStoreForTests();
    Object.defineProperty(HTMLButtonElement.prototype, "setPointerCapture", {
      configurable: true,
      value: vi.fn(),
    });
    Object.defineProperty(HTMLButtonElement.prototype, "hasPointerCapture", {
      configurable: true,
      value: vi.fn(() => false),
    });
  });

  it("opens settings for a short click", async () => {
    const onOpen = vi.fn();
    render(<Harness onOpen={onOpen} />);
    const pet = screen.getByRole("button", { name: "pet" });
    await waitFor(() => expect(pet).toHaveAttribute("data-ready", "true"));
    fireEvent.pointerDown(pet, {
      pointerId: 1,
      button: 0,
      clientX: 100,
      clientY: 100,
    });
    fireEvent.pointerUp(pet, { pointerId: 1, clientX: 102, clientY: 102 });
    fireEvent.click(pet);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("persists a drag without opening settings", async () => {
    const onOpen = vi.fn();
    render(<Harness onOpen={onOpen} />);
    const pet = screen.getByRole("button", { name: "pet" });
    await waitFor(() => expect(pet).toHaveAttribute("data-ready", "true"));
    fireEvent.pointerDown(pet, {
      pointerId: 2,
      button: 0,
      clientX: 100,
      clientY: 100,
    });
    fireEvent.pointerMove(pet, { pointerId: 2, clientX: 70, clientY: 70 });
    fireEvent.pointerUp(pet, { pointerId: 2, clientX: 70, clientY: 70 });
    fireEvent.click(pet);
    expect(onOpen).not.toHaveBeenCalled();
    expect(usePreferencesStore.getState().pet.position).not.toEqual({
      xRatio: 1,
      yRatio: 1,
    });
  });

  it("round-trips and clamps positions after viewport changes", () => {
    const viewport = { width: 800, height: 600 };
    const pixels = ratiosToPixels(
      { xRatio: 0.25, yRatio: 0.75 },
      "large",
      viewport,
    );
    expect(pixelsToRatios(pixels, "large", viewport)).toEqual({
      xRatio: 0.25,
      yRatio: 0.75,
    });
    expect(
      ratiosToPixels({ xRatio: 1, yRatio: 1 }, "large", {
        width: 100,
        height: 100,
      }),
    ).toEqual({ x: 0, y: 0 });
  });
});
