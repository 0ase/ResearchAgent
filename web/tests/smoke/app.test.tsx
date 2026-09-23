import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import Home from "@/app/page";
import { Providers } from "@/app/providers";

describe("home page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );
  });

  it("renders the Research Agent workspace entry point", async () => {
    render(
      <Providers locale="en">
        <Home />
      </Providers>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /start a research task/i }),
      ).toBeInTheDocument();
    });
    expect(screen.getAllByText(/research workspace/i).length).toBeGreaterThan(
      0,
    );
  });
});
