# B1GONE 前端交互原型

React + TypeScript + Vite + Tailwind CSS v4。此版本不连接 FastAPI，也不会调用模型；研究过程、报告与论文均为示例数据。

## 启动

在项目根目录运行：

```powershell
cd D:\BIGONE\web
npm install
npm run dev
```

打开 http://127.0.0.1:5173 。首次进入显示完成的示例研究，便于对照已确认的设计图。

## 体验方式

- 点击“新建研究”，输入问题后点击“提交”（Enter 提交，Shift + Enter 换行）。
- 研究节点逐行输出，默认约 12 秒完成；完成后“研究过程”折叠，点击可展开。
- 节点以不同道具的像素小角色区分 agent 职能：调度台、放大镜、筛选漏斗、书册、对照图表、打字机和审查印章。角标展示阶段状态，点击角色可查看职责、输入与产出。
- 点击“研究文献”开关右侧列表；摘要可展开，正文引用可定位到对应示例论文。
- 点击左侧“设置”右侧的按钮收起边栏，收起后点击左上方按钮恢复，当前研究与输入内容保留。
- 拖动文献栏左边界调整宽度（窄屏抽屉也支持），关闭后重新打开仍保留调整值；分隔线支持左右方向键（Shift 加速）和 Home / End，宽度会随窗口大小限制在可用范围内。
- “导出综述”下载包含示例文献的 Markdown 文件。
- “设置”可选择 5 / 10 / 15 篇论文、模拟速度与分析失败状态；失败后可重试，运行中可停止。
- 窄屏文献栏与手机侧栏使用抽屉；Esc 关闭，键盘焦点回到触发按钮。
- 历史研究在当前浏览器页面会话中保留，刷新后恢复预置示例。

## 检查

```powershell
npm run build
npm run test:e2e
```

端到端测试默认使用本机 Microsoft Edge。也可设置 `PLAYWRIGHT_CHANNEL=chrome` 使用已安装的 Chrome，或安装 Playwright Chromium 后设为 `chromium`。测试截图与结果位于项目根目录 `tmp`，不进入版本控制。

## 后续接入位置

- `src/services/mockResearch.ts`：本地事件流与状态更新，后续替换为真实研究流适配器。
- `src/data/demo.ts`：虚构论文、研究历史和阶段输出。
- `src/components/`：侧栏、研究过程、报告与文献栏组件。
- `src/styles.css`：灰蓝画布、炭黑侧栏、奶白按键与响应式布局。

正式接入需要将阅读结果、真实引用和错误追踪编号映射到对应视图。示例文献的“原文”仅打开说明窗口。

## 字体

常驻控件使用 [Fusion Pixel Font](https://github.com/TakWolf/fusion-pixel-font) 的 12px 简体中文比例字体（2026.09.25），字体采用 SIL OFL 1.1，文件与上游许可位于 `public/fonts/`；报告正文使用系统中文字体。品牌字与图标为代码绘制的 SVG。
