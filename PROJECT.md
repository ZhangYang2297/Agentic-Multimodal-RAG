# 多模态 Agentic RAG 项目管理文档

> **项目代号**：Agentic-Multimodal-RAG
> **创建日期**：2026-06-25
> **目标周期**：2 天跑通 Demo
> **文档用途**：项目记忆中枢——记录目标、技术选型、进度、决策、问题，新对话打开此文档即可快速续接。

---

## 1. 项目概述

### 1.1 一句话定义
基于 **LangGraph + Agentic RAG** 构建的**多模态智能旅游助理**，具备自主反馈与多轮反思能力。

### 1.2 系统架构（4 层）
```
┌──────────────────────────────────────────────┐
│  L1 用户交互层     文本 / 图片 输入            │
│  L2 多模态预处理层  清洗、特征提取、OCR/Caption │
│  L3 统一表征层     多模态编辑器 + 向量库        │
│  L4 智能决策层     搜索Agent / 推理Agent / 反馈Agent (LangGraph) │
│  L5 结果输出层     行程生成 / 推荐             │
└──────────────────────────────────────────────┘
```

### 1.3 核心能力
- 图片 + 文本混合输入
- 复杂 PDF（表格/图片/多栏）智能解析
- 自主决定「要不要检索 / 检索几次」
- 检索质量自评 + 失败自动改写重试
- 2 天内可演示的完整 Demo

---

## 2. 关键技术决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 多模态路线 | 路线 A：图片转文本 → 文本 RAG | 实现简单，先跑通再演进 |
| PDF 解析 | **PyMuPDF + qwen3.5-ocr** | 见 §2.2 架构图 |
| Embedding | BGE-large-zh-v1.5（本地）/ 硅基流动 BGE-M3 | 中文效果强 |
| 向量库 | FAISS（CPU） | 起步轻量 |
| LLM | DeepSeek-V3 / Qwen2.5 | 高性价比 |
| 图片理解 | Qwen2-VL（硅基流动）/ GPT-4o-mini | API 调用免部署 |
| Agent 框架 | LangGraph | 支持循环 + 状态机 |
| Python 版本 | 3.10 | PaddleOCR 兼容性最佳 |

### 2.1 多模态核心认知

### 2.2 文档解析架构（最终方案 2026-06-25 调整）

```nPDF
  PyMuPDF (dpi=200)
每页 PNG 图片
  qwen3.5-ocr (百炼 API)
每页 Markdown
  合并 + 分页标记
完整 .md 文档
```n
| 步骤 | 工具 | 理由 |
|------|------|------|
| PDF→图片 | PyMuPDF (fitz) | 本地、轻量、速度快 |
| 图片→MD | qwen3.5-ocr (百炼) | 已验证 4.12s/图，中文准确率高 |
| 合并 | Python 字符串拼接 | 简单可控 |

### 2.3 OCR 引擎决策记录

| 引擎 | 实测状态 | 结论 |
|------|---------|------|
| qwen3.5-ocr（百炼 API）| ✅ 已验证 | 4.12s/图，1424 token，与 PaddleOCR-VL 并列（接口可切换）|
| PaddleOCR-VL-1.6（百度）| ⏸️ 已写脚本未跑 | 储备方案 |
| PP-OCRv6（百度）| ❌ 弃用 | 返回结构不兼容，KeyError |
| PaddleOCR 本地 | ❌ 弃用 | API 变动，中文效果一般 |
| Unstructured hi_res | ❌ 弃用 | OCR 引擎仅支持本地 |

### 2.4 性能基线（冒烟测试 2026-06-25）

| 脚本 | 模型/引擎 | 耗时 | token | 评价 |
|------|----------|------|-------|------|
| smoke_llm.py | qwen3.7-max-2026-06-08 | 7.34s | 374 | ✅ |
| smoke_llm_fast.py | qwen3.6-flash | 6.71s | 833 | ✅ |
| smoke_ocr.py | qwen3.5-ocr | 4.12s | 1424 | ✅ |
| smoke_paddle_ocr.py | PaddleOCR 本地 | - | - | ❌ 弃用 |
| smoke_baidu_ocr.py | PaddleOCR-VL-1.6 | 8.55s | 19,803字符 | ✅ 全 PDF 跑通 |

