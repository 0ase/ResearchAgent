# B1GONE 本机运行指标

独立脚本读取现有日志和 SQLite，计算真实运行统计。默认不创建研究、不请求模型，不修改后端业务代码、数据库、环境配置或缓存。首页下滑可以查看生成的脱敏汇总；`?demo=1` 也展示真实运行统计，演示任务不纳入。

## 更新首页数据

从项目根目录使用 BIGONE 环境：

```powershell
cd D:\BIGONE
conda activate BIGONE
python -m evaluation.update_metrics
```

然后在首页下滑，点击“刷新读数”。该命令生成：

- `evaluation/runs/collected.json`：本地规范化快照，有追踪 ID、使用量和检索 ID，无提示词或报告正文。
- `evaluation/reports/latest.md`：指标、统计单位、分母和缺失原因。
- `web/public/metrics/summary.json`：前端读取的聚合数据，不包含查询、密钥、报告、单任务 ID 或检索 ID。

以上生成文件以及实际 `evaluation/labels.jsonl` 已被 Git 忽略。发布前先运行更新命令再构建前端，Vite 会复制当时的汇总快照；它不是自动更新的后端接口。

发布默认原子替换。Windows 静态文件读者允许写入但锁定重命名时，只有公开汇总允许回写；前端验证完整 JSON，刷新失败保留上次快照，初次读取失败显示暂无数据。本地观测明细始终采用原子写入。

可持续离线刷新，也可按时间过滤：

```powershell
python -m evaluation.update_metrics --watch --interval 30
python -m evaluation.update_metrics --since "2026-10-11T12:00:00+00:00"
```

独立执行采集和计算：

```powershell
python -m evaluation.collect --db D:/BIGONE/data/research.db
python -m evaluation.evaluate --labels evaluation/labels.jsonl
```

`--logs`、`--db`、`--observations`、`--output` 可以指定其他目录。SQLite 使用 `mode=ro`；库不存在时不创建，读取失败时保留日志并说明。采集只使用当前代码实际写入的 `sessions` 和研究请求日志，不把其他版本的 `research_tasks` 等表混入当前统计。

## 今后的完整 usage 与 RAG 观测

旧日志只记录筛选/分析 usage，无法还原主控、拆解、阅读、写作、评审和 embedding 的总消耗。旧阅读结果也没有实际检索 chunk ID，所以完整平均 token 和 RAG 质量显示 N/A。

如需积累这些记录，下次启动后端时可使用独立观测入口，替代原 Uvicorn 入口：

```powershell
cd D:\BIGONE
conda activate BIGONE
python -m uvicorn evaluation.observed_app:app --host 127.0.0.1 --port 3000 --reload --reload-dir backend --reload-dir evaluation
```

原 `scripts/start_backend.ps1` 和 `backend.main:app` 保持可用；使用原入口时仍能统计已有日志，但不会新增完整 usage 记录。本次没有重启用户后端或额外执行付费研究。

观测入口包装相同的 app，原接口、模型参数及返回值不变。仅对研究 POST 请求采集：

- 每次 AsyncOpenAI chat/embedding 响应的供应商 usage，单独记录失败调用的未知消耗。
- 真实 `CollectionProxy.get/query` 返回的切片 ID 与排序；阅读使用首批切片降级时记录为 fallback，不能冒充向量排序。
- 服务端响应时长、节点事件和 SSE 终态；HTTP 200 的 error 仍是失败。

记录原子写入 `evaluation/runs/observed/`。同一任务的日志与观测按 request/session ID 合并，观测优先；原始提示词、论文正文、响应正文、异常堆栈和凭证不写入。观测失败不修改业务返回。后台单进程默认启动即可；SDK 内部 HTTP 重试的失败账单仍无法从 usage 完整还原。

## 口径

