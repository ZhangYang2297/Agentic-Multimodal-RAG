"""
A3-工具2 (v2 修复): OCR 引擎统一接口
修复:  qwen 引擎通过 images_to_markdown 返回值字段名问题
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
    if engine != "auto":
        return engine
    size_mb = os.path.getsize(file_path) / 1024 / 1024
    return "paddle_vl" if size_mb < 2.0 else "qwen"


def parse_pdf_unified(
    file_path: str,
    engine: EngineType = "auto",
    output_path: Optional[str] = None,
    clean: bool = True,
    aggressive_clean: bool = False,
) -> dict:
    chosen = _choose_engine(file_path, engine)

    print(f"\u5bf9\u9009\u62e9\u5f15\u64ce: {chosen}")
    print(f"   \u6587\u4ef6: {file_path} ({os.path.getsize(file_path)/1024/1024:.2f} MB)")
    print("=" * 60)

    t0 = time.perf_counter()

    if chosen == "paddle_vl":
        result = parse_pdf_via_paddleocr_vl(file_path)
        raw_md = result["full_markdown"]
        elapsed = time.perf_counter() - t0

    elif chosen == "qwen":
        images = pdf_to_images(file_path, dpi=200)
        result = images_to_markdown(images)
        # v2 \u4fee\u590d: images_to_markdown \u8fd4\u56de\u7684\u662f\u5404\u9875 markdown \u5217\u8868
        if isinstance(result, dict):
            page_list = result.get("pages", [])
            raw_md = "\n\n---\n\n".join(
                p["markdown"] if isinstance(p, dict) else str(p)
                for p in page_list
            )
        else:
            raw_md = str(result)
        elapsed = time.perf_counter() - t0

    else:
        raise ValueError(f"\u672a\u77e5\u5f15\u64ce: {engine}")

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
        output_path = f"outputs/parsed/{stem}_{chosen}.md"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    summary = {
        "engine": chosen,
        "markdown": md,
        "char_count": char_count,
        "line_count": line_count,
        "output_path": output_path,
        "elapsed_sec": elapsed,
    }

    print(f"\n\ud83c\udf89 \u89e3\u6790\u5b8c\u6210!")
    print(f"   \u5f15\u64ce: {chosen}")
    print(f"   \u8017\u65f6: {elapsed:.2f}s")
    print(f"   \u5b57\u7b26\u6570: {char_count:,}")
    print(f"   \u884c\u6570: {line_count}")
    print(f"   \u8f93\u51fa: {output_path}")

    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("\u7528\u6cd5: python unified_parser.py <pdf_path> [engine]")
        sys.exit(1)
    pdf = sys.argv[1]
    eng = sys.argv[2] if len(sys.argv) > 2 else "auto"
    parse_pdf_unified(pdf, engine=eng)
