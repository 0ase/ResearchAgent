import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HistoryPage from "@/app/history/page";
import { Providers } from "@/app/providers";

describe("history page theme entry", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("data-theme");
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders the theme toggle in the right-side action group", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      () => new Promise(() => undefined),
    );

    render(
      <Providers locale="en">
        <HistoryPage />
      </Providers>,
    );

    expect(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    ).toBeInTheDocument();
  });
});