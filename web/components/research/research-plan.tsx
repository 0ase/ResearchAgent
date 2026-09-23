import { useTranslations } from "next-intl";

export function ResearchPlan() {
  const t = useTranslations("task");
  return (
    <section className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-5">
      <h2 className="text-base font-semibold text-[var(--color-text)]">
        {t("researchPlan")}
      </h2>
      <p className="mt-2 text-sm text-[var(--color-text-muted)]">
        {t("researchPlanPlaceholder")}
      </p>
    </section>
  );
}
