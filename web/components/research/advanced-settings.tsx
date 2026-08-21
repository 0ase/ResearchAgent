"use client";

import type { UseFormRegister } from "react-hook-form";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { ResearchComposerValues } from "@/components/research/research-composer";

const sources = [
  ["arxiv", "arXiv"],
  ["semantic_scholar", "Semantic Scholar"],
  ["pubmed", "PubMed"],
  ["crossref", "Crossref"],
] as const;

export function AdvancedSettings({
  open,
  onToggle,
  register,
}: {
  open: boolean;
  onToggle: () => void;
  register: UseFormRegister<ResearchComposerValues>;
}) {
  const t = useTranslations("composer");
  return (
    <div className="mt-6 border-t border-[var(--color-border)] pt-4">
      <Button
        aria-expanded={open}
        onClick={onToggle}
        type="button"
        variant="ghost"
        className="-ml-2"
      >
        {open ? t("advancedHide") : t("advanced")}
      </Button>
      {open ? (
        <div className="mt-4 grid gap-5 sm:grid-cols-2">
          <label className="block text-[13px] font-medium text-[var(--color-text)]">
            {t("maxPapers")}
            <input
              aria-label={t("maxPapers")}
              type="number"
              min={1}
              max={50}
              className="mt-1.5 h-9 w-full rounded-[var(--radius-panel)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-sm outline-none focus-visible:border-[var(--color-primary)] focus-visible:ring-2 focus-visible:ring-[var(--color-primary-subtle)]"
              {...register("maxPapers", { valueAsNumber: true })}
            />
          </label>
          <fieldset className="sm:col-span-2">
            <legend className="text-[13px] font-medium text-[var(--color-text)]">
              {t("sources")}
            </legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {sources.map(([value]) => (
                <label
                  key={value}
                  className="flex items-center gap-2 text-sm text-[var(--color-text-muted)]"
                >
                  <input
                    type="checkbox"
                    value={value}
                    {...register("sources")}
                  />
                  {value === "arxiv"
                    ? t("sourceArxiv")
                    : value === "semantic_scholar"
                      ? t("sourceSemanticScholar")
                      : value === "pubmed"
                        ? t("sourcePubmed")
                        : t("sourceCrossref")}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      ) : null}
    </div>
  );
}
