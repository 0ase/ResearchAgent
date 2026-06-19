from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings


async def synthesize_review(state: ResearchState) -> dict:
    """Write a structured literature review from insights + analysis"""

    insights = state.get("paper_insights", [])
    analysis = state.get("analysis_report", {})
    query = state.get("user_query", "")

    if not insights:
        return {"errors": ["no insights to synthesize"]}

    context_parts = []
    for i, insight in enumerate(insights):
        context_parts.append(
            f"### Paper {i+1}\n{insight.get('answer', '')}"
        )
    paper_summaries = "\n\n".join(context_parts)

    analysis_text = str(analysis) if analysis else "No cross-paper analysis available."

    # 读入 Critic 的反馈（如果有）用于改进
    feedback = state.get("feedback", "")
    revision_note = ""
    if feedback:
        revision_note = (
            f"\n\nIMPORTANT: The previous draft was rejected with this feedback:\n"
            f"{feedback}\n"
            f"Please address ALL these issues in your revision."
        )

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=180.0,
        max_retries=2,
    )
    response = await client.chat.completions.create(
        model=settings.default_model,
        max_tokens=4000,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an academic literature review writer. "
                    "Write a structured review with sections: "
                    "Introduction, Methods, Comparative Analysis (use a markdown table), "
                    "Research Gaps & Future Directions, References. "
                    "Use markdown formatting. Cite papers by their Paper ID."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research question: {query}\n\n"
                    f"Paper summaries:\n{paper_summaries}\n\n"
                    f"Cross-paper analysis:\n{analysis_text}"
                    f"{revision_note}\n\n"
                    "Write a literature review in markdown."
                ),
            },
        ],
    )

    review = response.choices[0].message.content

    return {
        "draft_sections": [{"title": "Literature Review", "content": review}],
        "final_answer": review,
    }
