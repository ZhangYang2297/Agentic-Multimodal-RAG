"""
A3 v2 - 零消耗重跑（最终版）
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsers import (
    clean_markdown,
    clean_markdown_aggressive,
    clean_markdown_full,
)


def clean_from_local(pdf_path, engine, output_path):
    cache_map = {
        "qwen": "outputs/parsed/document.md",
        "paddle_vl": "outputs/parsed/paddleocr_vl_result.md",
    }
    cache_path = cache_map[engine]
    if not os.path.exists(cache_path):
        return {"error": f"cache not found: {cache_path}"}

    print(f"[CACHE] reading: {cache_path}")
    raw_md = Path(cache_path).read_text(encoding="utf-8")

    t0 = time.perf_counter()
    cleaned = clean_markdown_full(raw_md)
    elapsed = time.perf_counter() - t0

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(cleaned, encoding="utf-8")

    return {
        "engine": engine,
        "output_path": output_path,
        "char_count": len(cleaned),
        "line_count": len([l for l in cleaned.split("\n") if l.strip()]),
        "elapsed_sec": elapsed,
        "source_cache": cache_path,
    }


def check_no_page_marker(content):
    """检查没有分页标记（独立行 --- 和 # 第 N 页）"""
    lines = content.split("\n")
    has_standalone_dash = any(l.strip() == "---" for l in lines)
    has_page_marker = any(f"\u7b2c {i} \u9875" in l for l in lines for i in range(1, 30))
    return not has_standalone_dash, not has_page_marker


def main():
    pdf_path = "data/raw/sample.pdf"
    print("=" * 60)
    print("A3 v2 - zero cost rerun")
    print("=" * 60)

    # === Test 1 ===
    print("\n[TEST 1] Markdown cleaner unit test")
    test_input = "---\n# \u7b2c 1 \u9875\n# \u5317\u4eac\n\n## A\nx\n\n---\n# \u7b2c 2 \u9875\n\nB\n42\n"
    cleaned = clean_markdown(test_input)
    checks = {
        "remove ---": "---" not in cleaned,
        "remove # page 1": "\u7b2c 1 \u9875" not in cleaned,
        "keep title": "\u5317\u4eac" in cleaned,
        "remove page num 42": "\n42\n" not in cleaned,
    }
    for n, ok in checks.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")
    cleaner_ok = all(checks.values())

    # === Test 2 ===
    print(f"\n[TEST 2] paddle_vl cache clean")
    vl = clean_from_local(pdf_path, "paddle_vl", "outputs/parsed/sample_paddle_vl.md")
    if "error" not in vl:
        print(f"   engine: {vl['engine']}")
        print(f"   chars: {vl['char_count']:,}")
        print(f"   lines: {vl['line_count']}")
        content = Path(vl["output_path"]).read_text(encoding="utf-8")
        no_dash, no_page = check_no_page_marker(content)
        vl_checks = {
            "file exists": os.path.exists(vl["output_path"]),
            "chars > 1000": vl["char_count"] > 1000,
            "lines >= 20": vl["line_count"] >= 20,
            "no standalone ---": no_dash,
            "no # page N": no_page,
        }
        for n, ok in vl_checks.items():
            print(f"   {'OK' if ok else 'FAIL'} {n}")
        vl_ok = all(vl_checks.values())
    else:
        vl_ok = False

    # === Test 3 ===
    print(f"\n[TEST 3] qwen cache clean")
    qwen = clean_from_local(pdf_path, "qwen", "outputs/parsed/sample_qwen.md")
    if "error" not in qwen:
        print(f"   engine: {qwen['engine']}")
        print(f"   chars: {qwen['char_count']:,}")
        print(f"   lines: {qwen['line_count']}")
        content = Path(qwen["output_path"]).read_text(encoding="utf-8")
        no_dash, no_page = check_no_page_marker(content)
        qwen_checks = {
            "file exists": os.path.exists(qwen["output_path"]),
            "chars > 1000": qwen["char_count"] > 1000,
            "lines >= 20": qwen["line_count"] >= 20,
            "no standalone ---": no_dash,
            "no # page N": no_page,
        }
        for n, ok in qwen_checks.items():
            print(f"   {'OK' if ok else 'FAIL'} {n}")
        qwen_ok = all(qwen_checks.values())
    else:
        qwen_ok = False

    # === Test 4 ===
    print(f"\n[TEST 4] auto mode logic")
    from src.parsers.unified_parser import _choose_engine
    size_mb = os.path.getsize(pdf_path) / 1024 / 1024
    chosen = _choose_engine(pdf_path, "auto")
    print(f"   file size: {size_mb:.2f} MB")
    print(f"   auto chose: {chosen}")
    auto_ok = chosen == "qwen"

    # === summary ===
    print("\n" + "=" * 60)
    print("[RESULT] A3 summary (zero cost)")
    print("=" * 60)
    all_checks = {
        "cleaner unit": cleaner_ok,
        "paddle_vl cache clean": vl_ok,
        "qwen cache clean": qwen_ok,
        "auto mode": auto_ok,
    }
    for n, ok in all_checks.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")
    all_pass = all(all_checks.values())
    print(f"\n{'A3 PASSED' if all_pass else 'A3 NOT FULLY PASSED'}")

    if vl_ok and qwen_ok:
        print(f"\n[STATS] dual engine compare:")
        print(f"   {'metric':<12} {'paddle_vl':<12} {'qwen':<12}")
        print(f"   {'-'*36}")
        print(f"   {'chars':<12} {vl['char_count']:<12,} {qwen['char_count']:<12,}")
        print(f"   {'lines':<12} {vl['line_count']:<12} {qwen['line_count']:<12}")


if __name__ == "__main__":
    main()
