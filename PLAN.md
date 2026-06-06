# 多 Agent 学术研究助手 — 实现计划

## 项目背景

在 `d:\BIGONE` 从零构建项目，展示多 Agent 开发能力，用于 Agent 开发实习求职。项目使用 7 个专业化 Agent，由 LangGraph 编排协作，具备**双向多模态**能力：**输入**（理解论文中的图表）和**输出**（通过 text-to-figure 生成科研图表）。RAG 系统基于 4 阶段混合检索。

## 技术选型

| 维度 | 选择 |
|------|------|
| Agent 框架 | **LangGraph**（状态机编排，条件边，并行扇出） |
| 部署形态 | **全栈 Web 应用**（FastAPI + Streamlit） |
| 数据源 | **全量学术 API 聚合**（arXiv + Semantic Scholar + PubMed + Crossref） |
| 大模型 | **Claude API**（主力），Haiku 用于轻量节点 |
| 向量数据库 | **ChromaDB**（进程内运行，快速开发；接口抽象可后续替换） |
| Embedding | `text-embedding-3-large`（主力），`all-MiniLM-L6-v2`（本地备选） |
| PDF 解析 | PyMuPDF (fitz) + pdfplumber |
| 视觉模型 | Claude Vision API |
| 科研绘图 | `matplotlib` + `seaborn` + `plotly` + `networkx` + Mermaid |
| 代码沙箱 | `subprocess` 配合超时、错误捕获、自动重试 |
| 前端 | Streamlit |

---

## Agent 架构

### 7 Agents + LangGraph 状态机

```
用户提问 → [Orchestrator: 拆解任务] → [Search Agent: 并行查4个API]
                                            ↓
                             [Orchestrator: 论文数量够了吗？]
                                 ↓ 够了              ↓ 不够（最多3轮）
                             [Read Agent: 精读论文]    [Search: 换关键词重搜]
                                 ↓
                             [Analyze Agent: 跨论文对比分析]
                                 ↓
                   ┌─────────────┴─────────────┐
                   ↓                           ↓
       [Synthesize Agent: 写综述]     [Visualization Agent: 生成图表]
                   │                           │
                   │ 文字 + [[FIG:xxx]] 占位符   │ 柱状图/趋势图/架构图
                   └─────────────┬─────────────┘
                                 ↓
                        [Figure Merger: 图表嵌入文字]
                                 ↓
                             [Critic Agent: 质量评审]
                                 ↓ 通过              ↓ 不通过
                             [输出结果]          [路由回对应节点修复]
```

**核心设计**：Synthesize 和 Visualization 从同一份 AnalysisReport **并行**启动。Synthesize 写文字时插入 `[[FIG:xxx]]` 占位符；Visualization 生成对应图表。最后 Figure Merger 将所有图表嵌入最终文档。

### Agent 职责

| Agent | 职责 | 输出 |
|-------|------|------|
| Orchestrator | 拆解研究问题，控制整体流程 | `research_plan: list[dict]` |
| Search Agent | 并行查询 4 个学术 API，去重排序 | `raw_papers: list[dict]` |
| Read Agent | 下载 PDF，检索相关段落，深度阅读 | `paper_insights: list[dict]` |
| Analyze Agent | 跨论文对比分析，找共识/矛盾/gap | `analysis_report: dict` |
| Synthesize Agent | 撰写结构化文献综述（含 `[[FIG:xxx]]` 占位符） | `draft_sections: list[dict]` |
| **Visualization Agent** | **根据分析数据生成科研图表（代码生成→沙箱执行）** | `figures: list[dict]` |
| Figure Merger | 匹配占位符与图表，嵌入最终文档 | `merged_sections: list[dict]` |
| Critic Agent | 质量评审（文字 + 图表），查漏补缺 | `critique: dict` |

---

## RAG 系统

### 入库流水线
```
论文ID → arXiv/S2/PubMed/Crossref API → 下载PDF → PyMuPDF解析
→ 按章节分块（512 token/块，128 token重叠）
→ text-embedding-3-large 向量化 → ChromaDB（含元数据：论文ID、章节、作者、引用数）
```

