"use client";

import { Moon, Sun } from "lucide-react";
import { useTranslations } from "next-intl";
import { useLayoutEffect, useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  applyTheme,
  getBrowserThemeStorage,
  getThemeServerSnapshot,
  getThemeSnapshot,
  nextTheme,
  persistTheme,
  readStoredTheme,
  readThemeFromRoot,
  subscribeToTheme,
} from "@/lib/theme";

export function ThemeToggle({ className }: { className?: string }) {
  const t = useTranslations("common");
  const theme = useSyncExternalStore(
    subscribeToTheme,
    getThemeSnapshot,
    getThemeServerSnapshot,
  );
  const isDark = theme === "dark";

  useLayoutEffect(() => {
    const rootTheme = readThemeFromRoot();
    const storedTheme = readStoredTheme(getBrowserThemeStorage());
    applyTheme(rootTheme === "dark" ? rootTheme : storedTheme);
  }, []);

  function toggleTheme() {
    const mode = nextTheme(readThemeFromRoot());
    applyTheme(mode);
    persistTheme(mode, getBrowserThemeStorage());
  }

  const label = isDark ? t("switchToLightTheme") : t("switchToDarkTheme");

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={label}
          aria-pressed={isDark}
          onClick={toggleTheme}
          className={className}
        >
          <Sun
            aria-hidden="true"
            className="theme-icon theme-icon-sun h-4 w-4"
          />
          <Moon
            aria-hidden="true"
            className="theme-icon theme-icon-moon h-4 w-4"
          />
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}
