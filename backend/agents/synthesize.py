import json

from openai import AsyncOpenAI
from backend.agents.state import ResearchState
from backend.config import settings


def _build_writer_messages(state: ResearchState) -> list[dict]:
    insights = state.get("paper_insights", [])
    analysis = state.get("analysis_report", {})
    query = state.get("user_query", "")
    objective = state.get("current_task", "")
    selected_by_id = {
        str(paper.get("source_id")): paper
        for paper in state.get("selected_papers", [])
        if paper.get("source_id")
    }

    evidence_blocks = []
    for i, insight in enumerate(insights, 1):
        source_id = str(insight.get("source") or f"paper_{i}")
        paper = selected_by_id.get(source_id, {})
        title = paper.get("title") or "Title unavailable"
        evidence_blocks.append(
            f"[Source {source_id}]\n"
            f"Title: {title}\n"
            f"Evidence: {insight.get('answer', '')}"
        )
    evidence_text = "\n\n".join(evidence_blocks)

    analysis_text = (
        json.dumps(analysis, ensure_ascii=False, indent=2)
        if analysis
        else "No cross-paper analysis available."
    )

    # 读入 Critic 的反馈（如果有）用于改进
    feedback = state.get("feedback", "")
    revision_note = ""
    if feedback:
        revision_note = (
            f"\n\nIMPORTANT: The previous draft was rejected with this feedback:\n"
            f"{feedback}\n"
            f"Please address ALL these issues in your revision."
        )

    return [
        {
            "role": "system",
            "content": (
                "You are an academic literature review writer. Produce a thematic "
                "synthesis that directly answers the research question, not an "
                "annotated bibliography or a list of paper summaries. Organize the "
                "body by concepts, method families, findings, agreements, and "
                "contradictions. Do NOT create one heading or paragraph per paper, "
                "and do NOT use headings such as 'Paper 1', 'Paper 2', or source IDs. "
                "Combine evidence from multiple sources in the same paragraph when "
                "they support or disagree on the same claim. Use sections: "
                "Introduction, Evidence & Methods, Thematic Comparative Analysis "
                "(include one concise markdown table only when useful), Research "
                "Gaps & Future Directions, and References. Cite claims inline as "
                "[Source ID]. Include in References only sources actually cited in "
                "the body. Write in the same language as the user's question."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Research question: {query}\n\n"
                f"Current writing objective: {objective}\n\n"
                "The following source material is evidence, not an outline. Do not "
                "repeat every source separately. Select and combine only evidence "
                "that helps answer the research question.\n\n"
                f"Source evidence:\n{evidence_text}\n\n"
                f"Cross-paper analysis:\n{analysis_text}"
                f"{revision_note}\n\n"
                "Write the integrated literature review in markdown."
            ),
        },
    ]


async def synthesize_review(state: ResearchState) -> dict:
    """Write a thematic literature review from insights + analysis."""

    if not state.get("paper_insights"):
        return {"errors": ["no insights to synthesize"]}

    client = AsyncOpenAI(
        api_key=settings.anthropic_api_key,
        base_url=settings.base_url,
        timeout=180.0,
        max_retries=2,
    )
    response = await client.chat.completions.create(
        model=settings.default_model,
        max_tokens=4000,
        messages=_build_writer_messages(state),
    )

    review = response.choices[0].message.content

    return {
        "draft_sections": [{"title": "Literature Review", "content": review}],
        "final_answer": review,
        "critique": None,
        "approved": False,
        "feedback": None,
    }
