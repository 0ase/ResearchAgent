# B1GONE 指标采集与首页展示施工计划

日期：2026-10-11。前端基线已提交为 `edcf645`。本轮只新增独立评测脚本和修改首页，不改后端 Agent、路由、配置默认值、数据库结构或现有启动脚本。

## 当前数据与统计边界

当前分支提供 `/api/research/stream` 等旧研究接口，实际保存到 `sessions`；旧评测计划中的 `/api/v1/research/tasks` 在当前代码中不存在，不能直接套用。日志有 `request.*`、`stage.*`，筛选与分析响应有部分 usage；阅读结果没有实际 chunk ID，全流程 usage 也没有完整记录。

先只读现有 JSON 日志和 SQLite，区分成功、失败、取消及记录不完整的研究。HTTP 200 不等于 SSE 任务成功。完成须有保存的非空报告或观测到 `done`；无终态证据记未知，不猜测成功。数据库只读连接使用 `mode=ro`，不迁移、不清空缓存，不读取或导出密钥。

## 指标定义

- **P50 / P95 / P99、平均任务完成耗时**：成功任务的实际耗时，nearest-rank 分位数，单位秒；服务端处理耗时与可选客户端端到端耗时分开。显示有效样本数，P99 小样本时说明它接近最大观测值。
- **任务完成率、失败率、取消率、降级比例**：以有启动证据的研究任务为总体，保留未知/未闭合记录；终态比例使用已确认终态为分母，同时展示终态记录覆盖率。完成不等于人工确认质量。
- **平均 LLM token / 平均 embedding token**：分别汇总供应商返回的 usage；重复日志不重复计算，同一任务内部多次模型调用都计入。只有完整观测的任务用于完整均值。历史部分 usage 单列为“已记录 token”，不当成任务总量；失败调用无法取得 usage 时标为不完整。不从字数推算，不把 reasoning 再加到已包含它的 completion 中。
- **RAG Hit@K、Recall@K、MRR@K**：使用冻结的“问题—参考论文”及相关 chunk ID 标注，比较本次实际选取的前 K 个切片；未读到预定参考论文仍计未命中。无标注或没有实际检索 ID 时为 N/A。非空检索结果率单列，不能冒充相关性命中率。
- **论文 Precision@K / Recall@K、事实支持率、引用覆盖率**：外置标注提供参考论文、逐论文相关性及报告事实判定；未标注/待评不能当作错误或正确。引用覆盖与事实支持分别计算，不以参考文献条目数代替。
- **阅读成功率、阶段耗时/失败情况、应用级重试比例、usage 记录覆盖率**：补充可客观复算的运行指标。当前开发历史覆盖多种版本/配置，不宣传为标准基准、SLA 或横向优劣结论。

## 新增脚本与入口

```text
evaluation/
  collect.py              # 只读日志/会话数据库/观测记录，生成规范化本地快照
  evaluate.py             # 离线计算指标；读取可选标注，输出汇总和 Markdown
  observer.py             # 可选独立观测层：计时、SDK usage、真实检索 ID，隔离保存
  observed_app.py         # 包装现有 app 的可选 Uvicorn 入口，复用全部原路由
  README.md               # 运行方法、口径、标注格式和限制
  labels.example.jsonl    # 仅格式占位，默认不参与任何统计
  tests/                  # 公式、去重、失败/缺失、只读和观测不改变返回值
  runs/                   # 本地原始快照，Git 忽略
  reports/                # 本地报告，Git 忽略
web/public/metrics/summary.json  # 脚本生成的脱敏汇总，Git 忽略
```

不新增 `/api/metrics` 或改动后端接口函数。默认采集命令不运行研究或调用模型。可选观测入口仅在用户选择它启动后端时生效，原请求、响应和 SDK 参数不改变；只为研究请求记录诊断，不写出提示词、文献正文或凭证。观测失败不改变业务返回。所有数据取自真实返回或显式外部标注，费用不按未配置价格猜测。

## 首页文件差异

- 新增指标类型与 `HomeMetrics.tsx`，读取静态汇总快照，显示数值、样本数、口径及 N/A 原因。
- `HomePage.tsx`：保留首屏结构与动效，在首屏下方添加指标面板；对话页保持原样。
- `homepage.css`：延续灰蓝画布、墨黑分割、奶白标记及等宽数据读数，小屏可读。
- `.gitignore`：排除本地观测/标注结果及生成快照；保留脚本、示例和说明。
- `web/README.md`、前端测试：说明生成/刷新方式，验证下滑可见、缺失数据与原交互。

## 验证

离线样例验证 nearest-rank、分母、SSE 错误、重复 usage、失败调用缺 usage、RAG 金标准与缺失项。假 SDK/假 ASGI 验证观测层不更改参数或响应，不调用真实模型。随后用当前真实日志和数据库生成快照，构建前端、运行相关及完整浏览器回归，检查桌面与小屏。仅提交用户已要求的前一轮成果，本轮指标功能保留待审阅。

参考定义：[Ragas Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)、[LangSmith 运行统计字段](https://reference.langchain.com/python/langsmith/schemas/ExperimentRunStats)。实现使用标准库计算，不接入云评测平台。

## 完成记录

已新增独立采集、离线计算、可选观测入口及一键发布脚本 `evaluation/update_metrics.py`，首页首屏下方增加指标区。指标类型位于 `web/src/types/evaluationMetrics.ts`；生成快照与原始明细均已 Git 忽略。旧 `docs/evaluation-implementation-plan.md` 保留原样。

当前真实快照覆盖 10 次研究启动：6 次完成、3 次失败、1 次未闭合。6 个成功计时样本的 P50 为 391.6619 秒，P95/P99 为 498.0826 秒，平均为 400.7892 秒。终态完成率为 6/9，单列 1 条未知记录，不以 HTTP 200 判断成功。

完整 usage 观测任务为 0，所以完整平均 LLM/embedding token 为 N/A；历史已记录的部分 LLM token 均值另列，不作为全任务总量。无匹配金标准或历史实际检索 ID，所以 RAG、论文筛选质量及逐事实支持指标为 N/A。可选观测入口已实际导入检查成功，但没有替换或重启用户后端，也没有执行额外研究或模型请求。

验证完成：

- BIGONE 环境中 14 项离线测试通过，覆盖公式、缺失、去重、金标准、只读、SDK 返回与异常保持、SSE 字节分帧，以及 Windows 文件锁发布。
- `npm run build` 通过；完整前端 34 项浏览器回归通过。
- `git diff --check` 通过，现有 `backend/` 与 `scripts/` 没有改动。
- 浏览器核对桌面和 390px 小屏，刷新成功、无横向溢出；截图为 `tmp/b1gone-homepage-metrics.png`。
- Windows 读者锁定公开文件重命名时，公开汇总可回写；前端验证 JSON，刷新失败保留上一份快照。观测明细保持原子写入。
- 前一轮前端成果提交为 `edcf645`；本轮指标功能暂未 commit，未 push。
