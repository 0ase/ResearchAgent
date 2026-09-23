# ResearchAgent

本地优先的学术研究工作区：Next.js 页面 + FastAPI 持久任务 + Supervisor 动态研究图。支持中英文、SSE 回放、论文/证据联动、历史任务、DeepSeek 设置、明暗主题、宠物和报告追问。

## 启动

在本仓库根目录执行（不要覆盖已有 .env）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix web ci
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_agent.ps1
```

浏览器打开 http://localhost:3000 。首次使用会要求配置 DeepSeek key；默认模型和轻量模型均为 deepseek-flash。DashScope 嵌入可选。请勿同时使用其他目录已启动的 3000/8000 服务。

启动脚本拒绝复用已占用的端口；与旧工作区并行运行时，先设置 `$env:RESEARCH_WEB_PORT = '3100'` 和 `$env:RESEARCH_API_PORT = '8100'`，浏览器改用 http://localhost:3100 。

手动启动：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# 另一终端
npm --prefix web run dev
```

可选旧客户端：`streamlit run frontend/streamlit_app.py`，与新页面使用同一后端和任务数据库。

## Windows 启动快捷方式

仓库根目录包含 `ResearchAgent-新版.lnk`，与 `ResearchAgent-启动.bat` 配套。快捷方式会记录生成时的目录；克隆到其他位置后，请先在新仓库根目录执行以下命令，使它指向当前目录：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/create_shortcut.ps1
```

随后双击 `ResearchAgent-新版.lnk` 启动。需要放到桌面时，可将重新生成的快捷方式复制过去；它的目标、工作目录和图标都取自当前仓库。

## 离线演示与验收

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start_dev.ps1
```

自动 Playwright 会启动独立 Demo 数据库，不使用真实模型或论文源。若原工作区仍运行，可使用隔离端口：

```powershell
$env:E2E_WEB_PORT = '3100'
$env:E2E_API_PORT = '8100'
$env:E2E_DEMO_DELAY_SECONDS = '1'
npm --prefix web run test:e2e
```

已有可用 Python 时，可设置 `$env:PYTHON_EXE = '完整的 python.exe 路径'`，供启动/OpenAPI 脚本使用，不必复制虚拟环境。

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\python.exe -m compileall -q backend
npm --prefix web run api:export
npm --prefix web run api:generate
npm --prefix web run api:check
npm --prefix web run test -- --run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run i18n:check
npm --prefix web run build
npm --prefix web run pet:build
npm --prefix web run pet:validate
```

## 使用约束

- 每实例一个活跃研究，论文 3–15 篇，默认 15。
- 运行中可排队一个追问并替换/取消；报告完成自动回答。研究失败、取消、中断清空队列。
- 已完成追问使用现有报告与证据，不发起新的研究。回答失败保留问题可重试；服务重启可能重新调用未完成的模型请求，不重复提交消息对。
- SQLite 保存任务、事件、论文、文本块、证据和消息；Chroma 只是可选二级索引。
- 启动自动顺序执行数据库迁移，包括旧 sessions/messages 导入。升级前自行备份实际数据库。
- 单机可信使用，无账号和多进程任务接管。Demo 不得用于 production。


### 运行可靠性

真实研究使用单进程启动，不使用 `--reload` 或多个 workers。相同数据库的第二实例将被拒绝；开发重载必须使用独立 Demo 数据库。启动器日志位于 `logs/launcher-<id>/`，同时监控前后端，后端退出时返回失败。关闭启动器会请求后端正常关闭，活跃任务记为 interrupted；不会自动重启真实研究。
