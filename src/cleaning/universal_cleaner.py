"""
Universal Cleaner - all-format text cleaner
处理:
  - BOM / 零宽字符
  - 控制字符 / OCR 乱码
  - 长分隔符 ====== / ------
  - 连续空行
  - 行首尾空白
"""
import re
import time


def universal_clean(text: str) -> str:
    """通用文本清洗（不依赖文件格式）"""
    if not text:
        return ""

    text = text.replace("\ufeff", "")
    text = text.replace("\u200b", "")
    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")

    text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)

    text = re.sub(r"\?{3,}", "", text)
    text = re.sub(r"\u00a0", " ", text)

    text = re.sub(r"={4,}", "---", text)
    text = re.sub(r"-{4,}", "---", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = text.strip()

    return text


def universal_clean_timed(text: str) -> tuple:
    """带耗时统计的清洗"""
    original_size = len(text)
    t0 = time.perf_counter()
    cleaned = universal_clean(text)
    elapsed = time.perf_counter() - t0
    return cleaned, elapsed, original_size, len(cleaned)


if __name__ == "__main__":
    test = "\ufeff\u200b\u00a0hello\u00a0world\n\n\n\n=====  \nfoo\n\n\n\nbar\n-----\nbaz\u0000????"
    print("=== input ===")
    print(repr(test))
    cleaned, elapsed, orig, new = universal_clean_timed(test)
    print("=== output ===")
    print(repr(cleaned))
    print(f"elapsed {elapsed*1000:.3f}ms, {orig} -> {new} chars")
