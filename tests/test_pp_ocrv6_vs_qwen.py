"""
PP-OCRv6 vs qwen3.5-ocr 对比测试
输入：同一份 sample.pdf（15 页）
输出：
  - outputs/parsed/pp_ocrv6_result.md
  - outputs/parsed/comparison_report.md
"""
import os
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsers import (
    pdf_to_images,
    parse_pdf_via_ppocrv6,
)


def main():
    pdf_path = "data/raw/sample.pdf"

    print("=" * 60)
    print("OCR 引擎对比测试: PP-OCRv6 vs qwen3.5-ocr")
    print("=" * 60)

    if not os.path.exists(pdf_path):
        print(f"❌ PDF 不存在: {pdf_path}")
        return

    # === 1. 统计基础信息 ===
    images = pdf_to_images(pdf_path, dpi=200)
    total_pages = len(images)
    print(f"\n📄 PDF 共 {total_pages} 页")
    pdf_size_kb = os.path.getsize(pdf_path) / 1024
    print(f"📦 文件大小: {pdf_size_kb:.1f} KB\n")

    # === 2. 跑 PP-OCRv6 ===
    print("=" * 60)
    print("🔍 引擎 B: PP-OCRv6 (百度)")
    print("=" * 60)

    try:
        t0 = time.perf_counter()
        pp_result = parse_pdf_via_ppocrv6(pdf_path, use_chart_recognition=False)
        pp_total_elapsed = time.perf_counter() - t0

        pp_md_path = "outputs/parsed/ppocrv6_result.md"
        Path(pp_md_path).parent.mkdir(parents=True, exist_ok=True)
        Path(pp_md_path).write_text(pp_result["full_markdown"], encoding="utf-8")

        print(f"\n📊 PP-OCRv6 结果:")
        print(f"   ⏱️  总耗时: {pp_total_elapsed:.2f}s")
        print(f"   📄 输出: {pp_md_path}")
        print(f"   📊 Markdown 行数: {pp_result['md_lines']}")
        print(f"   📊 Markdown 字符数: {pp_result['md_chars']}")
        print(f"   📊 检测到图片: {pp_result['image_count']} 张")
        print(f"   📊 平均每页: {pp_result['md_chars']//total_pages} 字符")

    except Exception as e:
        print(f"\n❌ PP-OCRv6 测试失败: {e}")
        print("   可能原因: 模型名错 / token 无权限 / PDF 太大")
        print("   解决方案: 检查 OCR-TOKEN 或联系百度开通 PP-OCRv6 权限")
        return

    # === 3. 读取 qwen3.5-ocr 已生成的结果 ===
    qwen_md_path = "outputs/parsed/document.md"
    qwen_lines = qwen_chars = 0
    qwen_exists = Path(qwen_md_path).exists()

    if qwen_exists:
        qwen_content = Path(qwen_md_path).read_text(encoding="utf-8")
        qwen_lines = len([l for l in qwen_content.split("\n") if l.strip()])
        qwen_chars = len(qwen_content)

    # === 4. 生成对比报告 ===
    print("\n" + "=" * 60)
    print("📊 生成对比报告")
    print("=" * 60)

    qwen_elapsed = 31.35
    qwen_tokens = 62796
    qwen_avg = qwen_tokens // total_pages if total_pages else 0

    report = f"""# OCR 引擎对比报告

**生成时间**: 2026-06-25
**测试 PDF**: {pdf_path} ({pdf_size_kb:.1f} KB, {total_pages} 页)

---

## 引擎 A: qwen3.5-ocr（百炼 MaaS）✅ 主方案

| 指标 | 值 |
|------|-----|
| 架构 | 同步 HTTP |
| 总耗时 | {qwen_elapsed}s |
| 总 Token | {qwen_tokens:,} |
| 平均每页 | {qwen_avg:,} token ({qwen_elapsed/total_pages:.2f}s) |
| Markdown 行数 | {qwen_lines} |
| Markdown 字符数 | {qwen_chars:,} |
| 中文准确率 | ✅ 用户确认效果不错 |
| 计费 | 100 万 token / ¥额度包 |

**优势**:
- ✅ 已实测，中文质量高
- ✅ 同步调用，逻辑简单
- ✅ 多模态大模型，能理解上下文

**劣势**:
- ⚠️ 按 token 计费（长 PDF 成本高）
- ⚠️ 平均 4186 token/页

---

## 引擎 B: PP-OCRv6（百度智能云）🔍 待评估

| 指标 | 值 |
|------|-----|
| 架构 | 异步任务流（轮询）|
| 总耗时 | {pp_total_elapsed:.2f}s |
| 平均每页 | {pp_total_elapsed/total_pages:.2f}s |
| Markdown 行数 | {pp_result['md_lines']} |
| Markdown 字符数 | {pp_result['md_chars']:,} |
| 检测到图片 | {pp_result['image_count']} 张 |
| 计费单位 | 按页（待确认价格）|

**优势**:
- ✅ 异步处理，无需长连接
- ✅ 专门做 OCR 的服务，理论上更快
- ✅ 按页计费，价格可预期

**劣势**:
- ❓ 需要人工对比中文准确率
- ❓ 异步逻辑复杂（轮询）
- ❓ 需要确认 OCR-TOKEN 是否有 PP-OCRv6 权限

---

## 关键对比

| 维度 | qwen3.5-ocr | PP-OCRv6 | 差异 |
|------|-------------|----------|------|
| 速度 (s/页) | {qwen_elapsed/total_pages:.2f} | {pp_total_elapsed/total_pages:.2f} | {((pp_total_elapsed-qwen_elapsed)/qwen_elapsed*100):+.1f}% |
| 输出字符数 | {qwen_chars:,} | {pp_result['md_chars']:,} | {(pp_result['md_chars']-qwen_chars)/qwen_chars*100:+.1f}% |
| 输出行数 | {qwen_lines} | {pp_result['md_lines']} | {(pp_result['md_lines']-qwen_lines)/qwen_lines*100:+.1f}% |
| 计费 | token | 页 | - |

---

## 决策建议（待人工对比后填写）

- [ ] 打开 outputs/parsed/pp_ocrv6_result.md 与 outputs/parsed/document.md 对比
- [ ] 检查中文准确率（重点看数字、地名、价格）
- [ ] 检查表格识别（Markdown 表格语法）
- [ ] 检查图片引用

### 推荐决策
- 若 PP-OCRv6 速度快 50%+ 且中文准确 → **切换**
- 若速度相当 → **保留 qwen3.5-ocr**（已实测可用）
- 若中文差 / 报错 → **保留 qwen3.5-ocr**，PP-OCRv6 标弃用

---

## 产物清单

| 文件 | 路径 | 用途 |
|------|------|------|
| qwen3.5-ocr 结果 | outputs/parsed/document.md | 主方案（已确认）|
| PP-OCRv6 结果 | outputs/parsed/pp_ocrv6_result.md | 对比方案 |
| 对比报告 | outputs/parsed/comparison_report.md | 本文件 |
"""

    report_path = "outputs/parsed/comparison_report.md"
    Path(report_path).write_text(report, encoding="utf-8")
    print(f"\n💾 对比报告已保存: {report_path}")
    print(f"\n📌 下一步：人工对比 outputs/parsed/pp_ocrv6_result.md 与 outputs/parsed/document.md")


if __name__ == "__main__":
    main()
