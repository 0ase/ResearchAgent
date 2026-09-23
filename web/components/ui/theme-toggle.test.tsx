import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ThemeToggle } from "@/components/ui/theme-toggle";
import { TooltipProvider } from "@/components/ui/tooltip";
import { getMessages } from "@/i18n/messages";
import { THEME_STORAGE_KEY, type ThemeMode } from "@/lib/theme";

function renderToggle() {
  return render(
    <NextIntlClientProvider locale="en" messages={getMessages("en")}>
      <TooltipProvider delayDuration={0}>
        <ThemeToggle />
      </TooltipProvider>
    </NextIntlClientProvider>,
  );
}

describe("ThemeToggle", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("data-theme");
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    try {
      localStorage.clear();
    } catch {
      // The browser may deny localStorage access in privacy-restricted contexts.
    }
  });

  it("toggles both directions with persistence and dynamic accessibility", async () => {
    const user = userEvent.setup();
    renderToggle();

    const toggle = screen.getByRole("button", {
      name: "Switch to dark theme",
    });
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    expect(toggle.querySelector(".theme-icon-moon")).toBeInTheDocument();
    expect(toggle.querySelector(".theme-icon-sun")).toBeInTheDocument();

    await user.click(toggle);
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    expect(toggle).toHaveAttribute("aria-label", "Switch to light theme");

    await user.click(toggle);
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    expect(toggle).toHaveAttribute("aria-label", "Switch to dark theme");
  });

  it("keeps the current page dark when persistence fails", async () => {
    const user = userEvent.setup();
    const setItem = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("quota exceeded");
      });

    renderToggle();
    await user.click(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    );

    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(
      screen.getByRole("button", { name: "Switch to light theme" }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(setItem).toHaveBeenCalled();
  });

  it("keeps the page usable when the localStorage getter is unavailable", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("Storage is unavailable", "SecurityError");
    });

    renderToggle();
    const toggle = screen.getByRole("button", {
      name: "Switch to dark theme",
    });

    await user.click(toggle);

    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(
      screen.getByRole("button", { name: "Switch to light theme" }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("invalid stored values safely fall back to light", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "auto");
    renderToggle();

    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    expect(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("ignores system dark preference on a clean storage", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(
        (query: string) =>
          ({
            matches: query.includes("prefers-color-scheme: dark"),
            media: query,
            onchange: null,
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            addListener: vi.fn(),
            removeListener: vi.fn(),
            dispatchEvent: vi.fn(),
          }) as unknown as MediaQueryList,
      ),
    );

    renderToggle();
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
  });

  it("shows a Tooltip with the current action label", async () => {
    const user = userEvent.setup();
    localStorage.setItem(THEME_STORAGE_KEY, "dark" satisfies ThemeMode);
    document.documentElement.setAttribute("data-theme", "dark");
    renderToggle();

    const toggle = screen.getByRole("button", {
      name: "Switch to light theme",
    });
    await user.hover(toggle);

    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Switch to light theme",
    );
  });
});
