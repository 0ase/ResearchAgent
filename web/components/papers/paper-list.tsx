"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import {
  PaperFilters,
  type PaperSort,
} from "@/components/papers/paper-filters";
import { PaperRow } from "@/components/papers/paper-row";
import type { ResearchPaper } from "@/features/papers/paper-model";

export function PaperList({
  papers,
  selectedPaperId,
  onSelect,
}: {
  papers: ResearchPaper[];
  selectedPaperId?: string | null;
  onSelect?: (paper: ResearchPaper) => void;
}) {
  const t = useTranslations("papers");
  const [query, setQuery] = useState("");
  const [source, setSource] = useState("all");
  const [sort, setSort] = useState<PaperSort>("relevance");
  const [selectedOnly, setSelectedOnly] = useState(false);
  const [citedOnly, setCitedOnly] = useState(false);
  const [fromYear, setFromYear] = useState("");
  const [toYear, setToYear] = useState("");
  const fromYearValue = fromYear ? Number(fromYear) : null;
  const toYearValue = toYear ? Number(toYear) : null;
  const yearRangeInvalid =
    fromYearValue !== null &&
    toYearValue !== null &&
    fromYearValue > toYearValue;
  const sources = useMemo(
    () => [...new Set(papers.map((paper) => paper.source))].sort(),
    [papers],
  );
  const visiblePapers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return papers
      .filter((paper) => source === "all" || paper.source === source)
      .filter((paper) => !selectedOnly || paper.selected)
      .filter((paper) => !citedOnly || paper.cited)
      .filter(
        (paper) =>
          fromYearValue === null ||
          (paper.year !== null && paper.year >= fromYearValue),
      )
      .filter(
        (paper) =>
          toYearValue === null ||
          (paper.year !== null && paper.year <= toYearValue),
      )
      .filter(
        (paper) =>
          !normalizedQuery ||
          [paper.title, paper.abstract, ...paper.authors]
            .join(" ")
            .toLowerCase()
            .includes(normalizedQuery),
      )
      .sort((left, right) => {
        if (sort === "citations")
          return (right.citationCount ?? -1) - (left.citationCount ?? -1);
        if (sort === "year") return (right.year ?? 0) - (left.year ?? 0);
        return (right.relevanceScore ?? -1) - (left.relevanceScore ?? -1);
      });
  }, [
    citedOnly,
    fromYearValue,
    papers,
    query,
    selectedOnly,
    sort,
    source,
    toYearValue,
  ]);

  return (
    <section aria-label={t("title")} className="space-y-4">
      <PaperFilters
        query={query}
        source={source}
        sort={sort}
        selectedOnly={selectedOnly}
        citedOnly={citedOnly}
        fromYear={fromYear}
        toYear={toYear}
        sources={sources}
        onQueryChange={setQuery}
        onSourceChange={setSource}
        onSortChange={setSort}
        onSelectedOnlyChange={setSelectedOnly}
        onCitedOnlyChange={setCitedOnly}
        onFromYearChange={setFromYear}
        onToYearChange={setToYear}
        yearRangeInvalid={yearRangeInvalid}
      />
      <div className="divide-y divide-[var(--color-border)] border-b border-[var(--color-border)]">
        {visiblePapers.map((paper) => (
          <PaperRow
            key={paper.id}
            paper={paper}
            selected={paper.id === selectedPaperId}
            onSelect={onSelect}
          />
        ))}
      </div>
      {!visiblePapers.length ? (
        <p className="py-8 text-center text-sm text-[var(--color-text-muted)]">
          {t("empty")}
        </p>
      ) : null}
    </section>
  );
}
