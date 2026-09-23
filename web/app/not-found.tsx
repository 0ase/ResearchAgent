"use client";

import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { cn } from "@/lib/utils/cn";
import { Link } from "@/i18n/navigation";

export default function NotFound() {
  const t = useTranslations();
  return (
    <main className="relative flex min-h-screen items-center justify-center bg-[var(--color-page)] px-6">
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>
      <section className="max-w-md rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center">
        <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-text-subtle)]">
          404
        </p>
        <h1 className="mt-2 text-xl font-semibold text-[var(--color-text)]">
          {t("task.notFound")}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-muted)]">
          {t("task.loadError")}
        </p>
        <div className="mt-6 flex justify-center gap-2">
          <Link href="/" className={cn(buttonVariants({ variant: "primary" }))}>
            {t("common.home")}
          </Link>
          <Link
            href="/history"
            className={cn(buttonVariants({ variant: "secondary" }))}
          >
            {t("common.history")}
          </Link>
        </div>
      </section>
    </main>
  );
}
