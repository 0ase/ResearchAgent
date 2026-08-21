from __future__ import annotations


PIPELINE_ERROR_MESSAGES = {
    "NO_RESEARCH_RESULTS": "未检索到可用论文",
    "NO_READABLE_PAPERS": "检索到的论文均无法读取",
    "NO_PAPER_INSIGHTS": "未能生成论文洞察",
    "EMPTY_REPORT": "研究报告为空，无法完成任务",
}


class ResearchPipelineError(RuntimeError):
    """A safe, stable error that may be exposed in task status/events."""

    def __init__(self, code: str, public_message: str | None = None) -> None:
        if code not in PIPELINE_ERROR_MESSAGES:
            raise ValueError(f"unsupported research pipeline error: {code}")
        self.code = code
        self.public_message = public_message or PIPELINE_ERROR_MESSAGES[code]
        super().__init__(self.public_message)
