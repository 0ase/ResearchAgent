from backend.agents.contracts import SupervisorDecision
from backend.agents.state import ResearchState
from backend.config import settings

def validate_decision(
    decision: SupervisorDecision,
    state: ResearchState,
) -> SupervisorDecision:
    step_count = state.get("step_count", 0)
    max_steps = state.get("max_steps", 12)

    if step_count >= max_steps:
        return decision.model_copy(update={
            "next_agent": "finish",
            "objective": "使用已有资料生成当前能够提供的最佳答案",
            "reason": "达到最大Agent调用次数",
        })
    
    target = decision.next_agent

    has_insights = bool(state.get("paper_insights"))
    has_analysis = bool(state.get("analysis_report"))
    has_draft = bool(state.get("draft_sections"))
    critique = state.get("critique") or {}

    if state.get("retrieval_exhausted") and not has_insights:
        return decision.model_copy(update={
            "next_agent": "finish",
            "objective": "结束无法取得论文证据的研究任务",
            "reason": "检索已耗尽且没有可用论文",
        })

    # 一旦当前草稿已通过评审，任何新的模型路由决定都必须被终止规则覆盖。
    # 如果上游证据、分析或草稿发生变化，对应 Agent 会先清空 critique。
    if has_draft and critique.get("approved") is True:
        return decision.model_copy(update={
            "next_agent": "finish",
            "objective": "返回已经通过质量评审的研究综述",
            "reason": "当前草稿已通过质量评审",
        })

    if (
        has_draft
        and critique
        and critique.get("approved") is not True
        and state.get("critique_round", 0) >= settings.max_critique_rounds
    ):
        return decision.model_copy(update={
            "next_agent": "finish",
            "objective": "返回达到评审轮次上限后的最佳研究综述",
            "reason": "已达到最大质量评审轮次",
        })

    if target in {"analysis", "writer"} and not has_insights:
        return decision.model_copy(update={
            "next_agent": "retrieval",
            "objective": "搜索并阅读与用户问题相关的论文",
            "reason": "分析和写作需要论文证据",
        })
    
    if target == "critic" and not has_draft:
        if not has_insights:
            return decision.model_copy(update={
                "next_agent": "retrieval",
                "objective": "搜索并阅读与用户问题相关的论文",
                "reason": "生成和评审报告前需要论文证据",
            })
        if not has_analysis:
            return decision.model_copy(update={
                "next_agent": "analysis",
                "objective": "比较论文共识、冲突、方法差异和研究空白",
                "reason": "生成和评审报告前需要跨论文分析",
            })
        return decision.model_copy(update={
            "next_agent": "writer",
            "objective": "根据当前论文证据生成草稿",
            "reason": "Critic需要现有报告草稿",
        })
    
    if target == "writer" and has_insights and not has_analysis:
        return decision.model_copy(update={
            "next_agent": "analysis",
            "objective": "比较论文共识、冲突、方法差异和研究空白",
            "reason": "写作前缺少跨论文分析",
        })
    

    if target == "finish" and not has_draft:
        if not has_insights:
            return decision.model_copy(update={
                "next_agent": "retrieval",
                "objective": "搜索并阅读与用户问题相关的论文",
                "reason": "结束前需要论文证据",
            })
        if not has_analysis:
            return decision.model_copy(update={
                "next_agent": "analysis",
                "objective": "比较论文共识、冲突、方法差异和研究空白",
                "reason": "结束前需要跨论文分析",
            })
        return decision.model_copy(update={
            "next_agent": "writer",
            "objective": "生成最终研究报告",
            "reason": "结束前必须生成报告",
        })


    if target == "finish" and not critique:
        return decision.model_copy(update={
            "next_agent": "critic",
            "objective": "检查报告完整性、证据和引用质量",
            "reason": "报告尚未经过质量评审",
        })

    if target == "finish" and not critique.get("approved", False):
        issue_type = critique.get("issue_type", "writing_quality")

        route_by_issue = {
            "insufficient_evidence": "retrieval",
            "analysis_gap": "analysis",
            "citation_error": "retrieval",
            "writing_quality": "writer",
        }

        return decision.model_copy(update={
            "next_agent": route_by_issue.get(issue_type, "writer"),
            "objective": critique.get(
                "feedback",
                "根据评审意见修正研究报告",
            ),
            "reason": f"评审未通过：{issue_type}",
        })

    return decision
