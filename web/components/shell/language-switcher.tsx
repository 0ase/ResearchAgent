"use client";

import { Languages } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";

import { type AppLocale, LOCALE_COOKIE } from "@/i18n/locale";
import { usePathname, useRouter } from "@/i18n/navigation";

const labels: Record<AppLocale, string> = {
  "zh-CN": "中文",
  en: "English",
};

export function LanguageSwitcher({ locked = false }: { locked?: boolean }) {
  const locale = useLocale() as AppLocale;
  const t = useTranslations();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const lockedDescription = t("task.languageLocked");

  function switchLocale(nextLocale: AppLocale) {
    if (locked || nextLocale === locale) return;
    // eslint-disable-next-line react-hooks/immutability -- locale persistence is an intentional browser side effect.
    document.cookie = `${LOCALE_COOKIE}=${nextLocale}; Path=/; Max-Age=31536000; SameSite=Lax`;
    const query = searchParams.toString();
    router.replace(`${pathname}${query ? `?${query}` : ""}`, {
      locale: nextLocale,
    });
  }

  return (
    <div
      aria-label={t("common.languages")}
      className="inline-flex items-center gap-1 rounded-[var(--radius-control)] border border-[var(--color-border)] bg-[var(--color-surface-subtle)] p-1"
    >
      <Languages
        aria-hidden="true"
        className="ml-1 h-3.5 w-3.5 text-[var(--color-text-subtle)]"
      />
      {(["zh-CN", "en"] as const).map((option) => (
        <button
          key={option}
          type="button"
          className="rounded-[calc(var(--radius-control)-2px)] px-2 py-1 text-xs font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-70"
          aria-pressed={locale === option}
          aria-describedby={locked ? "task-language-locked" : undefined}
          disabled={locked}
          onClick={() => switchLocale(option)}
        >
          {labels[option]}
        </button>
      ))}
      {locked ? (
        <span id="task-language-locked" className="sr-only">
          {lockedDescription}
        </span>
      ) : null}
    </div>
  );
}
