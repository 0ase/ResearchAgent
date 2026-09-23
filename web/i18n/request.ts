import { getRequestConfig } from "next-intl/server";

import { DEFAULT_LOCALE, isAppLocale } from "@/i18n/locale";
import { getMessages } from "@/i18n/messages";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale =
    requested && isAppLocale(requested) ? requested : DEFAULT_LOCALE;

  return {
    locale,
    messages: getMessages(locale),
    timeZone: "Asia/Shanghai",
  };
});