### 4 阶段混合检索
1. **语义搜索**：余弦相似度 → Top 100
2. **BM25 关键词**：`rank_bm25` 库 → Top 100
3. **RRF 融合**：Reciprocal Rank Fusion (k=60) → Top 20
4. **Cross-encoder 重排**：`ms-marco-MiniLM-L-6-v2` + 引用数加权 → 最终 Top 5-10

---

## 双向多模态

### 输入端：理解论文原有图表
```
PDF页面 → PyMuPDF检测图表/表格
→ 提取为PNG图片
→ Claude Vision API：「详细描述此图表，提取所有数据点」
→ 描述文本向量化存入ChromaDB（has_visual=true）
→ 前端结果页展示原图
```

### 输出端：自动生成科研图表（Visualization Agent）
```
AnalysisReport（结构化数据：对比表、指标、趋势、分类）
    ↓
[Claude 生成 matplotlib/seaborn/plotly 代码]
    ↓
[代码沙箱：subprocess.run("python generated_script.py")]
    ↓  超时30秒，语法错误自动重试
[输出：PNG + SVG + 图注]
    ↓
[存入 data/figures/{session_id}/]
```

#### 7 种自动生成的图表类型

| 触发条件 | 图表类型 | 工具 |
|----------|---------|------|
| 方法对比（≥2个方法有可比较指标） | 分组柱状图/雷达图 | matplotlib + seaborn |
| 时间序列数据 | 折线图（含置信区间） | plotly（可交互） |
| 论文年代分布（跨度≥3年） | 时间线/直方图 | matplotlib |
| 子领域分类（≥5篇论文） | 桑基图/树图 | graphviz |
| 系统架构/流程描述 | Mermaid 架构图 | mermaid-cli → PNG |
| 交叉对比矩阵 | 热力图 | seaborn |
| 引用网络（≥8篇论文） | 网络拓扑图 | networkx + matplotlib |

---

## 项目结构

```
bigone/
├── backend/
│   ├── main.py                    # FastAPI 入口，CORS，lifespan
│   ├── config.py                  # Pydantic Settings 配置
│   ├── api/
│   │   ├── routes_research.py     # POST /research, WS /ws/{session_id}
│   │   ├── routes_papers.py       # GET /papers/{id}
│   │   └── schemas.py             # Pydantic 请求/响应模型
│   ├── agents/
│   │   ├── graph.py               # StateGraph 定义（核心编排）
│   │   ├── state.py               # ResearchState TypedDict
│   │   ├── orchestrator.py        # 任务拆解 + 最终输出
│   │   ├── search.py              # 多源并行搜索
│   │   ├── read.py                # 深度阅读 + RAG 检索
│   │   ├── analyze.py             # 跨论文对比分析
│   │   ├── synthesize.py          # 综述撰写（含 [[FIG:xxx]] 占位符）
│   │   ├── visualization.py       # text-to-figure：代码生成→沙箱执行
│   │   ├── figure_merger.py       # 图表嵌入文字
│   │   ├── critic.py              # 质量评审
│   │   └── decisions.py           # 条件边决策函数
│   ├── rag/
│   │   ├── ingestion.py           # PDF → 分块 → 向量化
│   │   ├── vector_store.py        # VectorStoreAdapter + ChromaDBAdapter
│   │   ├── hybrid_search.py       # 语义 + BM25 + RRF + 重排
│   │   ├── chunking.py            # 按章节分块
│   │   └── embeddings.py          # embedding 模型封装
│   ├── sources/
│   │   ├── base.py                # AbstractSourceClient
│   │   ├── arxiv_client.py        # arXiv API
│   │   ├── semantic_scholar_client.py
│   │   ├── pubmed_client.py
│   │   └── crossref_client.py
│   ├── multimodal/
│   │   ├── visual_parser.py       # PDF 图表检测提取
│   │   ├── vision_analyzer.py     # Claude Vision API 封装
│   │   └── table_extractor.py     # pdfplumber 表格提取
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── chart_generator.py     # LLM 生成图表代码→执行
│   │   ├── sandbox.py             # 子进程沙箱：超时、错误捕获、重试
│   │   ├── mermaid_renderer.py    # Mermaid → PNG
│   │   ├── figure_merger.py       # [[FIG:xxx]] 匹配→嵌入
│   │   └── chart_templates.py     # 各图表类型的 Prompt 模板
│   ├── services/
│   │   ├── research_orchestrator.py
│   │   ├── paper_cache.py
│   │   └── export_service.py      # Markdown/PDF/BibTeX 导出
│   └── db/
│       ├── database.py
│       └── models.py
├── frontend/
│   ├── streamlit_app.py           # 首页（输入问题 + 配置）
│   ├── pages/                     # 01_进度页, 02_结果页, 03_历史页
│   ├── components/                # 进度流、论文表格、导出按钮
│   └── utils/                     # api_client, ws_client, state
├── data/
│   ├── chroma_db/                 # ChromaDB 持久化
│   ├── paper_cache/               # 下载的 PDF
│   ├── figures/                   # 生成的图表（按 session_id 分目录）
│   └── research.db                # SQLite 数据库
├── notebooks/                     # RAG & 多模态实验
├── scripts/                       # ingest_papers, rebuild_index, test_apis
├── requirements.txt
├── .env.example
└── README.md
```

