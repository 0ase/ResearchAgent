"""Test RAG: search papers → ingest top 5 → query the vector store."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from backend.agents.graph import build_graph
from backend.rag.ingestion import ingest_paper
from backend.rag.embeddings import embed_single
from backend.rag.vector_store import search


async def main():
    print("=" * 60)
    print("测试 RAG：搜索 → 入库 → 向量检索")
    print("=" * 60)

    # Step 1: 跑 pipeline 搜论文
    print("\n① 搜索论文...")
    app = build_graph()
    result = await app.ainvoke({
        "user_query": "attention mechanism",
        "search_round": 0,
    })
    papers = result.get("raw_papers", [])
    print(f"  搜到 {len(papers)} 篇")

    # Step 2: 找有 PDF 链接的论文，逐个入库
    print("\n② 逐篇入库（只处理有 PDF 链接的论文）...")
    ingested = 0
    for i, paper in enumerate(papers):
        if ingested >= 5:  # 入库 5 篇就停
            break
        pdf_url = paper.get("pdf_url", "")
        source_id = paper.get("source_id", "unknown")
        title = paper.get("title", "?")[:60]

        print(f"  [{i+1}/{len(papers)}] {source_id}: {title}")
        if not pdf_url:
            print(f"         ⏭️ 无 PDF 链接，跳过")
            continue

        print(f"         ⏳ 下载 + 分块 + embed + 入库...")
        success = await ingest_paper(paper)
        if success:
            ingested += 1
            print(f"         ✅ 成功！({ingested}/5)")
        else:
            print(f"         ❌ 失败（下载超时或文本太短）")

    if ingested == 0:
        print("\n  ⚠️ 没有论文成功入库（PDF 下载失败？检查网络）")
        return

    # Step 3: 用问题搜向量库
    print(f"\n③ 向量检索（已入库 {ingested} 篇论文）...")
    query_embedding = await embed_single("attention mechanism in transformer models")
    results = search(query_embedding, n_results=3)

    print(f"  最相关的 3 个 chunk:")
    for i, r in enumerate(results, 1):
        content_preview = r["content"][:100].replace("\n", " ")
        print(f"  {i}. [{r['paper_id']}] chunk#{r['chunk_index']}: {content_preview}...")

    print("\n✅ RAG 流水线验证完毕！")


if __name__ == "__main__":
    asyncio.run(main())
