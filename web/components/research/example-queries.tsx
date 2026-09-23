import type { ReactNode } from "react";
import { useTranslations } from "next-intl";

export const exampleQueries = [
  {
    label: "Transformer 注意力机制的最新进展",
    query: "2023 年以来 Transformer 注意力机制有哪些进展？",
  },
  {
    label: "减少大语言模型幻觉的方法比较",
    query: "减少大语言模型幻觉的主要方法有哪些？请比较它们的证据和局限。",
  },
  {
    label: "LLM 多 Agent 协作方法综述",
    query: "请综述 LLM 多 Agent 协作方法的主要范式、评测方式和开放问题。",
  },
] as const;

const localizedExamples = [
  { labelKey: "example1Label", queryKey: "example1Query" },
  { labelKey: "example2Label", queryKey: "example2Query" },
  { labelKey: "example3Label", queryKey: "example3Query" },
] as const;

export function ExampleQueries({
  onSelect,
}: {
  onSelect: (query: string) => void;
}): ReactNode {
  const t = useTranslations("composer");
  return (
    <div className="mt-4">
      <p className="text-xs font-medium text-[var(--color-text-muted)]">
        {t("exampleQueries")}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        {localizedExamples.map((example) => (
          <button
            key={example.labelKey}
            type="button"
            className="rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs text-[var(--color-text-muted)] transition-colors hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-subtle)] hover:text-[var(--color-primary-hover)]"
            onClick={() => onSelect(t(example.queryKey))}
          >
            {t(example.labelKey)}
          </button>
        ))}
      </div>
    </div>
  );
}
