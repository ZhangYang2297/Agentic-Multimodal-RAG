# Agentic Multimodal RAG

> 基于 **LangGraph + Agentic RAG** 构建的多模态智能旅游助理，具备自主检索决策与多轮反思能力。

## 📌 项目概述

本项目实现了一个**多模态 Agentic RAG 系统**，能够接受文本和图片混合输入，自动解析复杂 PDF 文档（含表格、图片、多栏布局），通过 Agent 自主决定是否检索、检索几次，并对检索结果进行质量自评与自动改写重试。

### 核心能力

- **多格式文档解析**：PDF / Markdown / TXT 统一加载
- **OCR 引擎**：支持 qwen3.5-ocr（百炼 API）和 PaddleOCR-VL 双引擎切换
- **智能清洗**：通用文本清洗 + Markdown 专项清洗
- **语义切分**：（开发中）按标题分级的 MarkdownHeaderTextSplitter
- **向量检索**：（开发中）BGE Embedding + Chroma 向量库
- **Agent 编排**：（开发中）LangGraph 驱动的搜索/推理/反馈 Agent

### 系统架构（5 层）

```
┌──────────────────────────────────────────────┐
│  L1 用户交互层     文本 / 图片 输入           │
│  L2 多模态预处理层  清洗、特征提取、OCR/Caption│
│  L3 统一表征层     多模态嵌入 + 向量库        │
│  L4 智能决策层     搜索Agent / 推理Agent /
│                    反馈Agent (LangGraph)       │
│  L5 结果输出层     行程生成 / 推荐            │
└──────────────────────────────────────────────┘
```

## 📂 项目结构

```
Agentic-Multimodal-RAG/
├── PROJECT.md                      # 项目管理文档（记忆中枢）
├── 参考资料.txt                     # 技术调研与参考资源
├── all_models.txt                  # 可用模型清单
├── requirements.txt                # Python 依赖（待生成）
├── .gitignore
│
├── data/
│   └── raw/                        # 原始输入文件（PDF / TXT / 图片）
│       └── sample.pdf              #   测试用示例 PDF（15 页旅游文档）
│
├── outputs/                        # 生成结果目录
│   ├── logs/                       #   运行日志 / 测试报告
│   ├── ocr_results/                #   OCR 原始输出
│   └── parsed/                     #   解析后的 Markdown / 对比报告
│       └── pages/                  #     PDF 页面 PNG 切片
│
├── src/                            # 核心源代码
│   ├── __init__.py
│   │
│   ├── parsers/                    # 文档解析模块
│   │   ├── __init__.py             #   统一导出
│   │   ├── pdf_to_images.py        #   A2-Step1: PyMuPDF PDF→图片
│   │   ├── ocr_to_markdown.py      #   A2-Step2: qwen3.5-ocr 图片→Markdown
│   │   ├── unified_parser.py       #   A3: OCR 引擎统一接口（auto/qwen/paddle_vl）
│   │   ├── paddleocr_vl.py         #   PaddleOCR-VL-1.6 异步 PDF 解析
│   │   ├── pp_ocrv6.py             #   ❌ PP-OCRv6（已弃用，结构不兼容）
│   │   └── markdown_cleaner.py     #   A3: Markdown 噪音清洗（分页标记/页码）
│   │
│   ├── loaders/                    # 文档加载模块
│   │   ├── __init__.py
│   │   └── document_loader.py      #   B1: 多格式统一加载器（PDF/MD/TXT）
│   │
│   ├── cleaning/                   # 通用清洗模块
│   │   ├── __init__.py
│   │   └── universal_cleaner.py    #   B1: 通用文本清洗（BOM/零宽/控制字符）
│   │
│   ├── chunking/                   # 语义切分（B2，待开发）
│   ├── processing/                 # 批量处理流水线（B2-B3，待开发）
│   └── agent/                      # LangGraph Agent 编排（D 系列，待开发）
│
└── tests/                          # 测试与冒烟脚本
    ├── smoke_llm.py                #   LLM 连通性测试（qwen3.7-max）
    ├── smoke_llm_fast.py           #   LLM 连通性测试（qwen3.6-flash）
    ├── smoke_ocr.py                #   OCR 连通性测试（qwen3.5-ocr）
    ├── smoke_baidu_ocr.py          #   百度 PaddleOCR-VL 连通性测试
    ├── smoke_paddle_ocr.py         #   PaddleOCR 本地（已弃用）
    ├── test_iter_A2.py             #   A2 管线端到端测试（15 页 PDF）
    ├── test_iter_A3.py             #   A3 统一解析器测试
    ├── test_iter_A3_zerocost.py    #   A3 零消耗测试（本地缓存）
    ├── test_iter_B1.py             #   B1 多格式加载器测试（6 项验收）
    ├── test_universal_cleaner.py   #   B1 通用清洗测试（8 项+性能）
    ├── test_paddleocr_vl_vs_qwen.py#   OCR 引擎对比测试
    ├── test_pp_ocrv6_vs_qwen.py    #   ❌ PP-OCRv6 对比（已弃用）
    ├── ocr-example.txt             #   OCR 输出示例
    └── pp-ocrv6.txt                #   PP-OCRv6 输出示例
```

