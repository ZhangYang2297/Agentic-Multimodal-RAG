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
from concurrent.futures import ThreadPoolExecutor, as_completed


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
    max_workers: int = 4,
) -> list:
    """
    批量加载文档（ThreadPoolExecutor 并行）

    为什么用线程池：
      - OCR/Embedding 是 I/O 密集型，线程并行有效
      - 单文档失败不影响其他文档
      - 清洗/分块 < 100ms，不是瓶颈

    参数:
        file_paths:     文件路径列表
        ocr_engine:     OCR 引擎（auto/qwen/paddle_vl）
        clean_markdown: 是否清洗
        max_workers:    并行线程数（默认 4，与 PROJECT.md 一致）

    返回:
        [{"path": ..., "content": ..., "ext": ..., "size": ..., "success": ...}, ...]
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for fp in file_paths:
            future = executor.submit(
                _load_single, fp,
                ocr_engine=ocr_engine,
                clean_markdown=clean_markdown,
            )
            future_map[future] = fp

        for future in as_completed(future_map):
            fp = future_map[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({
                    "path": fp,
                    "content": None,
                    "ext": detect_format(fp),
                    "size": 0,
                    "success": False,
                    "error": str(e),
                })

    # 按原始顺序排序
    order = {fp: i for i, fp in enumerate(file_paths)}
    results.sort(key=lambda r: order.get(r["path"], 999))
    return results


def _load_single(file_path: str, ocr_engine: str = "auto", clean_markdown: bool = True) -> dict:
    """单个文档加载（供线程池调用）"""
    content = load_document(file_path, ocr_engine=ocr_engine, clean_markdown=clean_markdown)
    return {
        "path": file_path,
        "content": content,
        "ext": detect_format(file_path),
        "size": len(content),
        "success": True,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python document_loader.py <file_path>")
        sys.exit(1)
    content = load_document(sys.argv[1])
    print(f"loaded {len(content)} chars")
    print("---")
    print(content[:200])
