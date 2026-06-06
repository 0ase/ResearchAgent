"""Quick end-to-end test — runs the full pipeline without FastAPI."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from backend.agents.graph import build_graph


async def main():
    app = build_graph()
    print("=" * 60)
    print("测试：端到端 pipeline（Orchestrator → Search → arXiv）")
    print("=" * 60)

    result = await app.ainvoke({
        "user_query": "attention mechanism",
        "search_round": 0,
    })

    print(f"\n📋 研究计划 ({len(result.get('research_plan', []))} 个子查询):")
    for i, task in enumerate(result.get("research_plan", []), 1):
        print(f"  {i}. {task['sub_query'][:80]}...")

    papers = result.get("raw_papers", [])
    print(f"\n📄 论文总数: {len(papers)}")
    for i, p in enumerate(papers[:5], 1):
        print(f"  {i}. {p.get('title', 'N/A')[:80]}")
        print(f"     作者: {', '.join(p.get('authors', [])[:3])}")
        print(f"     来源: {p.get('source', 'N/A')}")

    print(f"\n🔍 搜索轮数: {result.get('search_round', 'N/A')}")
    print(f"\n✅ Pipeline 执行完毕！")


if __name__ == "__main__":
    asyncio.run(main())