| 指标 | 定义与边界 |
| --- | --- |
| P50/P95/P99、平均完成耗时 | 成功任务的服务端完整处理时间，单位秒；含内部重试与保存结果，不含客户端网络、队列或离线评分。nearest-rank：第 `ceil(p × n)` 项。小样本 P99 接近样本最大值，不是 SLA。 |
| 任务完成/失败/取消率 | 分母为确认终态任务，另列启动总数、未知记录和终态覆盖率。成功须有保存的非空报告或非空 done；HTTP 200 本身不算成功。 |
| 平均 LLM token | 仅完整 usage 的终止任务，各可见 LLM 调用 `total_tokens` 之和的均值；任务内部应用重试都计入。reasoning 已包含在 completion 时不重复添加。 |
| 平均 embedding token | 独立汇总 embedding usage，不与 LLM 的输入/输出消耗混算。 |
| 已记录 LLM token 均值 | 只有部分 usage 的历史也可以统计已知数，但它可能是下界，不是全流程平均消耗。与完整均值分开显示。 |
| 降级比例、阅读结果率 | 完成但存在 warnings/不完整写作的比例；有非空阅读摘要的不同入选论文 / 入选论文。这些不是内容正确率。 |
| 应用级重试比例 | 显式记录筛选修复、分析重试、embedding 重试的任务比例，不包含 SDK 内部不可见重试。 |
| RAG Hit@K | 已完成、已标注的问题—参考论文对，前 K 个实际阅读 chunk 至少一个相关的比例。预定参考论文没有读到仍记未命中。缺观测不当作未命中。 |
| Context Recall@K / MRR@K | 相对冻结 gold chunk IDs 的召回率、首个相关切片排名倒数；不是对全部相关知识的绝对召回率。不同 K 不混合。 |
| 非空检索率 | 仅表示有上下文返回，不能代替 RAG 相关性命中率。 |
| Paper Precision/Recall@K | 使用真实筛选顺序与完整标注；不足 K 的空位和重复论文不能提高精确率，召回相对有限参考集。 |
| 事实支持率 / 引用覆盖率 | 来自每份报告的人工原子事实标注；完整支持才计支持，有可定位正文引用才计覆盖。目录条目和模型自评分不能代替这些标注。 |

当前历史来自不同开发版本、问题、模型和缓存条件。需要比较版本时，应冻结测试问题、金标准、模型/检索预算和并发，记录相同缓存条件，分批采集，不从混合开发历史宣称模型或 Agent 优劣。

## 添加金标准标注

`labels.example.jsonl` 仅示例，带 `example_only` 标记，脚本拒绝将其计分。建立自己的 `evaluation/labels.jsonl`，每行一个真实标注：

- 使用 `session_id` 或 `request_id` 指定一份报告；也可用采集快照里的 `query_hash` 匹配重复问题的论文/RAG 金标准。
- `rag_k` 必须与观测记录的 `retrieval_top_k` 一致。`rag` 预先固定参考论文及真实 `relevant_chunk_ids`，不能只挑系统命中的切片。冻结文献索引；重建索引后重新核对 ID 对应内容。
- `papers.k` 指定筛选截止数量；`judgments` 为返回位置的 0/1 相关性标注，未标注和 pending 不算不相关；`reference_paper_ids` 是有限参考集。
- `facts` 必须指定一个真实 session/request，不能把同一问题某份报告的判定应用到所有报告。`status` 为 supported/partial/unsupported/contradicted/pending，`has_resolved_citation` 记录是否有明确归属的正文引用。

在运行中任务还未闭合时，报告会把它记为未知。对日志轮转丢失、重复 request ID、数据库独有报告及缺失 usage/标注都保留说明。不要把 N/A 填成 0，亦不要把无证据的成功记成 100%。

## 检查

```powershell
python -m unittest discover -s evaluation/tests -v
```

测试使用临时数据库、假 SDK 和假 ASGI，不调用真实模型。公式与观测职责独立，可反复重算同一快照。

指标参考：[Ragas Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)、[LangSmith ExperimentRunStats](https://reference.langchain.com/python/langsmith/schemas/ExperimentRunStats)。不安装这些平台，也不上传本地评测材料。
