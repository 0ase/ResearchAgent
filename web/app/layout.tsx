import type { Metadata } from "next";
import { getLocale } from "next-intl/server";
import "./globals.css";

import { Providers } from "@/app/providers";
import { DEFAULT_LOCALE, isAppLocale } from "@/i18n/locale";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

export const metadata: Metadata = {
  title: "Research Agent",
  description: "A multi-agent academic research workspace.",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const requestedLocale = await getLocale();
  const locale = isAppLocale(requestedLocale)
    ? requestedLocale
    : DEFAULT_LOCALE;
  return (
    <html
      lang={locale}
      data-theme="light"
      className="h-full antialiased"
      suppressHydrationWarning
    >
      <head>
        {/* Keep this parser-blocking so a persisted dark theme applies before first paint. */}
        <script
          id="research-agent-theme-init"
          dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }}
        />
      </head>
      <body className="min-h-full flex flex-col">
        <Providers locale={locale} enforceDeepSeekSetup>
          {children}
        </Providers>
      </body>
    </html>
  );
}
