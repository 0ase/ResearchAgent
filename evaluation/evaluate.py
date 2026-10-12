"""Reproducible offline metrics; missing evidence produces N/A, never estimates."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import statistics

from evaluation.collect import ROOT, atomic_json, number, utc_now


def percentile(values: list[float], percent: float):
    if not values:
        return None
    return sorted(values)[max(0, math.ceil(percent / 100 * len(values)) - 1)]


def average(values):
    return statistics.fmean(values) if values else None


def metric(identifier, label, value, unit, samples, definition, reason="", *, partial=False, numerator=None, denominator=None):
    return {"id": identifier, "label": label, "value": round(value, 4) if value is not None else None,
            "unit": unit, "samples": samples, "status": "unavailable" if value is None else "partial" if partial else "available",
            "definition": definition, "reason": reason if value is None or partial else "", "numerator": numerator, "denominator": denominator}


def rate(identifier, label, numerator, denominator, definition, reason=""):
    return metric(identifier, label, numerator / denominator * 100 if denominator else None, "%", denominator,
                  definition, reason if not denominator else "", numerator=numerator, denominator=denominator)


def token_total(run, kind, complete=True):
    calls = run.get(kind + "_calls") or []
    if complete and (not run.get("usage_observed") or any(call.get("status") != "completed" or number(call.get("total_tokens")) is None for call in calls)):
        return None
    totals = [number(call.get("total_tokens")) for call in calls]
    known = [value for value in totals if value is not None]
    if not complete and not known:
        return None
    return sum(known)


def load_labels(path: Path | None) -> list[dict]:
    if path is None:
        return []
    records = []
    with path.open(encoding="utf-8-sig") as file:
        for index, line in enumerate(file, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict) or record.get("example_only"):
                raise ValueError(f"Labels line {index} is not a usable gold annotation")
            if not any(record.get(key) for key in ("session_id", "request_id", "query_hash")):
                raise ValueError(f"Labels line {index} has no run selector")
            if record.get("facts") and not (record.get("session_id") or record.get("request_id")):
                raise ValueError("Fact labels must identify one report, not every run of a query")
            records.append(record)
    return records


def _label_for(run, labels):
    matches = [label for label in labels if any(label.get(key) for key in ("session_id", "request_id", "query_hash"))
               and all(not label.get(key) or label[key] == run.get(key) for key in ("session_id", "request_id", "query_hash"))]
    if len(matches) > 1:
        raise ValueError("More than one gold annotation matches one research run")
    return matches[0] if matches else None


def quality_metrics(completed: list[dict], labels: list[dict]) -> list[dict]:
    hits, recalls, reciprocals, rag_ks = [], [], [], set()
    precision_num = precision_den = recall_num = recall_den = 0
    paper_ks = set()
    supported = facts_total = cited = citation_total = 0
    rag_missing = paper_missing = fact_missing = 0
    for run in completed:
        label = _label_for(run, labels)
        if not label:
            continue
        result = run.get("result") or {}
        rag = label.get("rag")
        if isinstance(rag, list) and rag:
            k = label.get("rag_k", 6)
            if not isinstance(k, int) or isinstance(k, bool) or k < 1:
                raise ValueError("rag_k must be a positive integer")
            valid = run.get("retrieval_observed") and run.get("retrieval_top_k") == k
            retrieval = {r.get("paper_id"): r for r in run.get("retrievals", [])}
            values = []
            for unit in rag:
                gold = unit.get("relevant_chunk_ids") if isinstance(unit, dict) else None
                paper = unit.get("paper_id") if isinstance(unit, dict) else None
                if not paper or not isinstance(gold, list) or not gold or not all(isinstance(i, str) and i for i in gold):
                    raise ValueError("Each RAG gold unit needs a paper_id and nonempty relevant_chunk_ids")
                if paper not in result.get("read_paper_ids", []):
                    values.append((0, 0, 0))
                    continue
                retrieved = retrieval.get(paper)
                if not retrieved or not retrieved.get("ids_available"):
                    valid = False
                    break
                ids = retrieved.get("ids", [])[:k]
                positions = [i + 1 for i, chunk in enumerate(ids) if chunk in set(gold)]
                values.append((int(bool(positions)), len(set(ids) & set(gold)) / len(set(gold)), 1 / min(positions) if positions else 0))
            if valid:
                rag_ks.add(k)
                for hit, recall, reciprocal in values:
                    hits.append(hit); recalls.append(recall); reciprocals.append(reciprocal)
            else:
                rag_missing += 1
        paper = label.get("papers")
        if isinstance(paper, dict):
            k = paper.get("k", 15)
            if not isinstance(k, int) or isinstance(k, bool) or k < 1:
                raise ValueError("Paper k must be a positive integer")
            selected = result.get("selected_paper_ids", [])[:k]
            judgments = paper.get("judgments")
            gold = paper.get("reference_paper_ids")
            if result.get("selected_available") and isinstance(judgments, dict) and all(judgments.get(pid) in (0, 1) for pid in selected):
                paper_ks.add(k)
                precision_num += sum(judgments[pid] for pid in set(selected))
                precision_den += k  # Duplicate papers and missing slots never improve the score.
                if isinstance(gold, list) and gold:
                    recall_num += len(set(selected) & set(gold)); recall_den += len(set(gold))
            else:
                paper_missing += 1
        facts = label.get("facts")
        if isinstance(facts, list) and facts:
            statuses = [fact.get("status") for fact in facts if isinstance(fact, dict)]
            if len(statuses) == len(facts) and all(s in {"supported", "partial", "unsupported", "contradicted"} for s in statuses):
                supported += statuses.count("supported"); facts_total += len(facts)
                if all(isinstance(fact.get("has_resolved_citation"), bool) for fact in facts):
                    cited += sum(fact["has_resolved_citation"] for fact in facts); citation_total += len(facts)
            else:
                fact_missing += 1
    rag_reason = "尚无匹配的金标准标注或实际检索 ID；非空返回不能代替相关性命中。"
    if rag_missing:
        rag_reason = f"{rag_missing} 个标注任务因观测缺失未评分，数值仅覆盖有效观测单位。" if hits else rag_reason + f" {rag_missing} 个标注任务因观测缺失未评分。"
    if len(rag_ks) > 1:
        hits, recalls, reciprocals = [], [], []
        rag_reason = "标注中包含不同的 K；请分批计算，不混合为单一 Hit@K。"
    suffix = str(next(iter(rag_ks))) if len(rag_ks) == 1 else "K"
    if len(paper_ks) > 1:
        precision_num = precision_den = recall_num = recall_den = 0
    paper_suffix = str(next(iter(paper_ks))) if len(paper_ks) == 1 else "K"
    paper_reason = f"需要筛选列表和完整相关性标注；{paper_missing} 个标注任务缺记录或待评。"
    return [
        metric("rag_hit_rate", f"RAG Hit@{suffix}", average(hits) * 100 if hits else None, "%", len(hits),
               "已完成且标注的问题—参考论文对中，前 K 个实际阅读切片至少有一个金标准切片的比例；未读到参考论文记未命中。", rag_reason, partial=bool(rag_missing)),
        metric("rag_recall", f"Context Recall@{suffix}", average(recalls) * 100 if recalls else None, "%", len(recalls),
               "按问题—参考论文对平均：实际阅读切片找回的金标准 chunk ID 数 / 该对的金标准 chunk ID 总数。", rag_reason, partial=bool(rag_missing)),
        metric("rag_mrr", f"MRR@{suffix}", average(reciprocals), "score", len(reciprocals),
               "第一个相关阅读切片排名的倒数均值，未命中记 0；相同 K 的已标注单位。", rag_reason, partial=bool(rag_missing)),
        rate("paper_precision", f"Paper Precision@{paper_suffix}", precision_num, precision_den,
             "筛选前 K 个位置中相关的不同论文数 / 总位置数；不足 K 的空位和重复项不计相关。", paper_reason),
        rate("paper_recall", f"Paper Recall@{paper_suffix}", recall_num, recall_den,
             "选中前 K 项找回的参考论文数 / 标注中的有限参考论文数，非对所有论文的绝对召回。", paper_reason),
        rate("fact_support_rate", "事实支持率", supported, facts_total,
             "逐事实人工标注中完全 supported 的数量 / 所有需证据的正文事实；partial 不计支持，pending 报告不评分。",
             f"需要逐报告事实标注；{fact_missing} 个报告待评或标注不完整。"),
        rate("citation_coverage", "引用覆盖率", cited, citation_total,
             "有可解析且明确归属的正文引用的标注事实数 / 已完整标注的需证据事实数；目录条目不计。",
             "尚无完整的正文事实及引用归属标注。"),
    ]


def evaluate(snapshot: dict, labels: list[dict] | None = None) -> dict:
    labels = labels or []
    runs = [r for r in snapshot.get("runs", []) if r.get("task_started")]
    complete = [r for r in runs if r.get("status") == "completed"]
    terminal = [r for r in runs if r.get("status") in {"completed", "failed", "cancelled"}]
    counts = Counter(r.get("status", "incomplete") for r in runs)
    durations = [number(r.get("server_elapsed_seconds")) for r in complete]
    durations = [d for d in durations if d is not None]
    n = len(durations)
    latency = [metric(f"latency_p{p}", f"P{p} 完成耗时", percentile(durations, p), "seconds", n,
                      "成功任务服务端接收研究请求至响应流结束的处理时间；nearest-rank 分位数，不含客户端网络与排队。",
                      "没有带有效计时的成功任务。") for p in (50, 95, 99)]
    latency.append(metric("mean_completion_seconds", "平均完成耗时", average(durations), "seconds", n,
                          "成功任务服务端完整处理时间的算术平均，含内部重试；失败和取消另列。", "没有带有效计时的成功任务。"))
    llm_totals = [token_total(r, "llm") for r in terminal]
    llm_totals = [value for value in llm_totals if value is not None]
    embedding_totals = [token_total(r, "embedding") for r in terminal]
    embedding_totals = [value for value in embedding_totals if value is not None]
    recorded = [token_total(r, "llm", complete=False) for r in terminal]
    recorded = [value for value in recorded if value is not None]
    usage_reason = "历史 usage 仅覆盖部分节点；使用独立观测入口积累完整任务 usage 后可计算。"
    resource = [
        metric("mean_llm_tokens", "平均 LLM token", average(llm_totals), "tokens", len(llm_totals),
               "完整 usage 的已终止任务中，全部可见 LLM 调用 total_tokens 之和的均值，含应用重试；失败调用缺 usage 的任务不纳入。", usage_reason),
        metric("mean_embedding_tokens", "平均 embedding token", average(embedding_totals), "tokens", len(embedding_totals),
               "完整 usage 的已终止任务中，所有 embedding 调用 total_tokens 之和的均值，单列于 LLM。", usage_reason),
        rate("token_usage_coverage", "完整 usage 覆盖率", len(llm_totals), len(terminal),
             "LLM 调用 usage 均完整的终止任务数 / 已确认终止任务数；没有记录不等于没有消耗。", "没有已确认终止任务。"),
        metric("mean_recorded_llm_tokens", "已记录 LLM token 均值", average(recorded), "tokens", len(recorded),
               "至少有 usage 的终止任务，已记录的 LLM total_tokens 之和的均值；可能只是下界，不是全任务平均消耗。",
               "历史筛选/分析 usage 仅为部分调用；不可与完整 token 均值混用。", partial=True),
    ]
    selected = read = known_read_runs = 0
    for run in complete:
        result = run.get("result") or {}
        if result.get("selected_available"):
            selected += len(set(result.get("selected_paper_ids", [])))
            read += len(set(result.get("selected_paper_ids", [])) & set(result.get("read_paper_ids", [])))
            known_read_runs += 1
    runtime = [
        rate("task_completion_rate", "任务完成率", counts["completed"], len(terminal),
             "保存非空报告或收到非空 done 的任务 / 已确认终态任务；不等于内容质量达标。", "暂无确认终态。"),
        rate("task_failure_rate", "任务失败率", counts["failed"], len(terminal), "明确失败任务 / 已确认终态任务；SSE HTTP 200 错误仍算失败。", "暂无确认终态。"),
        rate("task_cancellation_rate", "任务取消率", counts["cancelled"], len(terminal), "明确取消任务 / 已确认终态任务。", "暂无确认终态。"),
        rate("terminal_coverage", "终态记录覆盖率", len(terminal), len(runs), "已确认完成、失败或取消的任务 / 有启动证据的研究；未知/未闭合记录单列。", "暂无研究启动记录。"),
        rate("degraded_rate", "完成但降级比例", sum(bool(r.get("degraded")) for r in complete), len(complete),
             "存在阶段降级、结果 warnings 或 writer_incomplete 的完成任务 / 完成任务。", "暂无完成任务。"),
        rate("paper_read_success_rate", "论文阅读结果率", read, selected,
             f"已完成且保留筛选列表的 {known_read_runs} 个任务：有非空阅读摘要的不同入选论文 / 不同入选论文；不代表摘要正确。", "缺少有效筛选列表或入选论文。"),
        rate("application_retry_rate", "应用级重试任务比例", sum(bool(r.get("application_retry")) for r in terminal), len(terminal),
             "记录筛选拆批修复、分析重试或 embedding 重试的终止任务 / 终止任务；不包括 SDK 内部不可见的 HTTP 重试。", "暂无终止任务。"),
    ]
    retrieval = [item for run in complete if run.get("retrieval_observed") for item in run.get("retrievals", []) if item.get("ids_available")]
    quality = quality_metrics(complete, labels)
    quality.append(rate("retrieval_nonempty_rate", "检索非空返回率", sum(bool(r.get("ids")) for r in retrieval), len(retrieval),
                        "有实际 ID 记录的完成任务阅读检索中，返回非空上下文的次数 / 检索次数；仅反映可用性，非 RAG 相关性命中率。", "现有历史未记录实际检索 ID。"))
    stage_events = defaultdict(list)
    for run in runs:
        for event in run.get("stage_events", []):
            if event.get("stage"):
                stage_events[event["stage"]].append(event)
    stages = []
    for stage, events in sorted(stage_events.items()):
        values = [e["duration_ms"] / 1000 for e in events if e.get("event") == "stage.completed" and number(e.get("duration_ms")) is not None]
        stages.append({"stage": stage, "started": sum(e.get("event") == "stage.started" for e in events),
                       "completed": len(values), "failed": sum(e.get("event") == "stage.failed" for e in events),
                       "degraded": sum(e.get("event") == "stage.degraded" for e in events),
                       "mean_seconds": average(values), "p50_seconds": percentile(values, 50),
                       "p95_seconds": percentile(values, 95), "p99_seconds": percentile(values, 99)})
    notes = list(snapshot.get("notes", []))
    if n and n < 100:
        notes.append(f"成功计时样本仅 {n} 个，P99 接近样本最大值，不能作为生产 SLA。")
    notes.append("供应商未返回 usage 的失败/断开调用及 SDK 内部计费不可据此还原；token 统计不等于供应商账单。")
    dates = [r["started_at"] for r in runs if r.get("started_at")]
    endings = [r.get("ended_at") or r.get("started_at") for r in runs if r.get("started_at")]
    return {"schema_version": 1, "generated_at": utc_now(), "population": {
                "started": len(runs), "completed": counts["completed"], "failed": counts["failed"],
                "cancelled": counts["cancelled"], "incomplete": counts["incomplete"],
                "timed_successes": n, "complete_usage_runs": len(llm_totals), "labeled_runs": sum(_label_for(r, labels) is not None for r in complete)},
            "window": {"start": min(dates) if dates else None, "end": max(endings) if endings else None},
            "groups": [{"id": "latency", "label": "耗时", "metrics": latency},
                       {"id": "resource", "label": "资源消耗", "metrics": resource},
                       {"id": "runtime", "label": "运行可靠性", "metrics": runtime},
                       {"id": "quality", "label": "检索与证据质量", "metrics": quality}],
            "stages": stages, "diagnostics": snapshot.get("diagnostics", {}), "notes": notes}


def markdown(report: dict) -> str:
    population = report["population"]
    lines = ["# B1GONE 本机指标快照", "", f"生成：{report['generated_at']}",
             f"研究启动 {population['started']}；完成 {population['completed']}；失败 {population['failed']}；取消 {population['cancelled']}；未知 {population['incomplete']}。", ""]
    for group in report["groups"]:
        lines.extend(["## " + group["label"], "", "| 指标 | 数值 | 样本/单位 | 口径与缺失 |", "| --- | --- | --- | --- |"])
        for item in group["metrics"]:
            value = "N/A" if item["value"] is None else str(item["value"]) + " " + item["unit"]
            lines.append(f"| {item['label']} | {value} | {item['samples']} | {item['definition']} {item['reason']} |")
        lines.append("")
    lines.extend(["## 限制", ""] + ["- " + note for note in report["notes"]])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "evaluation/runs/collected.json")
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "web/public/metrics/summary.json")
    parser.add_argument("--report", type=Path, default=ROOT / "evaluation/reports/latest.md")
    args = parser.parse_args()
    snapshot = json.loads(args.input.read_text(encoding="utf-8"))
    report = evaluate(snapshot, load_labels(args.labels))
    atomic_json(args.output, report, allow_locked_rewrite=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(markdown(report), encoding="utf-8")
    print(f"Published aggregate metrics for {report['population']['started']} research runs.")


if __name__ == "__main__":
    main()