### 2.5 未跑通 / 弃用方案总结

1. **PaddleOCR 本地**：PaddleOCR.ocr(cls=True) 已废弃，新 API predict()，且中文效果一般
2. **Unstructured hi_res**：OCR 引擎不可换，无法接 qwen3.5-ocr API
3. **PP-OCRv6（百度）**：返回结构不兼容（KeyError），弃用
4. **PaddleOCR-VL-1.6（百度）**：✅ 已跑通，作为对比方案

### 2.6 模块 C 状态调整
由于无图像理解模型，模块 C 改为接口预留，待开通多模态模型再补
> 「多模态 RAG」≠「多模态 LLM」
> 图像理解是"翻译官"（图片 → 文本），文本 RAG 是主干道。

| 方案 | 任务 | 工具 |
|------|------|------|
| OCR | 提取图中文字 | PaddleOCR |
| 图像理解 | 识别场景/物体/地点 | Qwen2-VL / GPT-4o |

---

## 3. 项目目录结构

```
Agentic-Multimodal-RAG/
├── PROJECT.md               ← 本文件
├── 参考资料.txt
├── data/
│   ├── raw/                 # 原始 txt/md/pdf
│   ├── parsed/              # 解析后的 Markdown
│   └── images/              # 从 PDF 抠出的图片
├── src/
│   ├── parsers/
│   │   ├── pdf_parser.py
│   │   ├── md_parser.py
│   │   └── txt_parser.py
│   ├── chunking/splitter.py
│   ├── cleaning/                  # 通用清洗（新）
│   │   └── universal_cleaner.py  # ✅ M9 完成
│   ├── loaders/                  # 多格式加载（新）
│   │   └── document_loader.py    # ✅ M8 完成
│   ├── embeddings/embedder.py
│   ├── vectorstore/faiss_store.py
│   ├── multimodal/image_understanding.py
│   └── rag/
│       ├── basic_rag.py
│       └── agentic_graph.py
├── tests/
│   ├── test_iter_A*.py
│   ├── test_iter_B*.py
│   ├── test_iter_C*.py
│   ├── test_iter_D*.py
│   └── test_iter_E*.py
├── notebooks/
├── outputs/
│   ├── *.md
│   ├── faiss_index/
│   └── logs/
├── requirements.txt
└── README.md
```

---

## 4. 2 天开发计划（8 个迭代）

### Day 1 上午 - 模块 A：PDF → Markdown（2.5h）
| Iter | 内容 | 测试标准 | 状态 |
|------|------|---------|------|
| A1 | 环境搭建 + PaddleOCR 冒烟 | 4 个冒烟脚本全部通过 | ✅ 完成 |
| A2 | PyMuPDF + qwen3.5-ocr 解析 PDF | PDF→图片→OCR→Markdown，5 项验收 | ✅ 完成 |
| A3 | Markdown 结构优化 + OCR 引擎统一接口 | 4 项验收全过（零消耗）| ✅ 完成 |

### Day 1 下午 - 模块 B：Embedding + 向量库 + 基础 RAG（3h）
| Iter | 内容 | 测试标准 | 状态 |
|------|------|---------|------|
| B1 | 多格式统一加载器 | 6/6 验收全过（不消耗 OCR）| ✅ 完成 |
| B1.5 | Universal Cleaner | 8/8 规则 + 性能测试（2MB 187ms）| ✅ 完成 |
| B2 | MarkdownHeaderTextSplitter 语义切分 | chunk 200-500 字 | ⬜ 待开始 |
| B3 | BGE Embedding + FAISS 入库 | top-5 相似度命中关键词 | ⬜ 待开始 |
| B4 | 基础 RAG 检索（不接 LLM） | 5 个旅游问题命中率 ≥ 80% | ⬜ 待开始 |

