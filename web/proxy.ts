import { NextResponse, type NextRequest } from "next/server";
import createMiddleware from "next-intl/middleware";

import { DEFAULT_LOCALE, LOCALE_COOKIE, isAppLocale } from "@/i18n/locale";
import { routing } from "@/i18n/routing";

const intlMiddleware = createMiddleware(routing);
const LOCALE_HEADER = "X-NEXT-INTL-LOCALE";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

export default function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isEnglishPath = pathname === "/en" || pathname.startsWith("/en/");
  const isDefaultLocalePath =
    pathname === "/zh-CN" || pathname.startsWith("/zh-CN/");
  const cookieValue = request.cookies.get(LOCALE_COOKIE)?.value;
  const preferredLocale = isAppLocale(cookieValue ?? "")
    ? cookieValue
    : DEFAULT_LOCALE;

  if (isDefaultLocalePath) {
    const response = NextResponse.redirect(stripLocale(request, "zh-CN"));
    persistLocale(response, DEFAULT_LOCALE);
    return response;
  }

  if (!isEnglishPath && preferredLocale === "en") {
    const response = NextResponse.redirect(prefixPath(request, "en"));
    persistLocale(response, "en");
    return response;
  }

  if (!isEnglishPath) {
    const response = nextWithLocale(request, DEFAULT_LOCALE);
    if (!isAppLocale(cookieValue ?? ""))
      persistLocale(response, DEFAULT_LOCALE);
    return response;
  }

  return intlMiddleware(request);
}

function nextWithLocale(request: NextRequest, locale: string) {
  const headers = new Headers(request.headers);
  headers.set(LOCALE_HEADER, locale);
  return NextResponse.next({ request: { headers } });
}

function prefixPath(request: NextRequest, locale: string) {
  const url = request.nextUrl.clone();
  url.pathname = `/${locale}${url.pathname === "/" ? "" : url.pathname}`;
  return url;
}

function stripLocale(request: NextRequest, locale: string) {
  const url = request.nextUrl.clone();
  const prefix = `/${locale}`;
  url.pathname = url.pathname.slice(prefix.length) || "/";
  return url;
}

function persistLocale(response: NextResponse, locale: string) {
  response.cookies.set(LOCALE_COOKIE, locale, {
    path: "/",
    maxAge: COOKIE_MAX_AGE,
    sameSite: "lax",
  });
}

export const config = {
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
