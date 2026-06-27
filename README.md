# Agentic Multimodal RAG

> 基于 **LangGraph + Agentic RAG** 构建的多模态智能旅游助理，具备自主检索决策、检索质量自评与多轮改写重试能力。

## 项目概述

本项目实现了一个**多模态 Agentic RAG 系统**，面向"国内旅游攻略"知识库场景：自动解析复杂 PDF（含表格、图片、多栏布局），构建可持久化的混合检索引擎，并由 LangGraph Agent 自主决定是否检索、检索结果是否足够、需不需要改写问题重试或拒答。

与传统"一次检索 + 直接生成"的 RAG 不同，本系统的核心是 **Agent 闭环**：

```
检索 → LLM 自评 → 不足则改写重试 → 仍不足则拒答兜底 → 足够则生成答案
```

### 核心能力

- **多格式文档解析**：PDF / Markdown / TXT 统一加载
- **OCR 引擎**：qwen-ocr（阿里云百炼 API）为主、PaddleOCR-VL 备用，统一接口可切换
- **智能清洗 + 语义切分**：通用文本清洗 + Markdown 专项清洗，按标题层级 / 递归段落切分
- **混合检索**：BGE-M3 稠密向量（ChromaDB）+ BM25（SQLite FTS5）+ RRF 融合 + BGE-reranker 重排序
- **全链路持久化**：向量库、BM25 索引、文档注册中心均落盘，进程重启不丢失，支持增量更新与版本 deprecate
- **Agentic 编排**：LangGraph 状态机驱动 Search / Evaluate / Rewrite / Answer / Fallback 五节点闭环
- **并发安全**：DocumentRegistry、ChromaStore、PersistentBM25 均加线程锁保护写操作

### 系统架构（5 层）

```
┌────────────────────────────────────────────────────┐
│  L1 用户交互层      文本 / 图片 输入                  │
│  L2 多模态预处理层   PDF→图片→OCR→清洗→语义切分        │
│  L3 统一表征层       BGE-M3 嵌入 + ChromaDB 向量库     │
│  L4 智能决策层       Search/Evaluate/Rewrite/         │
│                     Answer/Fallback (LangGraph)       │
│  L5 结果输出层       答案生成 / 拒答兜底               │
└────────────────────────────────────────────────────┘
```

### 检索架构（最终版）

```
用户问题
   │
   ├── BGE-M3 (SiliconFlow)  →  稠密向量 TOP 20  → 过滤 score < 0.5
   ├── SQLite FTS5 BM25       →  关键词检索 TOP 20 → 过滤 score < 0.5
   │
   └── RRF 融合 → TOP 10
        │
        └── BGE-reranker-v2-m3 → TOP 5 → 过滤 score < 0.9 → 最终结果
```

## 项目结构

```
Agentic-Multimodal-RAG/
├── README.md
├── requirements.txt
├── .gitignore
│
├── outputs/                          # 持久化数据（默认 gitignore）
│   ├── registry/documents.json       #   文档注册中心
│   ├── chroma-travel/                #   ChromaDB 向量库
│   ├── bm25/bm25_index.db            #   BM25 关键词索引（SQLite FTS5）
│   └── parsed/                       #   OCR 解析结果
│
├── src/
│   ├── parsers/                      # 文档解析
│   │   ├── pdf_to_images.py          #   PDF → PNG
│   │   ├── ocr_to_markdown.py        #   qwen-ocr
│   │   ├── paddleocr_vl.py           #   PaddleOCR-VL 备用
│   │   ├── unified_parser.py         #   统一接口
│   │   └── markdown_cleaner.py       #   清洗
│   │
│   ├── loaders/document_loader.py    # 多格式加载器
│   ├── cleaning/universal_cleaner.py # 通用文本清洗
│   ├── chunking/splitter.py          # 语义分块
│   │
│   ├── processing/
│   │   ├── document_registry.py      #   文档注册中心（线程安全 + MD5 + 版本管理）
│   │   └── pipeline.py               #   入库编排器
│   │
│   ├── embedding/embedder.py         # BGE-M3 embedding
│   ├── vectorstore/chroma_store.py   # ChromaDB 封装（线程安全）
│   │
│   ├── retrieval/                    # 检索层
│   │   ├── engine.py                 #   RetrievalEngine 统一入口
│   │   ├── config.py                 #   阈值配置
│   │   ├── dense_retriever.py        #   稠密检索
│   │   ├── persistent_bm25.py        #   SQLite FTS5 BM25（线程安全）
│   │   ├── hybrid_retriever.py       #   RRF 融合 + 重排序
│   │   └── reranker.py               #   BGE-reranker
│   │
│   └── agent/                        # LangGraph Agent
│       ├── graph.py                  #   状态机构建
│       ├── state.py                  #   AgentState 定义
│       ├── tools.py                  #   5 个节点 + 路由
│       └── llm.py                    #   多后端 LLM 服务（快/默认/强模型）
│
└── tests/                            # 各迭代测试脚本
    ├── test_engine_smoke.py          #   检索引擎端到端冒烟
    ├── test_bm25_deprecate.py        #   BM25 分词 + deprecate
    └── test_agent_*.py               #   Agent 单测 / mock / e2e
```

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| **Python** | 3.10 | PaddleOCR 兼容 |
| **PDF→图片** | PyMuPDF (fitz) | 本地轻量 |
| **OCR（主）** | qwen-ocr（阿里云百炼 API） | 直接输出 Markdown |
| **OCR（备）** | PaddleOCR-VL（百度） | 统一接口可切换 |
| **Embedding** | BGE-M3（SiliconFlow API） | 中文最优，1024 维 |
| **向量库** | ChromaDB | 轻量持久化，metadata 过滤 |
| **关键词检索** | SQLite FTS5 BM25 | **持久化**、零依赖、增量更新 |
| **融合算法** | RRF（Reciprocal Rank Fusion） | 不依赖分数归一化 |
| **重排序** | BGE-reranker-v2-m3（SiliconFlow API） | 精度提升关键，阈值 0.9 |
| **Agent 框架** | LangGraph | 支持循环 + 状态机 |
| **LLM** | qwen / deepseek（DashScope，可配置） | 快/默认/强三档分工 |

