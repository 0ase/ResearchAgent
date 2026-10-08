# 后端异常处理与追踪

后端的公共基础设施位于 `backend/core/`：`errors.py` 管理业务异常、错误分类和 HTTP/SSE 错误契约；`middleware.py` 建立请求上下文；`observability.py` 管理结构化日志与工作流阶段追踪；`streaming.py` 确保断线时关闭流生成器。`backend/main.py` 提供 `create_app()` 工厂和应用生命周期。

## 客户端错误契约

所有 HTTP 响应包含 `X-Request-ID`。调用方可以发送由字母、数字、点、下划线或连字符组成、长度为 1–128 的 `X-Request-ID`；缺失或非法时服务端生成编号。需要重试时，可复用请求编号，用每次错误独立的 `error_id` 区分失败。

HTTP 错误示例：

```json
{
  "error": {
    "code": "SESSION_SAVE_FAILED",
    "message": "研究结果保存失败，请稍后重试。",
    "status_code": 503,
    "request_id": "request-example",
    "error_id": "error-example"
  },
  "detail": "研究结果保存失败，请稍后重试。"
}
```

`detail` 保留现有客户端使用的入口。校验失败时，它与 `error.details` 均为包含 `loc`、`type`、`msg` 的列表，不返回原始输入和 Pydantic 的异常上下文。

SSE 已开始后无法改变 HTTP 状态码，因此连接仍是 HTTP 200，错误通过 `event: "error"` 的 JSON 数据发送，包含同样的 `code`、`message`、`status_code`、`request_id`、`error_id`。沿用已有 `data: {...}` 帧格式，客户端按 JSON 的 `event` 字段分派。所有进度、心跳和完成事件也包含 `request_id`。收到 `error` 应终止当前操作；只有结果成功写入数据库后才会发送 `done`。

| 错误码 | 状态码 | 含义 |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | 请求参数不合法 |
| `NOT_FOUND` | 404 | 路由或研究会话不存在 |
| `CONFLICT` | 409 | 消息编号冲突 |
| `METHOD_NOT_ALLOWED` | 405 | HTTP 方法不支持 |
| `HTTP_ERROR` | 原状态码 | 其他显式 HTTP 异常，保留 Retry-After、Allow 等响应头 |
| `NO_PAPERS_FOUND` | 422 | 工作流结束后没有可用论文 |
| `SEARCH_TARGET_NOT_MET` | 422 | 去重候选论文不足 80 篇 |
| `NO_RELEVANT_PAPERS` | 422 | 候选论文均未通过筛选相关性门槛 |
| `SCREENING_FAILED` | 502 | 模型未返回有效的多维评分 |
| `ANALYSIS_INPUT_EMPTY` | 502 | 没有非空逐篇摘要可以交给分析模型 |
| `ANALYSIS_EMPTY_RESPONSE` | 502 | 模型最终答案缺失、为空或只有空白 |
| `ANALYSIS_TRUNCATED` | 502 | 长度截断后仍无法获得完整、通过校验的分析结果 |
| `ANALYSIS_INVALID_JSON` | 502 | 非空最终答案无法解析为 JSON |
| `ANALYSIS_INVALID_SCHEMA` | 502 | 分析字段缺失，或列表/字典类型不正确 |
| `ANALYSIS_INVALID_RESPONSE` | 502 | 没有 choice/message、内容类型错误或意外工具调用 |
| `ANALYSIS_RESPONSE_REJECTED` | 502 | 接口报告内容过滤或拒绝回答 |
| `UPSTREAM_TIMEOUT` | 504 | 未恢复的 HTTP/模型 SDK 超时 |
| `UPSTREAM_UNAVAILABLE` | 502 | 未恢复的 HTTP/模型 SDK 连接或状态异常 |
| `STORAGE_UNAVAILABLE` | 503 | SQLite 读写失败 |
| `MODEL_CREDENTIALS_MISSING` | 503 | OPENAI_API_KEY 和 ANTHROPIC_API_KEY 都未配置 |
| `VECTOR_STORE_UNAVAILABLE` | 503 | 向量库子进程崩溃或操作超时 |
| `VECTOR_OPERATION_FAILED` | 503 | 向量库操作抛出 Python 异常，日志保留子进程堆栈 |
| `SESSION_SAVE_FAILED` | 503 | 研究结果持久化失败 |
| `STORED_DATA_INVALID` | 500 | 历史数据 JSON 损坏 |
| `WORKFLOW_EMPTY` | 500 | 流式工作流未产生状态 |
| `INTERNAL_ERROR` | 500 | 其他未处理异常，包括响应模型验证失败 |

外部检索源、论文下载、嵌入和摘要支持原有重试或部分失败降级。此时研究可以继续，但失败原因和尝试次数会记录在服务端日志；工作流已有 `errors` 会作为 `warnings` 写入研究结果和 SSE 完成数据。研究结果中保存最初的 `request_id`，方便从历史会话回查日志。

## 定位错误

