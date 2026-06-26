"""
A3 验收测试
1. OCR 引擎统一接口（qwen + paddle_vl + auto）
2. Markdown 清洗（去除分页噪音）
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsers import (
    parse_pdf_unified,
    clean_markdown,
    clean_markdown_aggressive,
    parse_pdf_via_paddleocr_vl,
    pdf_to_images,
    images_to_markdown,
)


def test_cleaner():
    """单元测试：清洗器"""
    print("=" * 60)
    print("🧪 测试 1: Markdown 清洗器")
    print("=" * 60)

    test_input = """---
# 第 1 页
# 北京三日游攻略
内容开始

## 第一天

天安门 → 故宫
---

# 第 2 页


## 第二天

长城
42
"""

    cleaned = clean_markdown(test_input)
    print("清洗后前 10 行:")
    for i, line in enumerate(cleaned.split("\n")[:10], 1):
        print(f"  {i}. {line}")

    # 检查：不应包含 '---' 或 '# 第 X 页'
    checks = {
        "去除分页标记 ---": "---" not in cleaned,
        "去除 # 第 N 页": not any("第 1 页" in l or "第 2 页" in l for l in cleaned.split("\n")),
        "保留正文": "北京三日游攻略" in cleaned and "天安门" in cleaned,
        "去除单独页码 42": "\n42\n" not in cleaned,
    }
    print("\n验收:")
    for name, ok in checks.items():
        print(f"   {'✅' if ok else '❌'} {name}")
    return all(checks.values())


def test_unified_with_engine(pdf_path: str, engine: str) -> dict:
    """测试统一接口的某个引擎"""
    print(f"\n{'=' * 60}")
    print(f"🧪 测试 2-{engine}: 引擎 {engine}")
    print(f"{'=' * 60}")

    t0 = time.perf_counter()
    result = parse_pdf_unified(pdf_path, engine=engine, clean=True)
    total_elapsed = time.perf_counter() - t0

    print(f"\n📊 完整流程耗时: {total_elapsed:.2f}s")
    print(f"   OCR 耗时: {result['elapsed_sec']:.2f}s")
    print(f"   字符数: {result['char_count']:,}")
    print(f"   行数: {result['line_count']}")

    md = result["markdown"]
    checks = {
        "输出文件存在": os.path.exists(result["output_path"]),
        "内容非空": result["char_count"] > 100,
        "行数 ≥ 20": result["line_count"] >= 20,
        "无 --- 分页": "---" not in md,
        "无 # 第 N 页": not any(f"第 {i} 页" in l for l in md.split("\n") for i in range(1, 30)),
    }

    print("\n验收:")
    for name, ok in checks.items():
        print(f"   {'✅' if ok else '❌'} {name}")
    return {"result": result, "checks": checks}


def main():
    pdf_path = "data/raw/sample.pdf"

    print("=" * 60)
    print("Iter A3 验收测试")
    print("=" * 60)

    if not os.path.exists(pdf_path):
        print(f"❌ PDF 不存在: {pdf_path}")
        return

    # === Test 1: 清洗器单元测试 ===
    cleaner_ok = test_cleaner()

    # === Test 2: 引擎 paddle_vl ===
    vl = test_unified_with_engine(pdf_path, "paddle_vl")

    # === Test 3: 引擎 qwen ===
    qwen = test_unified_with_engine(pdf_path, "qwen")

    # === Test 4: auto 模式 ===
    print(f"\n{'=' * 60}")
    print(f"🧪 测试 4: auto 模式（按文件大小自动选）")
    print(f"{'=' * 60}")
    auto = parse_pdf_unified(pdf_path, engine="auto", clean=True)
    print(f"\n   自动选择: {auto['engine']}")
    print(f"   （文件大小 {os.path.getsize(pdf_path)/1024/1024:.2f} MB → < 2MB 用 paddle_vl）")

    # === 总评 ===
    print("\n" + "=" * 60)
    print("🏆 A3 总评")
    print("=" * 60)
    all_checks = {
        "清洗器单元测试": cleaner_ok,
        "paddle_vl 引擎": all(vl["checks"].values()),
        "qwen 引擎": all(qwen["checks"].values()),
        "auto 模式": auto["char_count"] > 100,
    }

    for name, ok in all_checks.items():
        print(f"   {'✅' if ok else '❌'} {name}")

    all_pass = all(all_checks.values())
    print(f"\n{'🎉 A3 验收通过!' if all_pass else '⚠️  部分未通过，请检查'}")

    # 对比两个引擎输出
    print("\n📊 双引擎对比:")
    print(f"   {'指标':<15} {'paddle_vl':<15} {'qwen':<15}")
    print(f"   {'-'*45}")
    print(f"   {'耗时(s)':<15} {vl['result']['elapsed_sec']:<15.2f} {qwen['result']['elapsed_sec']:<15.2f}")
    print(f"   {'字符数':<15} {vl['result']['char_count']:<15,} {qwen['result']['char_count']:<15,}")
    print(f"   {'行数':<15} {vl['result']['line_count']:<15} {qwen['result']['line_count']:<15}")


if __name__ == "__main__":
    main()
