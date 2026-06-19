"""Full pipeline test — real-time progress with per-stage output."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from backend.agents.graph import build_graph


async def main():
    app = build_graph()
    print("=" * 60)
    print("🚀 7-Agent 全流程启动")
    print("=" * 60)

    # 追踪每个阶段是否已打印
    seen = set()
    result = None

    async for state in app.astream(
        {"user_query": "attention mechanism", "search_round": 0},
        stream_mode="values",
    ):
        result = state

        # --- Orchestrator ---
        plan = state.get("research_plan", [])
        if plan and "plan" not in seen:
            print(f"\n🧠 Orchestrator — 拆解为 {len(plan)} 个子查询:")
            for i, t in enumerate(plan, 1):
                print(f"    {i}. {t.get('sub_query', '?')[:80]}")
            seen.add("plan")

        # --- Search ---
        papers = state.get("raw_papers", [])
        if papers and "papers" not in seen:
            print(f"\n🔍 Search — 搜到 {len(papers)} 篇论文:")
            for p in papers[:3]:
                print(f"    [{p.get('source', '?')}] {p.get('title', '?')[:70]}")
            seen.add("papers")

        # --- Read ---
        insights = state.get("paper_insights", [])
        if insights and "insights" not in seen:
            print(f"\n📖 Read — LLM 总结完成 ({len(insights)} 篇):")
            for ins in insights[:1]:
                ans = ins.get("answer", "")
                print(f"    {ans[:300]}...")
            seen.add("insights")

        # --- Analyze ---
        analysis = state.get("analysis_report")
        if analysis and isinstance(analysis, dict) and "analysis" not in seen:
            ag = analysis.get("agreements", [])
            ct = analysis.get("contradictions", [])
            gp = analysis.get("gaps", [])
            print(f"\n🔬 Analyze — 共识 {len(ag)} | 矛盾 {len(ct)} | 空白 {len(gp)}")
            if ag:
                print(f"    共识例: {ag[0][:80]}")
            if ct:
                print(f"    矛盾例: {ct[0][:80]}")
            seen.add("analysis")

        # --- Synthesize ---
        draft = state.get("draft_sections", [])
        if draft and "draft" not in seen:
            content = draft[0].get("content", "") if draft else ""
            print(f"\n✍️ Synthesize — 综述 ({len(content)} 字符):")
            print(f"    {content[:400]}...")
            seen.add("draft")

        # --- Critic ---
        critique = state.get("critique")
        if critique and isinstance(critique, dict) and "critique" not in seen:
            print(f"\n✅ Critic — 评分 {critique.get('score', '?')}/10")
            issues = critique.get("issues", [])
            if issues:
                print(f"    问题: {issues[0][:100]}")
            seen.add("critique")

    # --- 最终 ---
    if result is None:
        print("\n❌ 无输出")
        return

    papers = result.get("raw_papers", [])
    print(f"\n{'=' * 60}")
    print(f"📊 DONE — {len(papers)} papers | 轮数 {result.get('search_round','?')}")
    final = result.get("final_answer", "")
    if final:
        print(f"\n📝 最终综述:")
        print(final[:1200])
    print(f"\n✅ 7-Agent 全流程执行完毕！")


if __name__ == "__main__":
    asyncio.run(main())
