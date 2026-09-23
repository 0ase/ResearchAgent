import type { AppLocale } from "@/i18n/routing";
import type { AppMessages } from "@/i18n/messages";

declare module "next-intl" {
  interface AppConfig {
    Locale: AppLocale;
    Messages: AppMessages;
  }
}
