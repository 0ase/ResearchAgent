import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { ReactNode } from "react";

import { CitationMarker } from "@/components/report/citation-marker";
import { buildEvidenceIndex } from "@/features/evidence/evidence-index";
import { remarkEvidenceCitations } from "@/lib/markdown/remark-evidence-citations";
import {
  remarkReportHeadings,
  type ReportHeadingIndex,
} from "@/lib/markdown/report-headings";
import type { ResearchTaskResultResponse } from "@/lib/api/client";
import styles from "./report-document.module.css";

export function ReportDocument({
  markdown,
  headingIndex,
  variant = "report",
  result,
}: {
  markdown: string;
  headingIndex?: ReportHeadingIndex;
  variant?: "report" | "message";
  result?: ResearchTaskResultResponse;
}) {
  const evidenceIndex = buildEvidenceIndex(result);
  const components = {
    citation: ({ node }: CitationNodeProps) => {
      const properties = (node as { properties?: { citationId?: unknown } })
        .properties;
      const citationId =
        typeof properties?.citationId === "string" ? properties.citationId : "";
      const citation = evidenceIndex.citations.get(citationId);
      return (
        <CitationMarker
          citationId={citationId}
          displayNumber={
            typeof citation?.display_number === "number"
              ? citation.display_number
              : undefined
          }
          valid={citation?.valid !== false}
        />
      );
    },
    table: ({ children }) => (
      <div
        className={
          variant === "report" ? styles.tableContainer : "overflow-x-auto"
        }
      >
        <table>{children}</table>
      </div>
    ),
    a: ({ href, children }) => (
      <a href={href} target="_blank" rel="noreferrer noopener">
        {children}
      </a>
    ),
  } as Components & { citation: (props: CitationNodeProps) => ReactNode };

  return (
    <div
      className={
        variant === "report"
          ? `report-document ${styles.document}`
          : "max-w-[760px] text-[15px] leading-[1.75] text-[var(--color-text)]"
      }
    >
      <Markdown
        skipHtml
        remarkPlugins={[
          remarkGfm,
          remarkEvidenceCitations,
          ...(variant === "report" && headingIndex
            ? [
                [remarkReportHeadings, headingIndex] as [
                  typeof remarkReportHeadings,
                  ReportHeadingIndex,
                ],
              ]
            : []),
        ]}
        components={components}
      >
        {markdown}
      </Markdown>
    </div>
  );
}

type CitationNodeProps = {
  node: { properties?: { citationId?: unknown } };
};
