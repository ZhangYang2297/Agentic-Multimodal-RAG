"""
B1: 多格式统一加载器
支持: .pdf / .md / .txt
- .pdf  -> 调用 parse_pdf_unified (OCR)
- .md   -> 直接读取
- .txt  -> 直接读取
"""
import os
from pathlib import Path
from typing import Literal


# 支持的文件类型
SUPPORTED_EXTS = {".pdf", ".md", ".txt", ".markdown"}

# OCR 引擎类型
OCREngine = Literal["qwen", "paddle_vl", "auto"]


def load_document(
    file_path: str,
    ocr_engine: str = "auto",
    clean_markdown: bool = True,
) -> str:
    """
    多格式统一加载器

    参数:
        file_path:      文件路径
        ocr_engine:     PDF 时使用的 OCR 引擎（auto/qwen/paddle_vl）
        clean_markdown: 是否清洗 Markdown（仅对 PDF 生效）

    返回:
        文档内容字符串
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"file not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext not in SUPPORTED_EXTS:
        raise ValueError(
            f"unsupported file type: {ext}. "
            f"supported: {sorted(SUPPORTED_EXTS)}"
        )

    # PDF -> OCR
    if ext == ".pdf":
        from src.parsers.unified_parser import parse_pdf_unified
        result = parse_pdf_unified(
            file_path,
            engine=ocr_engine,
            clean=clean_markdown,
        )
        return result["markdown"]

    # .md / .txt / .markdown -> 直接读
    return Path(file_path).read_text(encoding="utf-8")


def detect_format(file_path: str) -> str:
    """检测文件格式，返回扩展名（小写）"""
    return os.path.splitext(file_path)[1].lower()


def is_supported(file_path: str) -> bool:
    """判断文件类型是否支持"""
    return detect_format(file_path) in SUPPORTED_EXTS


def load_documents_batch(
    file_paths: list,
    ocr_engine: str = "auto",
    clean_markdown: bool = True,
) -> list:
    """
    批量加载文档

    返回:
        [{"path": ..., "content": ..., "ext": ..., "size": ...}, ...]
    """
    results = []
    for fp in file_paths:
        ext = detect_format(fp)
        try:
            content = load_document(fp, ocr_engine=ocr_engine, clean_markdown=clean_markdown)
            results.append({
                "path": fp,
                "content": content,
                "ext": ext,
                "size": len(content),
                "success": True,
            })
        except Exception as e:
            results.append({
                "path": fp,
                "content": None,
                "ext": ext,
                "size": 0,
                "success": False,
                "error": str(e),
            })
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python document_loader.py <file_path>")
        sys.exit(1)
    content = load_document(sys.argv[1])
    print(f"loaded {len(content)} chars")
    print("---")
    print(content[:200])
