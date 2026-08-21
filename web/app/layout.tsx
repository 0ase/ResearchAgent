import type { Metadata } from "next";
import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";
import "./globals.css";

import { Providers } from "@/app/providers";
import { DEFAULT_LOCALE, isAppLocale } from "@/i18n/locale";

export const metadata: Metadata = {
  title: "Research Agent",
  description: "A multi-agent academic research workspace.",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const requestedLocale = await getLocale();
  const locale = isAppLocale(requestedLocale)
    ? requestedLocale
    : DEFAULT_LOCALE;
  return (
    <html lang={locale} className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <Providers locale={locale} enforceDeepSeekSetup>
          {children}
        </Providers>
      </body>
    </html>
  );
}
