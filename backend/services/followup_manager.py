import asyncio
import re
import logging

from backend.agents.followup import answer_followup
from backend.config import settings, current_settings, settings_scope


class FollowUpManager:
    def __init__(self, repository, tasks, results, answerer=None, configuration=None):
        self.configuration = configuration or current_settings()
        self.repository, self.tasks, self.results = repository, tasks, results
        self.answerer = answerer or answer_followup
        self._worker = None
        self._wake = asyncio.Event()
        self._stopping = False
        self.storage_failed = False

    async def start(self):
        await self.repository.recover()
        with settings_scope(self.configuration):
            self._worker = asyncio.create_task(self._run())
        self._worker.add_done_callback(self._observe)

    def _observe(self, future):
        if not future.cancelled():
            error = future.exception()
            if error is not None:
                self.storage_failed = True
                logging.getLogger(__name__).error("Follow-up worker failed: %s", type(error).__name__)

    def wake(self):
        self._wake.set()

    async def shutdown(self):
        if self._worker:
            self._stopping = True
            self._wake.set()
            try:
                await asyncio.wait_for(asyncio.shield(self._worker), timeout=5)
            except asyncio.TimeoutError:
                self._worker.cancel()
                await asyncio.gather(self._worker, return_exceptions=True)

    async def _run(self):
        while not self._stopping:
            self._wake.clear()
            job = await self.repository.claim()
            if not job:
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    pass
                continue
            try:
                task = await self.tasks.get(job["task_id"])
                result = await self.results.get(job["task_id"])
                if not task or not result:
                    raise ValueError("Research result unavailable")
                snapshot = await self.repository.snapshot(task.id)
                if settings.research_runner_mode == "demo":
                    await asyncio.sleep(max(0.1, settings.demo_delay_seconds))
                    text = "这是基于当前报告的演示回答；未发起新的检索。" if task.effective_locale == "zh-CN" else "This demo answer uses the existing report; no new research was started."
                    valid = [c["citation_id"] for c in result.citations if c.get("valid") and c.get("citation_id")]
                    answer = {"answer": text + (f" [[CITE:{valid[0]}]]" if valid else ""), "citations": valid[:1]}
                else:
                    answer = await self.answerer(job["content"], {"query": task.query,
                        "effective_locale": task.effective_locale,
                        "result": {**result.model_dump(), "final_answer": result.report_markdown}}, snapshot["messages"])
                    valid = {c["citation_id"] for c in result.citations if c.get("valid") and c.get("citation_id")}
                    answer["answer"] = re.sub(r"\[\[CITE:([^\]]+)\]\]", lambda m: m[0] if m[1] in valid else "", answer.get("answer", ""))
                    answer["citations"] = [c for c in re.findall(r"\[\[CITE:([^\]]+)\]\]", answer["answer"]) if c in valid]
                if not answer.get("answer", "").strip():
                    raise ValueError("Empty answer")
                await self.repository.finish(job, answer)
            except asyncio.CancelledError:
                raise
            except Exception:
                await self.repository.finish(job)
