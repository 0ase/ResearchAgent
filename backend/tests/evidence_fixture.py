def evidence_state():
    report = "# Report\n\nThe source claim provides a traceable observation. This report compares that observation with the research question, while limiting its conclusion to the supplied evidence. [[CITE:citation-1]]"
    return {
        "raw_papers": [{"paper_id": "paper-1", "title": "Paper 1"}],
        "paper_insights": [{"paper_id": "paper-1", "source": "paper-1", "answer": "A source claim"}],
        "paper_claims": [{"claim_id": "claim-1", "paper_id": "paper-1", "statement": "A source claim",
                          "support_type": "direct", "chunk_ids": ["chunk-1"], "evidence_text": "A source claim"}],
        "chunks": [{"chunk_id": "chunk-1", "paper_id": "paper-1", "content": "A source claim from the paper.", "content_type": "abstract"}],
        "structured_report": {"sections": [{"section_id": "section-1", "citation_ids": ["citation-1"]}],
                              "citations": [{"citation_id": "citation-1", "claim_ids": ["claim-1"], "chunk_ids": ["chunk-1"]}]},
        "draft_sections": [{"content": report}],
        "final_answer": report,
    }
