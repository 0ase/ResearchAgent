import { describe, expect, it } from "vitest";

import { remarkEvidenceCitations } from "@/lib/markdown/remark-evidence-citations";

describe("remarkEvidenceCitations", () => {
  it("turns strict citation tokens into citation nodes", () => {
    const tree = {
      type: "root",
      children: [
        {
          type: "paragraph",
          children: [{ type: "text", value: "A [[CITE:citation-1]] claim" }],
        },
      ],
    };

    remarkEvidenceCitations()(tree);

    expect(tree.children[0].children.map((node) => node.type)).toEqual([
      "text",
      "citation",
      "text",
    ]);
    expect(
      (tree.children[0].children[1] as { data?: { citationId?: string } }).data
        ?.citationId,
    ).toBe("citation-1");
  });

  it("does not interpret ordinary citation-like prose", () => {
    const tree = {
      type: "root",
      children: [
        {
          type: "paragraph",
          children: [
            { type: "text", value: "CITE:paper-1 or [[cite:paper-1]]" },
          ],
        },
      ],
    };

    remarkEvidenceCitations()(tree);

    expect(tree.children[0].children).toHaveLength(1);
    expect(tree.children[0].children[0].type).toBe("text");
  });
});
