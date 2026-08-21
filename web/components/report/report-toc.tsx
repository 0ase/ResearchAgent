export type ReportHeading = { level: number; text: string; id: string };

export function extractReportHeadings(markdown: string): ReportHeading[] {
  const counts = new Map<string, number>();
  const headings: ReportHeading[] = [];
  for (const match of markdown.matchAll(/^(#{1,6})\s+(.+)$/gm)) {
    const text = match[2].trim().replace(/[*_`]/g, "");
    const base = slugify(text);
    const count = counts.get(base) ?? 0;
    counts.set(base, count + 1);
    headings.push({
      level: match[1].length,
      text,
      id: count ? `${base}-${count + 1}` : base,
    });
  }
  return headings;
}

import { useTranslations } from "next-intl";

export function ReportToc({ markdown }: { markdown: string }) {
  const t = useTranslations("report");
  const headings = extractReportHeadings(markdown);
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
              className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-primary)]"
            >
              {heading.text}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "section";
}
