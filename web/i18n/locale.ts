import type { AppLocale } from "@/i18n/routing";

export type { AppLocale } from "@/i18n/routing";

export const SUPPORTED_LOCALES = [
  "zh-CN",
  "en",
] as const satisfies readonly AppLocale[];
export const DEFAULT_LOCALE: AppLocale = "zh-CN";
export const LOCALE_COOKIE = "RESEARCH_AGENT_LOCALE";

export function isAppLocale(value: string): value is AppLocale {
  return SUPPORTED_LOCALES.includes(value as AppLocale);
}

export function localeFromOutputLanguage(value: unknown): AppLocale {
  return value === "zh-CN" ? "zh-CN" : "en";
}

export function localeForTask(
  query: string,
  outputLanguage: unknown,
): AppLocale {
  if (outputLanguage === "zh-CN" || outputLanguage === "en") {
    return outputLanguage;
  }
  return /[\u3400-\u9fff]/u.test(query) ? "zh-CN" : "en";
}
