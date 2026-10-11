# B1GONE 前后端接入施工计划

状态：2026-10-10 先完成本文并明确边界，再按清单编码；本轮施工与验证已完成。此前扩大后端生命周期的构想已收窄，避免不必要的重构。

## 施工边界

本机单用户版本；保留已确认的视觉、角色、侧栏收起和文献栏调宽。分支 fix/backend-reliability，前端基线 14c9549，后端使用 BIGONE Conda 环境。

本轮保持以下文件及行为不变：backend/api/routes_research.py、backend/api/schemas.py、backend/config.py、backend/agents/**、backend/rag/**、backend/services/session_store.py、数据库结构、模型密钥选择、配置默认值。backend/main.py 仅导入和注册独立配置路由。施工不改写实际 .env，只有用户点击设置中的保存才写入；测试使用临时文件，不调用付费模型。

## 原样复用的接口

| 功能 | 现有接口函数 | 前端工作 |
| --- | --- | --- |
| 健康检查 | GET /health → health | 仅表示服务可响应，不代表外部服务就绪。 |
| 新研究 | POST /api/research/stream → start_research_stream | query ≤2000 字，max_papers 3–15；Fetch 读取 POST SSE。 |
| 历史列表 | GET /api/research/history → research_history | 真实会话列表；时间为原接口首次结果保存时间。 |
| 历史详情 | GET /api/research/{session_id} → research_detail | 真实报告、论文及已有调度记录；不补造缺失过程。 |
| 历史消息 | GET /api/research/{session_id}/messages → research_messages | 展示原报告之后的追问。 |
| 追问 | POST /api/research/{session_id}/chat → followup_chat | message ≤4000 字；失败重试复用 message_id。新研究通过“新建研究”发起。 |
| 导出 | 无新增接口 | 浏览器下载真实 final_answer Markdown。 |

SSE 是 data: JSON，类型来自 JSON 的 event 字段。支持中文跨网络块、CRLF、多行 data、心跳、流内 error、断流和取消；只有 done 表示成功。

agent 是调度通知，stage 是结果变化通知，均不代表精确节点生命周期。前端标注“调度记录”和“结果已返回”，按真实事件追加节点，保留重复阶段。任务等待时只表示仍在处理，不猜测哪个节点已开始。历史仅恢复 agent_trace 与现有结果摘要。

实际阅读 ID 来自非空 paper_insights.answer 的 source，关联 selected_papers/papers。正文 [Source ID]、[arxiv:ID] 等直接来源编号及 DOI 仅精确匹配已知阅读文献，歧义别名不关联；参考文献章节单独出现不算正文引用。不能匹配的来源引用及数字引用保留原文，并提示引用数量无法完整确认。此逻辑放前端，无需改后端生成规则。

停止采用 AbortController 断开当前流；提示“已停止接收；后端按现有流清理机制处理”，不声称已经取得服务器取消确认或保存了停止记录。

## 新增接口函数

仅新增配置接口，不新增研究路由。

| 方法/路径 | 路由函数 | 输入/输出 |
| --- | --- | --- |
| GET /api/settings | read_settings | 本机来源检查；返回白名单非秘密配置、密钥布尔状态、系统环境覆盖标记、待重启字段和只读目录，不返回密钥。 |
| PUT /api/settings | update_settings | {values, secrets, clear_secrets}；要求 X-B1GONE-Config: local；整体校验后原子保存根目录 .env，返回脱敏状态、修改字段与重启提示。 |

服务函数：get_settings_snapshot() 负责读取和脱敏；save_settings_update(update) 负责白名单合并、整体 Pydantic 校验及保存；require_local_settings_access(request) 检查连接地址、Host、Origin 和写入头；_read_env_document() / _render_env_update() 使用现有 python-dotenv 解析和保留未修改配置/注释，不执行文本。

允许编辑：模型地址/名称、模型与来源密钥、来源邮箱、候选数量/轮次、筛选阈值/批次/token、分析 token/重试、写作 token、阅读并发。目录、数据库与日志配置只读。OPENAI 优先、ANTHROPIC 备用、DashScope 独立的规则不变。

密钥输入默认空，空提交保留，清除需明确操作；不放 localStorage 或 VITE_*，不回显到响应、日志或错误。第一版保存后重启后端生效，不热改全局 settings。区分文件值、当前生效值与系统环境覆盖；系统环境覆盖不会因保存文件而消失。

已有启动脚本固定工作目录到项目根目录，本轮不改配置加载机制。若从其他目录启动，配置写入拒绝并提示使用该脚本，避免保存到错误文件。

## 文件结构差异

| 文件 | 类型及作用 |
| --- | --- |
| backend/main.py | 修改：仅注册 settings 路由。 |
| backend/api/routes_settings.py | 新增：GET/PUT 和本机来源保护。 |
| backend/api/settings_schemas.py | 新增：独立请求/响应契约。 |
| backend/services/settings_store.py | 新增：白名单、脱敏、整体验证、原子保存。 |
| backend/tests/test_settings_api.py | 新增：临时 env、来源限制、校验、脱敏测试。 |
| web/vite.config.ts | 修改：开发代理 /api 和 /health。 |
| web/package.json / package-lock.json | 修改：Markdown 渲染依赖。 |
| web/src/App.tsx / types.ts | 修改：真实连接、会话、事件、错误和追问。 |
| web/src/services/apiClient.ts | 新增：同源请求、SSE 分块解析、统一错误。 |
| web/src/services/researchAdapter.ts | 新增：后端结果转换为节点、文献与引用。 |
| web/src/components/SettingsDialog.tsx | 新增：真实配置表单、密钥操作、重启提示。 |
| web/src/components/Report.tsx / PaperPanel.tsx | 修改：真实 Markdown、引用定位、元数据和原文链接。 |
| web/src/components/Sidebar.tsx / ResearchTimeline.tsx | 修改：真实/演示提示与调度/结果通知语义。 |
| web/src/data/agentRoles.ts | 修改：后端阶段别名适配。 |
| web/src/styles.css | 修改：只补充设置、对话、Markdown 必要样式。 |
| web/tests/workspace.spec.ts | 修改：原视觉检查显式进入 ?demo=1。 |
| web/tests/integration.spec.ts | 新增：接口模拟、分块流、历史、追问、配置和错误。 |
| web/README.md | 修改：启动、接入、演示和设置说明。 |
| docs/frontend-backend-integration-plan.md | 本文及施工验收记录。 |

mockResearch.ts 与示例数据保留，仅 ?demo=1 启用；默认真实模式从空白提问页开始。原有 docs/evaluation-implementation-plan.md 不动。

## 顺序与验收

1. 先完成本文，再写代码。新增配置模块和临时文件测试，核对既有研究路由与默认配置无差异。
2. 接入同源 API、SSE 解析与适配，再接报告/论文、历史、追问与设置。
3. 运行后端原测试及新增测试、前端构建和浏览器检查，核对 Git diff 与实际页面。

检查：跨块中文、流内错误/断流、重复阶段、阅读和引用区分、原文链接、历史缺失过程、追问稳定 ID 重试、秘密不回显/不存本地、无效配置回滚、系统环境覆盖、非本机访问拒绝。联调不调用真实模型。

## 本轮不实施

精确节点生命周期、关键事件服务器持久化、独立取消确认、失败/停止任务持久化、刷新恢复运行任务、配置热更新、多人权限、生产静态托管。这些需触碰现有后端内部，另列必要性和计划后实施。

## 施工验收记录

已按清单实现：同源 API/SSE、真实历史与追问、Markdown 报告、实际阅读/引用关联、原文链接、独立配置接口及设置表单。默认真实模式，原型可通过 ?demo=1 使用。

后端实际差异为四个新增文件（路由、契约、服务、测试）和 main.py 的两行路由注册。已通过 Git diff 确认研究路由、原 schemas、config、agents、rag、session_store 无修改；数据库未迁移，实际 .env 未由施工或测试改写。

验证结果：

- BIGONE 环境后端测试：127 项通过，其中新增配置测试 19 项；使用临时 env 和测试目录。
- 前端构建：TypeScript 与 Vite 通过。
- Edge 浏览器测试：13 项通过，含原视觉/侧栏交互与新增接口联调、分块中文流、断流、错误追踪、稳定消息 ID、旧来源编号/DOI、停止与配置脱敏。
- 实际本机连接：健康检查、真实历史报告、文献列表及当前配置读取成功；旧报告的 11 篇有效阅读文献与正文来源编号关联成功。
- Git diff --check 通过；前端依赖审计为 0 漏洞（同时更新 source-map-js 的兼容补丁版）。

没有提交新的付费研究任务或保存实际配置。2026-10-11 收尾：确认联调服务已退出，5173/3000 端口无监听；用户授权提交本轮改动，本轮不推送远端。独立取消确认、失败任务持久化与精确生命周期仍按上节留待后续。
