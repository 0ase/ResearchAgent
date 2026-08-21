import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import type { ReactNode } from "react";

import { slugify } from "@/components/report/report-toc";
import { CitationMarker } from "@/components/report/citation-marker";
import { buildEvidenceIndex } from "@/features/evidence/evidence-index";
import { remarkEvidenceCitations } from "@/lib/markdown/remark-evidence-citations";
import type { ResearchTaskResultResponse } from "@/lib/api/client";

export function ReportDocument({
  markdown,
  result,
}: {
  markdown: string;
  result?: ResearchTaskResultResponse;
}) {
  const headingCounts = new Map<string, number>();
  const evidenceIndex = buildEvidenceIndex(result);
  const components = {
    h1: ({ children }) => renderHeading(1, children, headingCounts),
    h2: ({ children }) => renderHeading(2, children, headingCounts),
    h3: ({ children }) => renderHeading(3, children, headingCounts),
    h4: ({ children }) => renderHeading(4, children, headingCounts),
    h5: ({ children }) => renderHeading(5, children, headingCounts),
    h6: ({ children }) => renderHeading(6, children, headingCounts),
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
      <div className="overflow-x-auto">
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
    <div className="report-document max-w-[760px] text-[15px] leading-[1.75] text-[var(--color-text)]">
      <Markdown
        skipHtml
        remarkPlugins={[remarkGfm, remarkEvidenceCitations]}
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

function renderHeading(
  level: 1 | 2 | 3 | 4 | 5 | 6,
  children: ReactNode,
  counts: Map<string, number>,
) {
  const text = plainText(children);
  const base = slugify(text);
  const count = counts.get(base) ?? 0;
  counts.set(base, count + 1);
  const id = count ? `${base}-${count + 1}` : base;
  const props = { id };
  switch (level) {
    case 1:
      return <h1 {...props}>{children}</h1>;
    case 2:
      return <h2 {...props}>{children}</h2>;
    case 3:
      return <h3 {...props}>{children}</h3>;
    case 4:
      return <h4 {...props}>{children}</h4>;
    case 5:
      return <h5 {...props}>{children}</h5>;
    case 6:
      return <h6 {...props}>{children}</h6>;
  }
}

function plainText(children: ReactNode): string {
  if (typeof children === "string" || typeof children === "number")
    return String(children);
  if (Array.isArray(children)) return children.map(plainText).join("");
  if (children && typeof children === "object" && "props" in children) {
    return plainText(
      (children as { props?: { children?: ReactNode } }).props?.children,
    );
  }
  return "section";
}
