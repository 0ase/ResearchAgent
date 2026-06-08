"""Direct test of Semantic Scholar API without our code."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import httpx


async def main():
    # 用最简单的 query 直接调 S2
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": "attention",
        "limit": 3,
        "fields": "title,year",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Total results: {data.get('total', 'N/A')}")
        print(f"Data keys: {list(data.keys())}")
        for item in data.get("data", []):
            print(f"  - {item.get('title', 'N/A')[:80]}")


if __name__ == "__main__":
    asyncio.run(main())
