"""Test the orchestrator alone to see what DeepSeek returns."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from backend.agents.orchestrator import orchestrate


async def main():
    result = await orchestrate({"user_query": "attention mechanism"})
    plan = result.get("research_plan", [])
    print(f"子查询数量: {len(plan)}")
    for i, task in enumerate(plan, 1):
        print(f"  {i}. {task['sub_query'][:100]}")
    print(f"\n原始 plan: {plan}")


if __name__ == "__main__":
    asyncio.run(main())
