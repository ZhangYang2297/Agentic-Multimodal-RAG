"""
A3-工具1: Markdown 清洗器
去除 OCR 输出中的噪音（分页标记、空行、重复内容）
"""
import re
from typing import List


def clean_markdown(md_text: str) -> str:
    """
    清洗 OCR 输出的 Markdown 文本

    处理项：
        1. 去除分页标记 --- 
        2. 去除 # 第 N 页 噪音标题
        3. 合并连续空行（最多保留 1 个）
        4. 去除行首尾空白
        5. 去除行末多余空格
        6. 保留有意义的换行
    """
    if not md_text:
        return ""

    lines = md_text.split("\n")
    cleaned_lines: List[str] = []
    prev_blank = False

    for line in lines:
        # 1. 去除行尾空格
        line = line.rstrip()

        # 2. 去除分页标记 ---
        if line.strip() == "---":
            continue

        # 3. 去除 "# 第 N 页" 标题（各种形式）
        if re.match(r"^#+\s*第\s*\d+\s*页\s*$", line.strip()):
            continue

        # 4. 去除 "Page X" 英文标记
        if re.match(r"^#+\s*Page\s*\d+\s*$", line.strip(), re.IGNORECASE):
            continue

        # 5. 空行处理：合并连续空行
        if not line.strip():
            if prev_blank:
                continue
            prev_blank = True
            cleaned_lines.append("")
            continue

        prev_blank = False
        cleaned_lines.append(line)

    # 6. 去除开头/结尾的空行
    while cleaned_lines and not cleaned_lines[0].strip():
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1].strip():
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)


def clean_markdown_aggressive(md_text: str) -> str:
    """
    激进清洗（额外去除页眉页脚特征）
    适用于 qwen3.5-ocr 输出（可能含页码标记）
    """
    cleaned = clean_markdown(md_text)

    lines = cleaned.split("\n")
    final_lines = []

    for line in lines:
        s = line.strip()

        # 去除单独的数字（页码残留）
        if re.match(r"^\d{1,3}$", s):
            continue

        # 去除 "Page X / Y" 类
        if re.match(r"^Page\s*\d+\s*(of|/)\s*\d+$", s, re.IGNORECASE):
            continue

        # 去除 "X / Y" 类
        if re.match(r"^\d+\s*/\s*\d+$", s):
            continue

        final_lines.append(line)

    return "\n".join(final_lines)


def clean_markdown_full(md_text: str) -> str:
    """
    完整清洗：先去掉独立 --- 分页，再激进清洗
    比 clean_markdown 更彻底，适用于 qwen3.5-ocr 输出
    """
    # 先用标准清洗
    cleaned = clean_markdown(md_text)
    # 再做激进清洗（去单独页码）
    cleaned = clean_markdown_aggressive(cleaned)
    return cleaned


if __name__ == "__main__":
    test_md = """---
# 第 1 页
# 北京三日游攻略

## 第一天
天安门 → 故宫 → 王府井

---

# 第 2 页

## 第二天

长城一日游

42
"""
    print("=== 原始 ===")
    print(test_md)
    print("=== 清洗后 ===")
    print(clean_markdown(test_md))
