"""
Iter A2 验收测试
完整流程：PDF → 图片 → OCR → Markdown
"""
import sys
import os
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parsers import pdf_to_images, images_to_markdown


def main():
    pdf_path = "data/raw/sample.pdf"

    print("=" * 60)
    print("Iter A2: PDF → Markdown (PyMuPDF + qwen3.5-ocr)")
    print("=" * 60)

    if not os.path.exists(pdf_path):
        print(f"❌ 请先放一份 PDF 到 {pdf_path}")
        return

    t0 = time.perf_counter()
    image_paths = pdf_to_images(pdf_path, dpi=200)
    step1_time = time.perf_counter() - t0
    print(f"\n⏱️  Step1 (PDF→图片) 耗时: {step1_time:.2f}s")

    t0 = time.perf_counter()
    summary = images_to_markdown(image_paths)
    step2_time = time.perf_counter() - t0

    print("\n" + "=" * 60)
    print("🧪 A2 验收检查")
    print("=" * 60)

    md_content = Path(summary["output_path"]).read_text(encoding="utf-8")
    md_lines = [l for l in md_content.split("\n") if l.strip()]

    checks = {
        "PDF 成功转图片":   len(image_paths) > 0,
        "OCR 识别成功":     len(summary["pages"]) == len(image_paths),
        "Markdown 文件存在":  os.path.exists(summary["output_path"]),
        "Markdown 非空":     len(md_content) > 100,
        "Markdown 行数 ≥ 20": len(md_lines) >= 20,
    }

    all_pass = True
    for name, ok in checks.items():
        print(f"   {'✅' if ok else '❌'} {name}")
        if not ok:
            all_pass = False

    report = {
        "iter": "A2",
        "pdf": pdf_path,
        "step1_time_sec": round(step1_time, 2),
        "step2_time_sec": round(step2_time, 2),
        "total_pages": summary["total_pages"],
        "total_tokens": summary["total_tokens"],
        "avg_tokens_per_page": summary["avg_tokens_per_page"],
        "md_output": summary["output_path"],
        "md_size_bytes": len(md_content),
        "md_line_count": len(md_lines),
        "all_checks_passed": all_pass,
    }

    report_path = "outputs/logs/A2_test_report.json"
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n💾 测试报告: {report_path}")
    print(f"\n{'🎉 A2 验收通过!' if all_pass else '⚠️  A2 验收未完全通过，请检查'}")

    if all_pass:
        print("\n📌 下一步: Iter B1 - 多格式统一加载")


if __name__ == "__main__":
    main()