## 当前进展

### 已完成

| 模块 | 状态 |
|------|------|
| PDF 解析管线（PDF→图片→OCR→Markdown） | ✅ |
| 多格式加载器 + 通用清洗 + 语义分块 | ✅ |
| 文档注册中心（MD5 检测 + 版本管理 + 线程锁） | ✅ |
| ChromaDB 向量库封装（状态过滤 + 版本 deprecate + 线程锁） | ✅ |
| PersistentBM25（SQLite FTS5 + 单字分词 + deprecate + 线程锁） | ✅ |
| RRF 融合 + BGE-reranker 重排序 | ✅ |
| RetrievalEngine 统一入口（全链路持久化） | ✅ |
| 阈值调优（dense/bm25 0.5、rerank 0.9） | ✅ 测试验证 |
| LangGraph Agent（Search/Evaluate/Rewrite/Answer/Fallback） | ✅ |
| 检索引擎端到端冒烟测试 | ✅ 通过 |

### 待完善

| 模块 | 优先级 |
|------|--------|
| 多模态输入（图片 + 文本混合查询） | 高 |
| 端到端 Agent 真实 API 回归 | 中 |
| 批量入库整库攻略 PDF | 中 |

## 环境变量配置

本项目使用环境变量管理 API 密钥，**不提交任何密钥到代码仓库**。

| 环境变量 | 用途 | 获取方式 |
|----------|------|---------|
| `SILICONFLOW_API_KEY` | BGE-M3 Embedding + BGE-reranker-v2-m3 | [SiliconFlow 控制台](https://cloud.siliconflow.cn) |
| `DASHSCOPE_API_KEY` | qwen-ocr + Agent LLM（阿里云百炼） | [百炼平台](https://bailian.console.aliyun.com/) |
| `OCR-TOKEN` | PaddleOCR-VL（百度，可选） | [AI Studio](https://aistudio.baidu.com) |

可选覆盖 Agent 模型（默认见下）：`AGENT_FAST_MODEL`、`AGENT_MODEL`、`AGENT_STRONG_MODEL`。

### 设置方式

```powershell
# Windows PowerShell（注意 User 级变量需显式传递给当前进程）
$env:SILICONFLOW_API_KEY = [Environment]::GetEnvironmentVariable('SILICONFLOW_API_KEY','User')
$env:DASHSCOPE_API_KEY   = [Environment]::GetEnvironmentVariable('DASHSCOPE_API_KEY','User')
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量（见上）

# 3. 一键入库 + 检索
python -c "
from src.retrieval.engine import RetrievalEngine
engine = RetrievalEngine()
engine.ingest('outputs/parsed/document.md')
for r in engine.search('成都有什么美食推荐'):
    print(f\"#{r['rank']} rerank={r.get('rerank_score',0):.4f} {r['document'][:60]}\")
"
```

### 跑测试

```powershell
$env:PYTHONIOENCODING='utf-8'              # 避免 GBK 控制台 emoji 报错
python tests/test_engine_smoke.py          # 检索引擎端到端冒烟
python tests/test_bm25_deprecate.py        # BM25 分词 + deprecate
```

## 工程亮点

开发过程中沉淀了一份完整的工程踩坑记录（本地维护），涵盖以下有代表性的真实问题与权衡：

- **OCR 引擎选型**：PP-OCRv6 / PaddleOCR-VL / qwen-ocr 三选一，最终选直接输出 Markdown 的 qwen-ocr。
- **余弦距离 vs 余弦相似度**：命名混淆导致阈值判断方向反了，负相似度文档被误召回。
- **BM25 持久化**：从纯内存（重启即丢）迁移到 SQLite FTS5，支持增量更新与版本 deprecate。
- **BM25 列权重打分恒为 0**：误读 FTS5 `bm25()` 的列权重语义，把唯一索引列权重设成 0，端到端冒烟才暴露。
- **检索组件线程安全**：最小必要加锁——只锁有竞争的写路径，不锁无状态转发层和读路径。
- **检索阈值设计**：dense/bm25 0.5、rerank 0.9 两层过滤，逐步从 0.3 收紧到 0.9 并经测试验证。
- **环境适配**：ChromaDB Windows 文件锁、PowerShell GBK 编码、用户级环境变量作用域。
- **Agent 鲁棒性**：三层兜底（节点 try/except + 流程重试上限 + 拒答 fallback）+ 后端熔断器，保证流程必收敛、不抛异常给用户。
- **模型路由解决超时**：评估/改写等高频轻量节点用 flash 小模型、关闭深度思考，回答/兜底才用强模型，端到端延迟从 1 分多压到十几秒。

## 许可

MIT