### Day 2 上午 - 模块 C：多模态图片 → 文本（2h）
| Iter | 内容 | 测试标准 | 状态 |
|------|------|---------|------|
| C1 | Qwen2-VL/GPT-4o 图片描述封装 | 3 张景点图描述含地点+景物 | ⬜ 待开始 |
| C2 | 多模态统一入口 | text/image_path 输入统一返回可检索文本 | ⬜ 待开始 |

### Day 2 下午 - 模块 D：LangGraph + Agentic RAG（4h）
| Iter | 内容 | 测试标准 | 状态 |
|------|------|---------|------|
| D1 | StateGraph 定义 + 工具节点 | 图能编译不报错 | ⬜ 待开始 |
| D2 | 决策节点（要不要检索） | 闲聊直答，工具问题触发检索 | ⬜ 待开始 |
| D3 | 评分节点（检索质量） | yes/no 正确路由 | ⬜ 待开始 |
| D4 | 改写节点（最多 2 次重试） | 刁钻问题自动改写 | ⬜ 待开始 |
| D5 | 生成节点 + 图连线 | 完整状态流转日志 | ⬜ 待开始 |

### Day 2 晚上 - 模块 E：端到端整合（1h）
| Iter | 内容 | 测试标准 | 状态 |
|------|------|---------|------|
| E1 | 旅游助理整合 | 3 个端到端用例全通过 | ⬜ 待开始 |

### 验收用例（E1）
1. 文本："北京三日游攻略" → 返回结构化行程
2. 图片：上传故宫照片 → 返回"这是故宫... 推荐半日游..."
3. 刁钻："适合带老人的美食之旅" → 触发自动重写

---

## 5. 进展日志


### 5.1 已选定模型清单（19 个 · 百炼 MaaS OpenAI 兼容）

| 用途 | 模型 ID | 说明 |
|------|---------|------|
| 主推理（生成答案、行程规划） | `qwen3.7-max-2026-06-08` | 最新千问旗舰 |
| 快速任务（评分、改写） | `qwen3.6-flash` | 低延迟、省 token |
| 高性价比生成 | `qwen3.7-plus` / `qwen3.7-plus-2026-05-26` | 批量任务 |
| 大参数 MoE | `qwen3.6-35b-a3b` / `qwen3.6-27b` | 中等推理 |
| 国产备用 | `deepseek-v4-pro` / `kimi-k2.6` / `glm-5.2` | 对比实验 |
| OCR（中文 + 英文） | `qwen3.5-ocr` | 唯一 OCR 模型 |
| ⚠️ 无多模态视觉 | - | 待后续开通 |

> **额度**：每个模型 1,000,000 token。`qwen3.7-max-2026-06-08` 额度耗尽时自动切到 `qwen3.7-max` → `qwen3.7-plus`。

### 5.2 模型选用原则
- 默认用最新版（带日期后缀的最新值）
- 性能测试时主模型与 Flash 各跑一次，对比耗时和 token
- 每个冒烟脚本必须打印：⏱️ 耗时 / 📊 Token / 📝 内容

### 5.3 性能基线（来自冒烟测试 2026-06-25）

| 脚本 | 模型 | 耗时 | prompt | completion | total |
|------|------|------|--------|------------|-------|
| smoke_llm.py | qwen3.7-max-2026-06-08 | 7.34s | 16 | 358 | 374 |
| smoke_llm_fast.py | qwen3.6-flash | 16.96s | 27 | 2036 | 2063 ⚠️ |
| smoke_ocr.py | qwen3.5-ocr | 4.12s | 766 | 658 | 1424 |
| smoke_paddle_ocr.py | PaddleOCR 本地 | 待补 | - | - | - |

⚠️ **qwen3.6-flash 输出 2036 token 异常偏高**：疑似 prompt 触发了长列表模式，后续用更严格的 prompt 控制。

### 5.4 模块 C 状态调整
由于无图像理解模型，**模块 C「多模态图片 → 文本」改为接口预留 + 单元测试桩**，待后续开通多模态模型再补。OCR 能力通过 `qwen3.5-ocr` API + PaddleOCR 本地双保险实现。