默认写入控制台和项目根目录的 `logs/backend.log`，每行一个 JSON 对象。日志包含 UTC 时间、级别、进程编号和事件名称；请求内日志还包含 `request_id`、方法和路径。研究阶段增加 `session_id`、`stage`，追问增加 `message_id`。异常记录包含 `error_id`、异常类型、堆栈和 `raise ... from ...` 原因链；同一个异常经过阶段和 HTTP/SSE 边界时复用编号。

先用客户端的 `error_id` 找到异常记录，再用 `request_id` 查看前后阶段、外部来源和耗时：

```powershell
rg -F "客户端返回的error_id" logs -g "backend.log*"
rg -F "客户端返回的request_id" logs -g "backend.log*"
```

常见事件包括 `request.started/completed`、`stage.started/completed/failed/degraded/cancelled`、`source.failed/timeout`、`embedding.attempt.failed`、`read.summary.failed`、`llm.parse.fallback`、`llm.validation.fallback`。请求耗时覆盖整个 SSE 连接。SSE 中的业务错误以错误事件及异常日志为准，访问日志的 HTTP 状态仍然是 200。响应已经发出后的后台任务错误保留日志，客户端无法收到替换响应。

不会主动记录请求体、授权头或模型完整输出。JSON 日志格式化器会遮盖配置中的 API 密钥、Bearer 值、URL 查询参数及常见 `token=...` 等模式。新增日志应优先记录来源、论文编号、批次、计数和耗时，避免把用户正文或凭据拼接到日志。服务器自身或其他工具配置的独立日志处理器不受本项目 JSON 格式化器控制。

## 分析节点返回空正文的追溯

`analysis` 首次生成预算默认 6000 token。DeepSeek 接口明确使用低强度思考和 JSON 输出；
截断、空正文或 JSON/结构错误会进行一次恢复请求，预算默认 8000 token，关闭 DeepSeek
思考模式以优先生成最终 JSON。其他兼容接口不发送 DeepSeek 专属参数。以下事件共享
`request_id`、`session_id`、`stage=analysis`、节点级 `analysis_run_id`；每次请求有独立的
`analysis_call_id` 和 `attempt`，原始 SDK 连接重试与输出恢复次数分别记录：

- `analysis.request.started`：实际模型、接口主机、生成上限、超时、SDK 重试数，以及输入摘要
  总数/非空数/空摘要数、逐篇来源编号和长度。输入字符数不等同于输入 token 数。
- `analysis.input.empty_summaries`：部分摘要为空的论文编号。空摘要不送入模型，保留其他
  论文的原始编号和来源。全部为空时使用
  `analysis.input.failed`，不向模型发送无有效证据的请求。
- `analysis.response.received`：模型响应 `response_id`、SDK 提供的 HTTP 请求编号
  `provider_request_id`、实际响应模型、`finish_reason`、正文与推理内容长度、过滤/拒绝标志，
  以及 `prompt_tokens`、`completion_tokens`、`total_tokens`、`reasoning_tokens`。
  接口未提供的用量保持 null，不推断为零。
- `analysis.request.failed`：SDK 连接、状态码或超时异常，保留原有错误分类及异常链。
- `analysis.output.retrying`：可恢复的输出失败及其错误编号；后续尝试仍使用相同有效证据，
  不重跑检索或阅读，也不把部分 JSON 或推理正文作为新证据。
- `analysis.output.failed`：恢复次数耗尽后的失败类别和统一 `error_id`。JSON 语法错误保留报错位置，
  结构校验只记录字段位置与错误类型，不记录原始答案或校验输入值。
- `analysis.completed`：通过校验后的四类结果计数和 `empty_analysis`。结构完整且模型明确
  返回空列表的结果可以成功完成；空字符串、截断和解析失败不再被伪装为四个空列表。
  `attempts` 保存各次参数和结果元数据，`recovered` 表示成功前发生过恢复请求。