## 🛠️ 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| **Python** | 3.10 | PaddleOCR 兼容性最佳 |
| **PDF→图片** | PyMuPDF (fitz) | 本地轻量，dpi=200 |
| **OCR 引擎（主）** | qwen3.5-ocr（百炼 API） | 4.12s/页，中文高准确率 |
| **OCR 引擎（备）** | PaddleOCR-VL-1.6（百度） | 统一接口可切换 |
| **Embedding** | BGE-large-zh-v1.5 / 硅基流动 BGE-M3 | 中文效果好 |
| **向量库** | Chroma / FAISS | 起步轻量 |
| **LLM** | DeepSeek-V3 / Qwen2.5 | 高性价比 |
| **Agent 框架** | LangGraph | 支持循环 + 状态机 |

## 🚦 当前进展

### ✅ 已完成

| 迭代 | 模块 | 状态 | 说明 |
|------|------|------|------|
| **A1** | 基线流水线 | ✅ 通过 | PDF→图片→OCR→Markdown |
| **A2** | 端到端管线 | ✅ 通过 | 15 页 PDF，31.38s，322 行 Markdown |
| **A3** | 统一解析器 | ✅ 通过 | 双 OCR 引擎统一接口 + Markdown 清洗 |
| **B1** | 加载器 + 清洗 | ✅ 通过 | 多格式加载器 + 通用清洗（6+8 项验收） |

### 🚧 待完成

| 迭代 | 模块 | 优先级 | 说明 |
|------|------|--------|------|
| **B2** | 语义切分 | ⬆️ 高 | MarkdownHeaderTextSplitter，按标题分级 200-500 字/chunk |
| **B3** | 向量入库 | ⬆️ 高 | BGE Embedding + Chroma 向量库 |
| **B4** | 检索测试 | ⬆️ 高 | 5 个旅游问题命中率验证 |
| **C1/C2** | 多模态接口 | ➡️ 中 | 图片理解预留（等开通多模态模型） |
| **D1-D5** | Agent 编排 | ➡️ 中 | LangGraph 决策/评分/改写/生成节点 |
| **E1** | 端到端整合 | ➡️ 中 | 旅游助理 3 个验收用例 |

### 📊 进度总览

```
文档解析 ████████████████░░░░ 70%
文档加载 ████████████████░░░░ 70%
语义切分 ██░░░░░░░░░░░░░░░░░░ 10%
向量检索 ████░░░░░░░░░░░░░░░░ 20%
Agent编排 ░░░░░░░░░░░░░░░░░░░░  0%
端到端整合 ░░░░░░░░░░░░░░░░░░░░  0%
```

## 🔑 环境变量配置

本项目使用环境变量管理 API 密钥，**不提交任何密钥到代码仓库**。

### 必需环境变量

| 环境变量 | 用途 | 获取方式 |
|----------|------|---------|
| `DASHSCOPE_API_KEY` | qwen3.5-ocr / LLM 调用（阿里云百炼平台） | 1. 访问 [阿里云百炼平台](https://bailian.console.aliyun.com/) |
| | | 2. 登录后进入「模型广场」→「API-KEY 管理」 |
| | | 3. 创建 API Key 并复制 |
| `OCR-TOKEN` | PaddleOCR-VL-1.6 调用（百度 AI Studio） | 1. 访问 [AI Studio 模型库](https://aistudio.baidu.com) |
| | | 2. 搜索 PaddleOCR-VL 模型 |
| | | 3. 获取 Access Token |

### 设置方式

```bash
# Windows PowerShell
$env:DASHSCOPE_API_KEY="your-api-key-here"
$env:OCR-TOKEN="your-ocr-token-here"

# 或创建 .env 文件（不提交到 Git）
echo DASHSCOPE_API_KEY=your-api-key-here >> .env
echo OCR-TOKEN=your-ocr-token-here >> .env
```

## 🚀 快速开始

```bash
# 1. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量（见上表）

# 4. 解析 PDF 文档
python -m src.parsers.unified_parser data/raw/sample.pdf

# 5. 运行测试
python tests/test_iter_A2.py
python tests/test_iter_B1.py
```

## 🧪 测试指南

```bash
# 冒烟测试（连通性验证）
python tests/smoke_ocr.py              # OCR 连通性
python tests/smoke_llm.py              # LLM 连通性
python tests/smoke_baidu_ocr.py        # 百度 OCR 连通性

# 迭代验收测试
python tests/test_iter_A2.py           # A2 管线
python tests/test_iter_A3.py           # 统一解析器
python tests/test_iter_A3_zerocost.py  # 零消耗模式
python tests/test_iter_B1.py           # 多格式加载器
python tests/test_universal_cleaner.py # 通用清洗器
python tests/test_paddleocr_vl_vs_qwen.py # OCR 引擎对比
```

## 📄 许可

MIT