### 5.5 PaddleOCR 已知问题
- `PaddleOCR.ocr(cls=True)` 已废弃，新 API 为 `PaddleOCR.predict(img)`，不带 cls 参数
- 识别结果通过 `.json.get("res")[].rec_texts` 获取（不再是 `[[(box, (text, conf))]]`）
### 2026-06-25
- M1：完成 Iter A1 环境搭建与冒烟测试
  - 解决 pip 依赖冲突（paddlenlp protobuf/PyYAML 警告，可忽略）
  - 模型锁定 19 个百炼模型
  - 向量库技术选型 FAISS → Chroma（更轻量）
  - 4 个百炼冒烟脚本全部通过
- M2：完成 A2 架构选型调整（重要决策）
  - ❌ 原方案 Unstructured hi_res 放弃：OCR 引擎仅支持本地 PaddleOCR，无法接 qwen3.5-ocr API
  - ✅ 采用方案 2：PyMuPDF + qwen3.5-ocr 自建
    - PyMuPDF 把 PDF 每页转图片（dpi=200）
    - qwen3.5-ocr 把每页图片直接识别为 Markdown
    - 自动合并为完整 .md 文档
  - ⏸️ 储备方案 B：PaddleOCR-VL-1.6 直接产出 MD，等 A 方案效果不达标时切换
- M3：完成 A2 测试脚本
  - 新增 src/parsers/pdf_to_images.py、ocr_to_markdown.py
  - 新增 tests/test_iter_A2.py 含 5 项验收检查
  - PDF 已就位（data/raw/sample.pdf），待跑测试
- 未跑通/弃用方案记录：
  - ❌ smoke_paddle_ocr.py：PaddleOCR 本地 API 已变（ocr(cls=True)→predict()），中文效果一般
  - ❌ Unstructured hi_res：OCR 引擎不可换，不支持 API OCR 集成
  - ⏸️ smoke_baidu_ocr.py：百度 PaddleOCR-VL-1.6/PP-OCRv6 已写未跑，储备中
