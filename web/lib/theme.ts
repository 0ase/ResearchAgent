export type ThemeMode = "light" | "dark";

export const THEME_STORAGE_KEY = "research-agent.theme.v1";
export const DEFAULT_THEME: ThemeMode = "light";
export const THEME_ATTRIBUTE = "data-theme";

export interface ThemeStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function getBrowserThemeStorage(): ThemeStorage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export const THEME_INIT_SCRIPT = `(function(){try{var s=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});var m=s==="dark"?"dark":"light";document.documentElement.setAttribute(${JSON.stringify(THEME_ATTRIBUTE)},m);}catch(e){document.documentElement.setAttribute(${JSON.stringify(THEME_ATTRIBUTE)},"light");}})();`;

const themeListeners = new Set<() => void>();

function notifyThemeListeners() {
  for (const listener of themeListeners) listener();
}

export function parseTheme(value: unknown): ThemeMode {
  return value === "dark" ? "dark" : "light";
}

export function readStoredTheme(storage?: ThemeStorage | null): ThemeMode {
  if (!storage) return DEFAULT_THEME;
  try {
    return parseTheme(storage.getItem(THEME_STORAGE_KEY));
  } catch {
    return DEFAULT_THEME;
  }
}

export function readThemeFromRoot(
  root: HTMLElement = document.documentElement,
): ThemeMode {
  return parseTheme(root.getAttribute(THEME_ATTRIBUTE));
}

export function applyTheme(
  mode: ThemeMode,
  root: HTMLElement = document.documentElement,
) {
  if (root.getAttribute(THEME_ATTRIBUTE) !== mode) {
    root.setAttribute(THEME_ATTRIBUTE, mode);
    notifyThemeListeners();
  }
}

export function persistTheme(
  mode: ThemeMode,
  storage?: ThemeStorage | null,
): boolean {
  if (!storage) return false;
  try {
    storage.setItem(THEME_STORAGE_KEY, mode);
    return true;
  } catch {
    return false;
  }
}

export function nextTheme(mode: ThemeMode): ThemeMode {
  return mode === "dark" ? "light" : "dark";
}

export function subscribeToTheme(listener: () => void): () => void {
  themeListeners.add(listener);
  return () => {
    themeListeners.delete(listener);
  };
}

export function getThemeSnapshot(): ThemeMode {
  return typeof document === "undefined" ? DEFAULT_THEME : readThemeFromRoot();
}

export function getThemeServerSnapshot(): ThemeMode {
  return DEFAULT_THEME;
}
