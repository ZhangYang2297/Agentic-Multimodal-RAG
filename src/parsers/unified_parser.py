"""A3-工具2 (v3): OCR 引擎统一接口
策略变更 (v3):
  - PaddleOCR-VL 优先（输出标准 Markdown 标题，分块效果好）
  - qwen3.5-ocr 后备（输出含 HTML 标签，需更多清洗）
"""
import os
import time
from typing import Literal, Optional

from .ocr_to_markdown import images_to_markdown
from .pdf_to_images import pdf_to_images
from .paddleocr_vl import parse_pdf_via_paddleocr_vl
from .markdown_cleaner import clean_markdown, clean_markdown_aggressive, clean_markdown_full


EngineType = Literal["qwen", "paddle_vl", "auto"]


def _choose_engine(file_path: str, engine: str) -> str:
    """策略: PaddleOCR-VL 优先 → qwen 后备"""
    if engine != "auto":
        return engine
    return "paddle_vl"  # PaddleOCR-VL 输出标准 Markdown 标题，分块效果好


def parse_pdf_unified(
    file_path: str,
    engine: EngineType = "auto",
    output_path: Optional[str] = None,
    clean: bool = True,
    aggressive_clean: bool = False,
) -> dict:
    chosen = _choose_engine(file_path, engine)

    print(f"选择引擎: {chosen}")
    print(f"   文件: {file_path} ({os.path.getsize(file_path)/1024/1024:.2f} MB)")
    print("=" * 60)

    t0 = time.perf_counter()
    parsed_ok = False
    raw_md = ""
    engine_used = chosen

    # 尝试首选引擎
    if chosen == "paddle_vl":
        try:
            result = parse_pdf_via_paddleocr_vl(file_path)
            raw_md = result["full_markdown"]
            elapsed = time.perf_counter() - t0
            parsed_ok = True
            engine_used = "paddle_vl"
        except Exception as e:
            print(f"  ⚠️  PaddleOCR-VL 失败: {e}")
            print(f"  → 自动降级到 qwen3.5-ocr")
            chosen = "qwen"

    # 后备：qwen 引擎
    if chosen == "qwen" and not parsed_ok:
        try:
            images = pdf_to_images(file_path, dpi=200)
            result = images_to_markdown(images)
            if isinstance(result, dict):
                page_list = result.get("pages", [])
                raw_md = "\n\n---\n\n".join(
                    p["markdown"] if isinstance(p, dict) else str(p)
                    for p in page_list
                )
            else:
                raw_md = str(result)
            elapsed = time.perf_counter() - t0
            parsed_ok = True
            engine_used = "qwen"
        except Exception as e:
            elapsed = time.perf_counter() - t0
            return {
                "engine": "both_failed",
                "markdown": "",
                "char_count": 0,
                "line_count": 0,
                "output_path": "",
                "elapsed_sec": elapsed,
                "error": str(e),
            }

    if not parsed_ok:
        elapsed = time.perf_counter() - t0
        return {
            "engine": "both_failed",
            "markdown": "",
            "char_count": 0,
            "line_count": 0,
            "output_path": "",
            "elapsed_sec": elapsed,
            "error": "Both OCR engines failed",
        }

    # 清洗
    if clean:
        if aggressive_clean:
            md = clean_markdown_full(raw_md)
        else:
            md = clean_markdown(raw_md)
    else:
        md = raw_md

    char_count = len(md)
    line_count = len([l for l in md.split("\n") if l.strip()])

    if output_path is None:
        stem = os.path.splitext(os.path.basename(file_path))[0]
        output_path = f"outputs/parsed/{stem}_{engine_used}.md"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    summary = {
        "engine": engine_used,
        "markdown": md,
        "char_count": char_count,
        "line_count": line_count,
        "output_path": output_path,
        "elapsed_sec": elapsed,
    }

    print(f"\n🎉 解析完成!")
    print(f"   引擎: {engine_used}")
    print(f"   耗时: {elapsed:.2f}s")
    print(f"   字符数: {char_count:,}")
    print(f"   行数: {line_count}")
    print(f"   输出: {output_path}")

    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python unified_parser.py <pdf_path> [engine]")
        sys.exit(1)
    pdf = sys.argv[1]
    eng = sys.argv[2] if len(sys.argv) > 2 else "auto"
    parse_pdf_unified(pdf, engine=eng)