- M4：✅ A2 测试通过（2026-06-25）
  - PDF 共 15 页，Step1 转图 3s，Step2 OCR 28s，总耗时 31.35s
  - 总 Token: 62796，平均 4186 token/页
  - 5 项验收全过：PDF→图片 / OCR 识别 / MD 文件 / 非空 / ≥20 行
  - 产物：outputs/parsed/document.md + outputs/parsed/pages/*.png
  - 报告：outputs/logs/A2_test_report.json
- M5：PP-OCRv6 对比测试失败（2026-06-25）
  - 提交任务成功但下载结果 KeyError: layoutParsingResults
  - 根据官方文档修正后仍不兼容
  - 决策：改用 PaddleOCR-VL-1.6（已跑通）做对比
- M6：✅ PaddleOCR-VL-1.6 对比测试通过（2026-06-25）
  - 总耗时 8.55s（vs qwen3.5-ocr 31.35s，快 3.7 倍）
  - 输出 233 行 / 19,803 字符（比 qwen 更精简）
  - 中文效果好，用户决策：两个 OCR 都保留，做成可选接口
  - 决策：A3 阶段把 OCR 引擎封装成统一接口，参数切换
- 下一里程碑：A3 Markdown 优化 + OCR 接口封装 → B1-B4 检索层 → C/D/E

---

## 6. 假设与前提

| # | 假设 | 风险 |
|---|------|------|
| 1 | Python 3.10 + Windows | PaddleOCR 需 VC++ 运行库 |
| 2 | 有 DeepSeek / 硅基流动 API Key | 无 Key 则 D/E 模块卡住 |
| 3 | 无 GPU 或入门级 | Embedding 走本地 BGE 或 API |
| 4 | 目标是本地可跑 Demo | 不追求生产级性能 |

---

## 7. 风险与应急预案

| 卡点 | 应急方案 |
|------|---------|
| PaddleOCR 装不上 | 跳过 PDF 解析，直接拿 .md 跑后续 |
| 无 GPU | Embedding 用硅基流动 BGE-M3 API |
| 无 API Key | Ollama 本地 qwen2.5:7b + llava:7b |
| LangGraph 报错 | 简化 3 节点：retrieve → grade → generate |

---

## 8. 准备工作清单

- [ ] 1 份样例 PDF（旅游攻略类，含表格和图）
- [ ] DeepSeek / 硅基流动 API Key
- [ ] 3 张景点图片（故宫、长城、外滩等）

---

## 9. 更新规范

每完成一个 Iter 必须更新：
1. 本文档"4. 2 天开发计划"对应行的状态（⬜→🔄→✅）
2. 本文档"5. 进展日志"追加一行记录
3. 在 tests/ 下保存对应测试脚本
4. 关键产物路径登记到"10. 产物清单"

---

## 10. 产物清单

| 类型 | 路径 | 备注 |
|------|------|------|
| 解析后的 Markdown | outputs/parsed/document.md | ✅ A2 已生成 |
| PDF 拆图 | outputs/parsed/pages/*.png | ✅ A2 已生成（15 张）|
| A2 测试报告 | outputs/logs/A2_test_report.json | ✅ A2 已生成 |
| Cleaner 清洗输出 | outputs/parsed/sample_*.md | ✅ M9 已生成 |
| 向量索引 | outputs/chroma_db/ | 待生成 |
| 测试日志 | outputs/logs/ | 待生成 |
| 图片素材 | data/images/ | 从 PDF 抽取 |

---

使用说明：在任何新对话中，先打开此文档，模型即可知道项目全貌与当前进展。

---


---


---

## 13. 多格式清洗策略分析（2026-06-25 用户提出）

### 13.1 现状

| 格式 | 解析方式 | 清洗 |
|------|---------|------|
| PDF | OCR -> Markdown | clean_markdown_full（去分页标记）|
| .md | 直读 | 当前无清洗 |
| .txt | 直读 | 当前无清洗 |
| .docx | 不支持 | - |

### 13.2 用户提出的清洗场景

#### A. 乱码清洗
- 来源：OCR 偶尔识别错误、PDF 编码异常
- 表现：出现 `、???、` 等无意义字符
- 必要性：高（影响 Embedding 质量）

#### B. 分隔符清洗
- 来源：Word 文档复制粘贴遗留
- 表现：连续 ====== 或 ----------（长度 6+）
- 必要性：中（影响语义连贯，但 Embedding 还能容忍）

### 13.3 推荐方案：分层清洗架构

**决策：统一入口 + 按类型分桶清洗**

理由：
1. 通用规则（去空行、去噪字符）对所有格式适用
2. 格式特有规则（去分页标记、去 OCR 噪音）只对 PDF/MD 适用
3. 单个入口方便用户调用，内部按类型分发

### 13.4 清洗架构设计

`
load_document(file)
   |
   v
parse_to_raw_text(file)        <- 格式特定解析（PDF/MD/TXT）
   |
   v
detect_format_and_clean(text)   <- 格式检测 + 路由清洗
   |
   +-- universal_clean(text)    <- 所有格式通用（乱码/分隔符/空白）
   +-- pdf_clean(text)          <- PDF 特有（分页标记）
   +-- md_clean(text)           <- MD 特有（表格噪音）
   |
   v
return clean text
`

### 13.5 通用清洗规则（universal_clean）

适用于所有格式：

| 规则 | 示例 | 处理 |
|------|------|------|
| 去连续空行 | a\n\n\n\nb | a\n\nb |
| 去行首尾空白 | \u00a0hello\u00a0 | hello |
| 去零宽字符 | \u200b\u200c\u200d | 删除 |
| 去 BOM | \ufeff | 删除 |
| 去 OCR 乱码 | `、??? 簇 | 替换为空 |
| 去长分隔符 | ====== / ------ | 替换为 --- |

### 13.6 格式特有规则

| 格式 | 额外清洗 |
|------|---------|
| PDF | 去 # 第 N 页、去独立 ---（分页标记）|
| MD | 去 HTML 注释 <!-- ... --> |
| TXT | 去重复连续段落 |

### 13.7 实现计划

`
src/cleaning/
├── universal_cleaner.py    <- 所有格式通用（v1 必做）
├── pdf_cleaner.py          <- PDF OCR 输出（v1 必做）
├── md_cleaner.py           <- MD 特有（v2 选做）
├── router.py               <- 统一入口，按格式分发
└── __init__.py
`

### 13.8 与现有代码的关系

- 保留 src/parsers/markdown_cleaner.py（不动）
- 新增 src/cleaning/ 目录，独立模块
- load_document() 调用 router.clean_document() 而不是直接解析
- 不破坏向后兼容

### 13.9 决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口数量 | 统一入口 router.clean_document() | 用户调用简单 |
| 规则组织 | 通用 + 格式特有分桶 | 既复用又灵活 |
| 清洗粒度 | 三档：light/standard/aggressive | 不同场景可选 |
| B2 集成 | 只做 light + standard 两档 | 满足当前需求 |

## 12. 批量并行处理方案分析（2026-06-25 用户提出）

### 12.1 用户场景

| 场景 | 处理流程 |
|------|---------|
| 用户上传 1 个文档 | 串行：加载 -> 解析 -> 分块 -> 入库 |
| 用户上传 N 个文档 | 并行：每个文档独立 pipeline，同时执行 |

### 12.2 流水线拆解

每个文档的 pipeline 包含 4 步：
1. 加载 load_document (PDF 调 OCR, md/txt 直读)
2. 解析/清洗 markdown_cleaner (仅 PDF 需要)
3. 分块 splitter (按标题切)
4. 入库 embed + vectorstore.add

### 12.3 Python 并行方案对比

| 方案 | 适用 | GIL | 推荐场景 |
|------|------|-----|---------|
| threading.Thread | I/O 密集 | 不受影响 (IO 释放 GIL) | 调 API (OCR/Embedding) |
| multiprocessing | CPU 密集 | 不受影响 (独立进程) | 本地大文档切分 |
| ThreadPoolExecutor | I/O 密集 | 不受影响 | 推荐: API 调用并行 |
| ProcessPoolExecutor | CPU 密集 | 不受影响 | 大量本地文本处理 |
| asyncio + aiohttp | 高并发 I/O | 单线程事件循环 | 超高并发 |

### 12.4 GIL 影响分析

`
Pipeline 各步的 GIL 状态:
  - 加载 (PDF->OCR API)    : I/O 密集, GIL 释放 [OK] 线程有效
  - 加载 (md/txt 直读)     : I/O 密集, GIL 释放 [OK]
  - 清洗 (字符串处理)      : CPU 密集, GIL 锁住 [NO] 线程无效
  - 分块 (文本切分)        : CPU 密集, GIL 锁住 [NO] 线程无效
  - 入库 (Embedding API)   : I/O 密集, GIL 释放 [OK] 线程有效
`

结论:
- I/O 步骤 (OCR, Embedding) -> 线程并行有效
- CPU 步骤 (清洗, 分块) -> 线程无效，需多进程
- 本项目瓶颈是 OCR/Embedding (2-30s/次), 线程并行收益最大

### 12.5 推荐方案: ThreadPoolExecutor

理由:
1. OCR/Embedding 是 I/O 密集型，线程并行有效
2. 清洗/分块单文档 < 100ms，不是瓶颈
3. API 简单，代码易维护
4. 进程池开销大 (50MB/进程)，小文档不划算

### 12.6 一一对应关系设计

伪代码:
`python
def process_single_doc(file_path: str) -> dict:
    content = load_document(file_path)              # 1. 加载
    chunks = split_document(content, file_path)     # 2+3. 清洗+分块
    doc_ids = vectorstore.add_documents(chunks)     # 4. 入库
    return {"file": file_path, "chunks": len(chunks), "ids": doc_ids}

def process_batch(file_paths: list) -> list:
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_single_doc, fp): fp for fp in file_paths}
        results = []
        for future in as_completed(futures):
            fp = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({"file": fp, "error": str(e)})
        return results
`

### 12.7 异常隔离策略

| 错误类型 | 处理 |
|---------|------|
| 单文档失败 | 该文档返回 error，其他继续 |
| OCR 失败 | 重试 1 次，仍失败则跳过 |
| Embedding 失败 | 重试 2 次 (指数退避) |
| 数据库失败 | 整体报错，停止后续入库 |

### 12.8 实现计划

| 步骤 | 内容 | 时机 |
|------|------|------|
| 1 | src/processing/pipeline.py (单文档) | B2 阶段 |
| 2 | src/processing/batch.py (批量) | B3 阶段 |
| 3 | 性能基准测试 (1/5/10 文档) | B3 末尾 |
| 4 | 真实多文档上传测试 | E1 阶段 |

### 12.9 决策记录

- 采用: ThreadPoolExecutor (I/O 密集为主)
- 不采用: 多进程 (开销大), asyncio (重写客户端成本高)
- 后续: 若 CPU 步骤成为瓶颈再切换 ProcessPoolExecutor
## 11. 后续待办（按优先级）

### 11.1 立即执行（等用户跑测试）
- [x] 跑 A2 测试：python tests/test_iter_A2.py（✅ 已通过）
- [x] 把测试输出贴回，把 5 项验收结果贴给我（✅ 已完成）
- [x] 检查 outputs/parsed/document.md 的中文质量（✅ 用户认可效果不错）

### 11.2 PaddleOCR-VL-1.6 对比测试（✅ 已完成）
- [x] 跑 PaddleOCR-VL-1.6 全量 PDF（✅ 8.55s/15页）
- [x] 对比指标：耗时 / Markdown 行数 / 中文准确率
- [x] 决策：两个 OCR 都保留，做成可选接口

### 11.3 A3 OCR 引擎统一接口（✅ 已完成）
- [x] 新建 src/parsers/unified_parser.py（parse_pdf_unified + auto 策略）
- [x] 封装 2 个引擎为统一接口
- [x] 跑统一接口测试（零消耗版本：本地缓存读取）
- [x] Markdown 清洗：去除分页标记噪音

### 11.4 B 模块当前任务：检索层
- [x] **Iter B1**：多格式统一加载器（✅ 6/6）
- [x] **Universal Cleaner**（✅ 8/8 + 性能测试）
- [ ] **Iter B2**：MarkdownHeaderTextSplitter 语义切分（按标题分级）
- [ ] **Iter B3**：BGE Embedding + Chroma 入库
- [ ] **Iter B4**：基础 RAG 检索测试（5 个旅游问题命中率）

### 11.3 A2 通过后立即进入
- [ ] Iter A3：Markdown 结构优化（去除分页标记噪音 / 按语义合并段落）
- [ ] Iter B1：多格式统一加载器（md/txt/pdf → 字符串）
- [ ] Iter B2：MarkdownHeaderTextSplitter 语义切分（按标题分级，200-500 字/chunk）
- [ ] Iter B3：BGE Embedding + Chroma 入库（outputs/chroma_db/）
- [ ] Iter B4：基础 RAG 检索测试（5 个旅游问题命中率）

### 11.5 B2 当前任务（待启动）
- [ ] Iter C1/C2：多模态图片接口预留（等开通多模态模型）
- [ ] Iter D1-D5：LangGraph + Agentic RAG（决策/评分/改写/生成节点）
- [ ] Iter E1：旅游助理端到端整合（3 个验收用例）

### 11.7 储备方案（条件触发）
- [ ] 若 A2 中文效果差 → 切换到方案 B：PaddleOCR-VL-1.6
- [ ] 若 qwen3.5-ocr 额度耗尽 → 用 PaddleOCR 本地 fallback（已弃用，需重写）
- [ ] 若多模态模型开通 → 补模块 C

### 11.8 文档维护
- [ ] 每次完成 Iter 后更新本文档 §4 状态、§5 进展日志、§10 产物清单

---

