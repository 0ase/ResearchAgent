import type { ResearchTaskResultResponse } from "@/lib/api/client";

export type EvidenceRecord = Record<string, unknown> & {
  evidence_id?: string;
  citation_id?: string;
};

export type CitationRecord = Record<string, unknown> & {
  citation_id?: string;
};

export type EvidenceIndex = {
  citations: Map<string, CitationRecord>;
  evidenceByCitation: Map<string, EvidenceRecord[]>;
  evidence: Map<string, EvidenceRecord>;
  papers: Map<string, Record<string, unknown>>;
};

export function buildEvidenceIndex(
  result: ResearchTaskResultResponse | undefined,
): EvidenceIndex {
  const citations = new Map<string, CitationRecord>();
  const evidence = new Map<string, EvidenceRecord>();
  const evidenceByCitation = new Map<string, EvidenceRecord[]>();
  const evidenceByChunk = new Map<string, EvidenceRecord[]>();
  const papers = new Map<string, Record<string, unknown>>();

  for (const paper of result?.papers ?? []) {
    const id = asString(paper.paper_id);
    if (id) papers.set(id, paper);
  }
  for (const raw of result?.evidence ?? []) {
    const item = raw as EvidenceRecord;
    const id = asString(item.evidence_id);
    if (id) evidence.set(id, item);
    const chunkId = asString(item.chunk_id);
    if (chunkId) {
      const existing = evidenceByChunk.get(chunkId) ?? [];
      evidenceByChunk.set(chunkId, [...existing, item]);
    }
  }
  for (const raw of result?.citations ?? []) {
    const citation = raw as CitationRecord;
    const id = asString(citation.citation_id);
    if (!id) continue;
    citations.set(id, citation);
    const evidenceIds = arrayOfStrings(citation.evidence_ids);
    const chunkIds = arrayOfStrings(citation.chunk_ids);
    const linkedEvidence = evidenceIds
      .map((evidenceId) => evidence.get(evidenceId))
      .filter((item): item is EvidenceRecord => Boolean(item));
    for (const chunkId of chunkIds) {
      for (const item of evidenceByChunk.get(chunkId) ?? []) {
        if (!linkedEvidence.includes(item)) linkedEvidence.push(item);
      }
    }
    evidenceByCitation.set(id, linkedEvidence);
  }
  for (const raw of result?.evidence ?? []) {
    const item = raw as EvidenceRecord;
    const citationId = asString(item.citation_id);
    if (citationId) {
      const existing = evidenceByCitation.get(citationId) ?? [];
      if (!existing.includes(item)) {
        evidenceByCitation.set(citationId, [...existing, item]);
      }
    }
  }
  return { citations, evidenceByCitation, evidence, papers };
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function arrayOfStrings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}
