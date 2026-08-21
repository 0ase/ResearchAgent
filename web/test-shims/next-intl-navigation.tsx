import type { AnchorHTMLAttributes, ReactNode } from "react";

type Href =
  | string
  | { pathname: string; query?: Record<string, string | number | undefined> };

export function Link({
  href,
  children,
  ...props
}: Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  href: Href;
  children?: ReactNode;
}) {
  const target = typeof href === "string" ? href : href.pathname;
  return (
    <a href={target} {...props}>
      {children}
    </a>
  );
}

export function useRouter() {
  return {
    push: (href: Href) => {
      window.history.pushState(
        {},
        "",
        typeof href === "string" ? href : href.pathname,
      );
    },
    replace: (href: Href) => {
      window.history.replaceState(
        {},
        "",
        typeof href === "string" ? href : href.pathname,
      );
    },
    back: () => window.history.back(),
    forward: () => window.history.forward(),
    refresh: () => undefined,
    prefetch: async () => undefined,
  };
}

export function usePathname() {
  return window.location.pathname;
}

export function redirect(href: Href): never {
  throw new Error(
    `Redirected to ${typeof href === "string" ? href : href.pathname}`,
  );
}

export function getPathname({ href }: { href: Href }) {
  return typeof href === "string" ? href : href.pathname;
}

export function createNavigation() {
  return { Link, redirect, usePathname, useRouter, getPathname };
}