`content_state` 区分 missing、empty、whitespace、text、unexpected_type。只存在推理内容而
没有最终答案时记录 `failure_kind=reasoning_without_final_answer`；这说明响应形态，不能单凭
推理字符数判断消耗了多少 token。`finish_reason=length` 表明长度限制停止；进一步结合
`completion_tokens`、`reasoning_tokens` 和请求上限判断生成预算是否被推理占用。
结束原因和用量字段依据 [DeepSeek Chat Completions 文档](https://api-docs.deepseek.com/api/create-chat-completion/)。

生成结果虽标记 `length`，但 JSON 已完整且四类字段通过校验时，可以保留真实结果，并记录
`analysis.output.complete_at_limit`。不完整结果才重试；空结果不会凭空获得结论。
内容过滤/拒绝回答不切换模式重试，SDK 认证、连接和超时仍沿用原有异常契约。

恢复后仍失败才终止本次研究，HTTP/SSE 返回可读错误及追踪编号，不发送分析完成和 done 事件。
SSE 已发送响应头后 HTTP 状态仍为 200，错误事件中的业务状态为 502。有效结果的诊断元数据
保存在 `analysis_diagnostics`，随 API 结果和历史会话保存；新检索会清除旧分析诊断。
日志不保存完整论文摘要、最终答案、推理正文或完整响应头。

可只重放历史会话的分析步骤：

```powershell
conda activate BIGONE
python scripts/diagnose_analysis.py --session-id 已保存的session_id
```

省略 `--session-id` 使用最新会话。脚本只读 SQLite 历史结果、复用原摘要及分析目标，调用
当前配置的分析节点（默认最多两次模型请求，SDK 连接重试保持原设置），不会重新检索、下载或覆盖历史会话。
结果写入普通分析日志，增加 `diagnostic=true` 和新的请求编号；控制台只输出状态、计数和
追踪编号。失败以退出码 1 返回。用新 `request_id` 查询本次完整轨迹：

```powershell
rg -F "本次诊断的request_id" logs -g "backend.log*"
```

旧任务没有记录的 `finish_reason` 和 token 用量无法从空列表结果中还原；重放得到的是新响应，
不能冒充当时接口的原始返回。

分析配置：

```text
ANALYSIS_MAX_TOKENS=6000
ANALYSIS_RETRY_MAX_TOKENS=8000
ANALYSIS_MAX_ATTEMPTS=2
ANALYSIS_THINKING_EFFORT=low
```

恢复预算不能小于首次预算，输出恢复次数允许 1–3 次；默认两次总尝试，防止无界循环。
首次 DeepSeek 思考强度允许 none/low/high/max，恢复请求固定 none。
配置变更后重启后端。筛选的每批 5 篇、6000 token 是另一套独立参数。

## 配置与保留

应用启动时自动配置日志，无需额外服务或数据库迁移。可以通过进程环境变量覆盖以下设置：

| 环境变量 | 默认值 |
| --- | --- |
| `LOG_LEVEL` | `INFO`，支持 DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `LOG_DIR` | `logs`，相对路径相对于项目根目录 |
| `LOG_MAX_BYTES` | `10485760`，单个日志文件约 10 MiB |
| `LOG_BACKUP_COUNT` | `5`，最多保留五份轮转备份 |

轮转日志适用于当前单进程启动方式。多个 worker 应分别设置日志路径或将控制台日志交给统一采集器，避免多个进程同时轮转同一文件。追溯范围取决于日志保留期，备份超过上限会被轮换删除。

Chroma 的原生操作在独立子进程中执行，主进程记录失败操作、子进程编号及退出码。
`VECTOR_STORE_TIMEOUT_SECONDS` 默认 60 秒；崩溃或超时后关闭该子进程，并快速返回
`VECTOR_STORE_UNAVAILABLE`，避免反复拉起崩溃进程。重启后端后会建立新的子进程。
阻塞的索引、PDF 解析和向量查询在线程中等待，SSE 心跳与健康检查可以继续响应。

Windows 上请用 `scripts/start_backend.ps1` 从 `BIGONE` 环境启动后端。已复现的
`base` 环境故障发生在 Chroma 原生读取：旧 `MSVCP140.dll` 中的访问冲突会直接结束
Python 进程，常规 `except Exception` 无法捕获。子进程隔离将这类故障转换为可追踪的
服务错误。已有向量数据库不需要删除或重建。

## 后续开发约定

- 可预期业务失败使用 `AppError("STABLE_ERROR_CODE", "对用户可读的说明", status_code)`；包装底层异常使用 `raise ... from exc`。
- 新增工作流节点通过 `trace_stage("stage_name", function)` 注册，保持函数签名和 LangGraph 的 `Command` 返回值。
- 捕获异常并继续运行时调用 `report_exception(exc, "component.operation.failed", level=logging.WARNING, ...)`，保留原始异常对象，不仅记录 `str(exc)`。
- 流式端点使用 `ManagedStreamingResponse` 和显式生成器清理；取消继续传播，避免误报为内部错误。
- 公共错误消息保持稳定，不把路径、SDK 原始响应或异常堆栈发送给客户端。

中间件采用纯 ASGI 实现，以维持流式响应期间的上下文传递，参考 [Starlette 中间件文档](https://www.starlette.io/middleware/)。

## 验证

```powershell
conda activate BIGONE
python -m pytest backend/tests -q
```

`test_error_handling.py` 覆盖统一契约、错误编号与异常链、请求并发隔离、HTTP 响应头、依赖分类、SSE 异常/断线、保存失败、日志脱敏/轮转、应用生命周期、历史数据损坏，以及实际编译的 LangGraph 动态路由。测试替换外部服务，不消耗模型 API 配额。

`test_analysis_tracing.py` 覆盖空/缺失/空白正文、推理占用预算的长度截断、合法空分析、
JSON/字段类型错误、空输入、超时、取消、日志正文保护、诊断结果保存和 SSE 错误编号关联。
`test_analysis_recovery.py` 覆盖截断/空输出/结构错误恢复、有界重试、完整 JSON 在长度限制
处保留、空摘要跳过、其他接口兼容性和恢复预算验证。
