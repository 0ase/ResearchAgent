import { afterEach, describe, expect, it, vi } from "vitest";

import {
  applyTheme,
  THEME_INIT_SCRIPT,
  DEFAULT_THEME,
  getBrowserThemeStorage,
  persistTheme,
  parseTheme,
  readStoredTheme,
  readThemeFromRoot,
  THEME_STORAGE_KEY,
  type ThemeStorage,
} from "@/lib/theme";

function storage({
  value,
  getThrows = false,
  setThrows = false,
}: {
  value?: string | null;
  getThrows?: boolean;
  setThrows?: boolean;
} = {}) {
  const entries = new Map<string, string>();
  if (typeof value === "string") entries.set(THEME_STORAGE_KEY, value);
  return {
    getItem: vi.fn((key: string) => {
      if (getThrows) throw new Error("storage read failed");
      return entries.get(key) ?? null;
    }),
    setItem: vi.fn((key: string, next: string) => {
      if (setThrows) throw new Error("storage write failed");
      entries.set(key, next);
    }),
  } satisfies ThemeStorage;
}

describe("theme contract", () => {
  afterEach(() => {
    document.documentElement.removeAttribute("data-theme");
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("falls back to light when storage is missing or corrupt", () => {
    expect(readStoredTheme(storage({ value: null }))).toBe(DEFAULT_THEME);
    expect(readStoredTheme(storage({ value: "" }))).toBe("light");
    expect(readStoredTheme(storage({ value: "invalid" }))).toBe("light");
    expect(parseTheme("dark")).toBe("dark");
    expect(parseTheme(undefined)).toBe("light");
  });

  it("returns light when storage cannot be read", () => {
    expect(readStoredTheme(storage({ getThrows: true }))).toBe("light");
  });

  it("returns null when the browser storage getter is unavailable", () => {
    const descriptor = Object.getOwnPropertyDescriptor(window, "localStorage");
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new DOMException("Storage is unavailable", "SecurityError");
      },
    });

    try {
      expect(getBrowserThemeStorage()).toBeNull();
    } finally {
      if (descriptor) {
        Object.defineProperty(window, "localStorage", descriptor);
      }
    }
  });

  it("applies and reads the theme from the root element", () => {
    applyTheme("dark");
    expect(readThemeFromRoot()).toBe("dark");
    applyTheme("light");
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
  });

  it("the first-paint script only reads the persisted value and never follows the system", () => {
    expect(THEME_INIT_SCRIPT).toContain(
      'localStorage.getItem("research-agent.theme.v1")',
    );
    expect(THEME_INIT_SCRIPT).toContain('"dark"');
    expect(THEME_INIT_SCRIPT).not.toContain("prefers-color-scheme");
    expect(THEME_INIT_SCRIPT).not.toContain("matchMedia");
  });

  it("persists only valid theme values and does not throw on write failure", () => {
    const writable = storage();
    expect(persistTheme("dark", writable)).toBe(true);
    expect(writable.setItem).toHaveBeenCalledWith(THEME_STORAGE_KEY, "dark");

    const readonly = storage({ setThrows: true });
    expect(persistTheme("light", readonly)).toBe(false);
  });

  it("skips persistence when browser storage is unavailable", () => {
    expect(() => persistTheme("dark", null)).not.toThrow();
    expect(persistTheme("dark", null)).toBe(false);
    expect(persistTheme("dark")).toBe(false);
  });
});
