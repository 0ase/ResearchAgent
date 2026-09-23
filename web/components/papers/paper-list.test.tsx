import { userEvent } from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PaperDetail } from "@/components/papers/paper-detail";
import { PaperList } from "@/components/papers/paper-list";
import type { ResearchPaper } from "@/features/papers/paper-model";
import { Providers } from "@/app/providers";

const papers: ResearchPaper[] = [
  {
    id: "paper-1",
    title: "Graph retrieval for scientific discovery",
    authors: ["Ada Lovelace", "Grace Hopper"],
    year: 2024,
    source: "arxiv",
    abstract: "A graph-based retrieval study.",
    doi: "10.1000/graph",
    citationCount: 42,
    relevanceScore: 4.8,
    pdfUrl: "https://example.com/graph.pdf",
    fullTextStatus: "full",
    selected: true,
    cited: true,
    reportCitationCount: 2,
  },
  {
    id: "paper-2",
    title: "Efficient attention in language models",
    authors: ["Katherine Johnson"],
    year: 2022,
    source: "semantic_scholar",
    abstract: "An attention survey.",
    citationCount: 11,
    relevanceScore: 3.2,
    pdfUrl: "",
    fullTextStatus: "abstract_only",
    selected: false,
    cited: false,
    reportCitationCount: 0,
  },
  {
    id: "paper-3",
    title: "Reliable evaluation benchmarks",
    authors: ["Alan Turing"],
    year: 2020,
    source: "pubmed",
    abstract: "Benchmark methods.",
    citationCount: 88,
    relevanceScore: 4.1,
    pdfUrl: "",
    fullTextStatus: "pdf_failed",
    selected: true,
    cited: false,
    reportCitationCount: 0,
  },
];

describe("PaperList", () => {
  it("filters by query, source, and selected/cited flags, then sorts locally", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <PaperList papers={papers} />
      </Providers>,
    );

    expect(
      screen.getByRole("button", { name: /graph retrieval/i }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /paper/i })).toHaveLength(3);

    await user.type(screen.getByLabelText("Search papers"), "attention");
    expect(
      screen.getByRole("button", { name: /efficient attention/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /graph retrieval/i }),
    ).not.toBeInTheDocument();

    await user.clear(screen.getByLabelText("Search papers"));
    await user.selectOptions(screen.getByLabelText("Source"), "arxiv");
    expect(
      screen.getByRole("button", { name: /graph retrieval/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /reliable evaluation/i }),
    ).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Source"), "all");
    await user.type(screen.getByLabelText("From year"), "2023");
    await user.type(screen.getByLabelText("To year"), "2024");
    expect(
      screen.getByRole("button", { name: /graph retrieval/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /efficient attention/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /reliable evaluation/i }),
    ).not.toBeInTheDocument();

    await user.clear(screen.getByLabelText("From year"));
    await user.clear(screen.getByLabelText("To year"));
    await user.click(screen.getByLabelText("Selected only"));
    expect(
      screen.queryByRole("button", { name: /efficient attention/i }),
    ).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /paper/i })).toHaveLength(2);

    await user.click(screen.getByLabelText("Cited only"));
    expect(
      screen.getByRole("button", { name: /graph retrieval/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /reliable evaluation/i }),
    ).not.toBeInTheDocument();
  });

  it("opens a paper detail with explicit reading-status labels", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <Providers locale="en">
        <PaperList papers={papers} onSelect={onSelect} />
      </Providers>,
    );

    await user.click(
      screen.getByRole("button", { name: /efficient attention/i }),
    );
    expect(onSelect).toHaveBeenCalledWith(papers[1]);

    render(
      <Providers locale="en">
        <PaperDetail paper={papers[1]} />
      </Providers>,
    );
    expect(screen.getAllByText("Abstract only")).toHaveLength(2);
    expect(
      screen.getByText("No PDF is available; showing the abstract."),
    ).toBeInTheDocument();
  });

  it("renders full-text and missing-text states in Chinese", () => {
    render(
      <Providers locale="zh-CN">
        <PaperDetail
          paper={{
            ...papers[0],
            abstract: "",
            fullTextStatus: "full_no_abstract",
          }}
        />
      </Providers>,
    );

    expect(screen.getByText("全文可用，暂无摘要")).toBeInTheDocument();
    expect(
      screen.getByText("全文可用，但该来源没有提供摘要。"),
    ).toBeInTheDocument();
  });
});
