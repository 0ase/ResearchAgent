import { useTranslations } from "next-intl";

import type { ReportHeading } from "@/lib/markdown/report-headings";

export function ReportToc({ headings }: { headings: ReportHeading[] }) {
  const t = useTranslations("report");
  if (!headings.length) return null;
  return (
    <nav
      aria-label={t("contents")}
      className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface-subtle)] p-4"
    >
      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
        {t("contents")}
      </p>
      <ol className="mt-2 space-y-1">
        {headings.map((heading) => (
          <li
            key={heading.id}
            style={{ paddingLeft: `${Math.max(0, heading.level - 1) * 10}px` }}
          >
            <a
              href={`#${heading.id}`}
              className="block text-sm text-[var(--color-text-muted)] hover:text-[var(--color-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]"
            >
              {heading.text}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