---

## 开发阶段（8 周）

### Phase 1：基础搭建（第 1-2 周）
- **第 1 周**：项目脚手架、config.py、arXiv API 客户端、测试脚本
- **第 2 周**：LangGraph 骨架（State + 2 个 Node）、FastAPI 单端点、Streamlit 基础 UI
- **里程碑**：用户输入问题 → 调 API → 跑 LangGraph → 得到回复

### Phase 2：多数据源 + RAG（第 3-4 周）
- **第 3 周**：4 个 API 客户端全部实现、并行查询、去重、WebSocket 流式推送
- **第 4 周**：分块策略、向量化、ChromaDB、入库流水线、混合检索、Read Agent + RAG
- **里程碑**：Read Agent 能根据问题从已入库论文中检索相关段落并总结

### Phase 3：完整流水线 + 可视化 + 多模态（第 5-6 周）
- **第 5 周**：Analyze + Synthesize + Critic，端到端图含评审循环。**Visualization Agent v1**：从分析数据生成柱状图/折线图 + 沙箱执行
- **第 6 周**：多模态输入（图表检测、视觉分析、表格提取）。**Visualization Agent v2**：Mermaid 架构图、引用网络图、Figure Merger 嵌入
- **里程碑**：完整的文献综述报告，含自动生成的科研图表 + 提取的论文原图

### Phase 4：打磨与 Demo（第 7-8 周）
- **第 7 周**：Cross-encoder 重排、引用加权、错误处理（API 限流、超时、PDF 损坏）、导出服务
- **第 8 周**：前端完善（交互式 Plotly 图表、图表画廊、历史记录）、引用格式、导出按钮、README、Demo 准备
- **里程碑**：可演示的多 Agent 学术研究助手，双向多模态

---

## 验证方案

1. **单元测试**：每个 Agent 节点的 mock 输入输出测试、API 客户端 mock 测试、RAG 检索精度测试
2. **集成测试**：端到端 LangGraph 流水线，验证所有节点正确执行
3. **端到端 Demo 查询**（每道题应产出文字 + 图表）：
   - "2023年以来 Transformer 注意力机制的最新进展？" → 方法对比柱状图
   - "比较各种减少 LLM 幻觉的方法" → 分类树 + 对比热力图
   - "Survey LLM 多 Agent 协作方法" → 架构图 + 趋势线
4. **可视化专项测试**：每种图表类型生成无报错、沙箱超时正常、占位符匹配正确
5. **前端验证**：启动 Streamlit，实时进度流、最终报告含引文和图表
6. **边界测试**：API 超时、PDF 损坏、空搜索结果、沙箱代码语法错误→自动重试
