import type { Data } from "mdast";
import type { Node } from "unist";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";

import { remarkEvidenceCitations } from "@/lib/markdown/remark-evidence-citations";

export type ReportHeading = { level: number; text: string; id: string };

export type ReportHeadingIndex = {
  headings: ReportHeading[];
  idsByOffset: ReadonlyMap<number, string>;
};

type MarkdownNode = Node & {
  data?: Data;
  depth?: number;
  value?: string;
  alt?: string;
  children?: MarkdownNode[];
};

const parser = unified()
  .use(remarkParse)
  .use(remarkGfm)
  .use(remarkEvidenceCitations);

export function buildReportHeadingIndex(markdown: string): ReportHeadingIndex {
  const tree = parser.runSync(parser.parse(markdown));
  const headings: ReportHeading[] = [];
  const idsByOffset = new Map<number, string>();
  const usedIds = new Set<string>();

  visitHeadings(tree, (node) => {
    const offset = node.position?.start.offset;
    if (offset === undefined) return;
    const text = headingText(node).replace(/\s+/g, " ").trim();
    const base = slugify(text);
    let id = base;
    let suffix = 2;
    while (usedIds.has(id)) id = `${base}-${suffix++}`;
    usedIds.add(id);
    headings.push({ level: node.depth!, text, id });
    idsByOffset.set(offset, id);
  });

  return { headings, idsByOffset };
}

// IDs are assigned before React renders; repeated StrictMode renders only read them.
export function remarkReportHeadings(index: ReportHeadingIndex) {
  return (tree: MarkdownNode) => {
    visitHeadings(tree, (node) => {
      const offset = node.position?.start.offset;
      const id =
        offset === undefined ? undefined : index.idsByOffset.get(offset);
      if (!id) return;
      node.data = {
        ...node.data,
        hProperties: { ...node.data?.hProperties, id },
      };
    });
  };
}

function visitHeadings(
  node: MarkdownNode,
  visit: (heading: MarkdownNode) => void,
): void {
  if (node.type === "heading") visit(node);
  for (const child of node.children ?? []) visitHeadings(child, visit);
}

function headingText(node: MarkdownNode): string {
  if (node.type === "citation" || node.type === "html") return "";
  if (node.type === "break") return " ";
  if (node.type === "image" || node.type === "imageReference")
    return node.alt ?? "";
  if (node.children) return node.children.map(headingText).join("");
  return node.value ?? "";
}

function slugify(value: string): string {
  return (
    value
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
      .replace(/^-+|-+$/g, "") || "section"
  );
}
