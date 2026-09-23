type MdastNode = {
  type: string;
  value?: string;
  children?: MdastNode[];
  data?: Record<string, unknown>;
};

export const CITATION_TOKEN_RE = /\[\[CITE:([A-Za-z0-9][A-Za-z0-9:_-]*)\]\]/g;

export function parseCitationToken(value: string): string | null {
  const match = /^\[\[CITE:([A-Za-z0-9][A-Za-z0-9:_-]*)\]\]$/.exec(value);
  return match?.[1] ?? null;
}

export function remarkEvidenceCitations() {
  return (tree: MdastNode) => {
    visitTextNodes(tree);
  };
}

function visitTextNodes(node: MdastNode): void {
  if (!node.children) return;
  const nextChildren: MdastNode[] = [];
  for (const child of node.children) {
    if (child.type === "text" && typeof child.value === "string") {
      nextChildren.push(...splitCitationText(child.value));
    } else {
      visitTextNodes(child);
      nextChildren.push(child);
    }
  }
  node.children = nextChildren;
}

function splitCitationText(value: string): MdastNode[] {
  const nodes: MdastNode[] = [];
  let cursor = 0;
  for (const match of value.matchAll(CITATION_TOKEN_RE)) {
    const start = match.index ?? 0;
    if (start > cursor)
      nodes.push({ type: "text", value: value.slice(cursor, start) });
    nodes.push({
      type: "citation",
      data: {
        hName: "citation",
        hProperties: { citationId: match[1] },
        citationId: match[1],
      },
    });
    cursor = start + match[0].length;
  }
  if (cursor < value.length)
    nodes.push({ type: "text", value: value.slice(cursor) });
  return nodes.length ? nodes : [{ type: "text", value }];
}
