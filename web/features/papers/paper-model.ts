export type PaperTextStatus =
  "full" | "abstract_only" | "full_no_abstract" | "unavailable" | "pdf_failed";

export type ResearchPaper = {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  source: string;
  abstract: string;
  doi?: string;
  citationCount: number | null;
  relevanceScore: number | null;
  pdfUrl: string | null;
  fullTextStatus: PaperTextStatus;
  selected: boolean;
  cited: boolean;
  reportCitationCount: number;
};

export function normalizePaper(
  value: Record<string, unknown>,
  index = 0,
): ResearchPaper {
  const source = asString(value.source, "unknown");
  const sourceId = asString(value.source_id);
  const paperId = asString(value.paper_id || value.id);
  const doi = asString(value.doi);
  const pdfUrl = asString(value.pdf_url);
  const status = asString(value.full_text_status);
  const legacyStatus = asString(value.pdf_status);
  const abstract = asString(value.abstract);
  const normalizedStatus =
    normalizeTextStatus(status) ?? normalizeTextStatus(legacyStatus);

  return {
    id: paperId || sourceId || doi || `paper-${index + 1}`,
    title: asString(value.title, "Untitled paper"),
    authors: Array.isArray(value.authors)
      ? value.authors.filter((item): item is string => typeof item === "string")
      : [],
    year: parseYear(value.year ?? value.published_date),
    source,
    abstract,
    doi: doi || undefined,
    citationCount: asNumber(value.citation_count),
    relevanceScore: asNumber(value.relevance_score),
    pdfUrl: pdfUrl || null,
    fullTextStatus: normalizedStatus ?? inferTextStatus({ abstract, pdfUrl }),
    selected: asBoolean(value.selected ?? value.is_selected),
    cited: asBoolean(value.cited ?? value.is_cited),
    reportCitationCount:
      asNumber(value.report_citation_count ?? value.citation_count_in_report) ??
      0,
  };
}

function normalizeTextStatus(value: string): PaperTextStatus | null {
  if (value === "failed") return "pdf_failed";
  if (
    value === "full" ||
    value === "abstract_only" ||
    value === "full_no_abstract" ||
    value === "unavailable" ||
    value === "pdf_failed"
  ) {
    return value;
  }
  return null;
}

function inferTextStatus({
  abstract,
  pdfUrl,
}: {
  abstract: string;
  pdfUrl: string;
}): PaperTextStatus {
  if (pdfUrl && abstract) return "full";
  if (pdfUrl) return "full_no_abstract";
  if (abstract) return "abstract_only";
  return "unavailable";
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asBoolean(value: unknown): boolean {
  return value === true;
}

function parseYear(value: unknown): number | null {
  const match = String(value ?? "").match(/\b(19|20)\d{2}\b/);
  return match ? Number(match[0]) : null;
}
