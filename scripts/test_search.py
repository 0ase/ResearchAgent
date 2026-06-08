"""Test search pipelines alone — arXiv + Semantic Scholar."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from backend.sources.arxiv_client import search_arxiv
from backend.sources.semantic_scholar_client import search_semantic_scholar


async def main():
    query = "attention mechanism in natural language processing"

    print("=== arXiv ===")
    arxiv = await search_arxiv(query)
    print(f"  返回: {len(arxiv)} 篇")
    for p in arxiv[:2]:
        print(f"  - {p.get('title', 'N/A')[:80]}")

    print("\n=== Semantic Scholar ===")
    s2 = await search_semantic_scholar(query)
    print(f"  返回: {len(s2)} 篇")
    for p in s2[:2]:
        print(f"  - {p.get('title', 'N/A')[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
