# Research Agent

Research Agent 是一个在个人电脑上运行的多来源学术研究工作台，由 FastAPI 后端和 Next.js 前端组成。默认使用 DeepSeek，主模型与轻量模型均为 `deepseek-v4-flash`。

## Windows 快速开始

首次使用前，请安装 Python 3.11+ 和 Node.js 20+，然后在项目目录中运行：

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix web install
```

双击根目录中的 `ResearchAgent-启动.bat`。浏览器会自动打开 [http://127.0.0.1:3000](http://127.0.0.1:3000)。首次进入时，页面会要求填写 DeepSeek 模型专用 API Key，并将其保存到本机项目根目录的 `.env` 文件中。

如需创建带项目图标的桌面快捷方式，右键 `安装桌面快捷方式.ps1`，选择“使用 PowerShell 运行”。

关闭启动脚本窗口，会停止由该脚本启动的前后端进程。若端口 8000 或 3000 已由已有的 Research Agent 进程占用，脚本会复用它们。

## 手动启动

```powershell
# 终端 1
& .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 终端 2
npm --prefix web run dev -- --hostname 127.0.0.1 --port 3000
```

后端接口文档位于 [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)。

## 配置

- `.env.example` 提供可选配置示例；真实 `.env` 已被 Git 忽略。
- `DEEPSEEK_API_KEY` 是规范的密钥变量，旧的 `ANTHROPIC_API_KEY` 仍兼容。
- 高级用户可通过环境变量覆盖默认模型。
- 本项目面向可信的单用户本机环境，不包含账号系统，也不会把 API Key 写入数据库或任务历史。

## 开发与验证

迁移、OpenAPI、测试、Demo Runner 和故障排查说明见 [docs/development.md](docs/development.md)。

## License

项目许可见 [LICENSE](LICENSE)，第三方素材许可见 [web/THIRD_PARTY_NOTICES.md](web/THIRD_PARTY_NOTICES.md) 和宠物素材目录内的 `LICENSE.md`。
