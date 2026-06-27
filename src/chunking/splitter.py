"""
B2: 统一分块模块

按文件类型自动选择分块策略：
  - .md / .markdown  → MarkdownHeaderTextSplitter（按标题层级切分）
  - .txt             → RecursiveCharacterTextSplitter（按段落/句子边界切分）

两种策略都包含「大段二次切分」机制，确保每个 chunk 不超过目标大小。
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional


# ─── 公开数据结构 ───

@dataclass
class Chunk:
    """单个分块，包含文本内容和元数据"""
    text: str
    metadata: dict = field(default_factory=dict)

    def __repr__(self):
        return f"Chunk(text={self.text[:50]}..., metadata={self.metadata})"


# ─── 默认参数 ───

DEFAULT_CHUNK_SIZE = 600       # 目标块大小（中文字符数 ≈ token 数 ×2）
DEFAULT_OVERLAP = 100          # 相邻块重叠字符数
MD_HEADERS = ["#", "##", "###"]  # 按哪些标题层级切分


# ═══════════════════════════════════════════════
#  公开接口
# ═══════════════════════════════════════════════

def split_document(
    content: str,
    file_path: Optional[str] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    doc_id: Optional[str] = None,
    doc_name: Optional[str] = None,
    md5: Optional[str] = None,
    version: int = 1,
) -> list[Chunk]:
    """统一文档分块入口。
    chunk metadata 中自动注入 doc_id/doc_name/md5/version/status/chunk_index。
    """
    fmt = _detect_format(content, file_path)

    if fmt == "markdown":
        chunks = _split_markdown(content, chunk_size=chunk_size, overlap=overlap)
    else:
        chunks = _split_plain_text(content, chunk_size=chunk_size, overlap=overlap)

    # 在每个 chunk 的 metadata 中注入文档信息
    for i, chunk in enumerate(chunks):
        if doc_id:
            chunk.metadata["doc_id"] = doc_id
        if doc_name:
            chunk.metadata["doc_name"] = doc_name
        if md5:
            chunk.metadata["md5"] = md5
        chunk.metadata["version"] = version
        chunk.metadata["status"] = "active"
        chunk.metadata["chunk_index"] = i

    return chunks


# ═══════════════════════════════════════════════
#  格式检测
# ═══════════════════════════════════════════════

def _detect_format(content: str, file_path: Optional[str] = None) -> str:
    """
    检测文档类型：
      1. 优先用文件扩展名判断
      2. 扩展名缺失时，扫描内容前半部分是否有 Markdown 标题模式
    """
    # 优先看扩展名
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".txt":
            return "text"
        if ext in (".md", ".markdown"):
            return "markdown"

    # 无扩展名或扩展名不明确 → 内容探测
    # 只扫描前 3000 字，避免大文件全文扫描
    head = content[:3000]
    # 匹配 # 开头且紧跟中英文的标题行，排除 # 第 X 页 这类分页标记
    header_pattern = re.compile(r"^#{1,3}\s+[^\d#].*$", re.MULTILINE)
    matches = header_pattern.findall(head)

    # 排除纯粹的 # 第 X 页 行后，看还剩几个真标题
    real_headers = [
        m for m in matches
        if not re.match(r"^#{1,3}\s+第\s*\d+\s*页\s*$", m.strip())
        and not re.match(r"^#{1,3}\s+Page\s*\d+\s*$", m.strip(), re.IGNORECASE)
    ]

    if real_headers:
        return "markdown"

    # 再检查是否有 HTML 标题标签（OCR 输出的常见格式）
    html_header_pattern = re.compile(r"<h[1-3][^>]*>.*?</h[1-3]>", re.DOTALL)
    if html_header_pattern.search(head):
        return "markdown"

    return "text"


# ═══════════════════════════════════════════════
#  Markdown 分块（按标题层级）
# ═══════════════════════════════════════════════

def _split_markdown(
    content: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """
    按标题层级（# / ## / ###）切分 Markdown

    实现步骤：
      1. 找到所有 #/##/### 标题行位置
      2. 相邻标题之间的内容构成一个「节」
      3. 每个节作为一个 chunk
      4. 超过 chunk_size 的节，用 _recursive_split 二次切分
      5. 元数据记录：header_path（标题路径，如 "请求参数 > 请求体"）
    """
    # 收集所有标题行（位置、层级、文本）
    headings = _extract_headings(content)

    # 如果没有标题 → 降级为纯文本分块
    if not headings:
        return _split_plain_text(content, chunk_size=chunk_size, overlap=overlap)

    chunks: list[Chunk] = []

    # 遍历标题区间，提取每个节
    for i, h in enumerate(headings):
        # 节的起始 = 当前标题位置
        start = h["pos"]
        # 节的结束 = 下一个标题位置（或文档末尾）
        end = headings[i + 1]["pos"] if i + 1 < len(headings) else len(content)
        # 节文本 = 标题行 + 其下的正文内容
        section_text = content[start:end].strip()

        if not section_text:
            continue

        # 计算当前标题的层级路径
        # 例如：h["hierarchy"] = ["1. 图片生成 API", "请求参数", "请求体"]
        header_path = " > ".join(h["hierarchy"]) if h["hierarchy"] else section_text.split("\n")[0]

        # 如果节长度 <= chunk_size，直接作为一个 chunk
        if len(section_text) <= chunk_size:
            chunks.append(Chunk(
                text=section_text,
                metadata={
                    "header": h["text"],
                    "header_path": header_path,
                    "level": h["level"],
                },
            ))
        else:
            # 大节 → 递归二次切分
            sub_texts = _recursive_split(
                section_text,
                chunk_size=chunk_size,
                overlap=overlap,
                separators=["\n\n", "\n", "。", "！", "？", "；"],
            )
            for j, st in enumerate(sub_texts):
                chunks.append(Chunk(
                    text=st,
                    metadata={
                        "header": h["text"],
                        "header_path": f"{header_path} (分段 {j + 1})",
                        "level": h["level"],
                        "sub_chunk": j + 1,
                    },
                ))

    # 文档开头没有标题的内容（如法律声明前导段）
    # 已经包含在第一个标题节之前？不对 — 第一个标题行之前的文字没被捕获。
    # 检查第一个标题位置之前是否有内容
    first_heading_pos = headings[0]["pos"]
    if first_heading_pos > 0:
        preamble = content[:first_heading_pos].strip()
        if preamble:
            # 前导内容也按纯文本分块插入到最前面
            pre_chunks = _split_plain_text(preamble, chunk_size=chunk_size, overlap=overlap)
            for pc in pre_chunks:
                pc.metadata["header"] = "(前言)"
                pc.metadata["header_path"] = "(前言)"
                pc.metadata["level"] = 0
            chunks = pre_chunks + chunks

    return chunks


def _extract_headings(content: str, max_level: int = 3) -> list[dict]:
    """
    从 Markdown 内容中提取标题行

    支持两种格式:
      - Markdown 原生:  ## 标题
      - HTML 标签:      <h2>标题</h2> （OCR 输出的常见格式）

    返回按位置排序的列表，每个元素:
      {
        "pos": int,           # 标题行在 content 中的起始位置
        "level": int,         # 标题层级 (1/2/3)
        "text": str,          # 标题文本
        "hierarchy": [str],   # 当前标题的层级路径
      }
    """
    raw_headers = []

    # --- 匹配 Markdown 原文标题: # 标题 ---
    md_pattern = re.compile(r"^(#{1," + str(max_level) + r"})\s+(.*?)$", re.MULTILINE)
    for m in md_pattern.finditer(content):
        level = len(m.group(1))
        text = m.group(2).strip()
        if _is_page_marker(text):
            continue
        raw_headers.append({
            "pos": m.start(),
            "level": level,
            "text": text,
        })

    # --- 匹配 HTML 标题标签: <h2>标题</h2> ---
    # OCR (qwen3.5-ocr) 的输出常见格式
    html_pattern = re.compile(r"<h([1-3])\b[^>]*>(.*?)</h\1>", re.DOTALL)
    for m in html_pattern.finditer(content):
        level = int(m.group(1))
        text = m.group(2).strip()
        # 去掉内部可能残留的 HTML 标签
        text = re.sub(r"<[^>]+>", "", text).strip()
        if _is_page_marker(text):
            continue
        if not text:
            continue
        raw_headers.append({
            "pos": m.start(),
            "level": level,
            "text": text,
        })

    # 按位置排序（HTML 和 Markdown 标题混合时保持文档顺序）
    raw_headers.sort(key=lambda x: x["pos"])

    # 构建层级路径
    stack: list[str] = []
    for h in raw_headers:
        while len(stack) >= h["level"]:
            stack.pop()
        stack.append(h["text"])
        h["hierarchy"] = list(stack)

    return raw_headers


def _is_page_marker(text: str) -> bool:
    """判断是否为分页标记标题（第 N 页 / Page N）"""
    if re.match(r"第\s*\d+\s*页$", text):
        return True
    if re.match(r"Page\s*\d+$", text, re.IGNORECASE):
        return True
    return False

    # 构建层级路径
    # 用栈记录当前各级标题的文本
    stack: list[str] = []
    hierarchy: list[str] = []
    for h in raw_headers:
        # 栈只保留同级或更高级的标题
        while len(stack) >= h["level"]:
            stack.pop()
        stack.append(h["text"])
        h["hierarchy"] = list(stack)
        hierarchy = list(stack)

    # 第一次循环后 hierarchy 指向最后一颗子树，不影响
    # 但需要确保每个 h 都拿到自己的 hierarchy
    # 重新做一次
    stack = []
    for h in raw_headers:
        while len(stack) >= h["level"]:
            stack.pop()
        stack.append(h["text"])
        h["hierarchy"] = list(stack)

    return raw_headers


# ═══════════════════════════════════════════════
#  纯文本分块（按段落/句子边界）
# ═══════════════════════════════════════════════

def _split_plain_text(
    content: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """
    纯文本分块

    优先级: 空行(\n\n) → 换行(\n) → 句号(。) → 感叹号(！) → 问号(？) → 逗号(；)
    保证每个 chunk 在 chunk_size 以内，相邻 chunk 有 overlap 字符重叠
    """
    sub_texts = _recursive_split(
        content,
        chunk_size=chunk_size,
        overlap=overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；"],
    )
    return [
        Chunk(text=t, metadata={"header": "", "header_path": "", "level": 0})
        for t in sub_texts if t.strip()
    ]


# ═══════════════════════════════════════════════
#  递归分块引擎（两种策略共用）
# ═══════════════════════════════════════════════

def _recursive_split(
    text: str,
    chunk_size: int,
    overlap: int,
    separators: list[str],
) -> list[str]:
    """
    递归文本切分

    1. 如果 text <= chunk_size，直接返回
    2. 否则按第一个分隔符切分
    3. 如果切出的片段仍然 > chunk_size，用下一个分隔符递归
    4. 如果所有分隔符用完仍 > chunk_size，按 chunk_size 硬切
    5. 相邻片段之间保留 overlap 字符的重叠

    参数:
        text:       待切分文本
        chunk_size: 目标大小（字符数）
        overlap:    重叠字符数
        separators: 分隔符优先级列表（从高到低）

    返回:
        切分后的文本片段列表
    """
    # 基本情况：文本已够短
    if len(text) <= chunk_size:
        return [text]

    # 没有可用分隔符 → 硬切
    if not separators:
        return _hard_split(text, chunk_size, overlap)

    sep = separators[0]
    remaining_seps = separators[1:]

    # 用当前分隔符切分
    # re.escape 处理字符串中的特殊字符
    parts = re.split(re.escape(sep), text)

    # 如果分隔符没切出超过 1 段（说明文本中没有这个分隔符）→ 试下一个
    if len(parts) <= 1:
        return _recursive_split(text, chunk_size, overlap, remaining_seps)

    # 重组：确保每个片段不超过 chunk_size
    merged = _merge_parts(parts, sep, chunk_size)

    # 对每个合并后的片段递归
    result = []
    for segment in merged:
        if len(segment) <= chunk_size:
            result.append(segment)
        else:
            result.extend(_recursive_split(segment, chunk_size, overlap, remaining_seps))

    # 添加 overlap
    return _apply_overlap(result, overlap, chunk_size)


def _merge_parts(parts: list[str], separator: str, chunk_size: int) -> list[str]:
    """
    将切分后的片段合并，保证每个合并块不超过 chunk_size

    例如用 \n\n 切分出多个段落，将小段落合并到邻近段落中
    """
    merged = []
    current = ""

    for part in parts:
        part_stripped = part.strip()
        if not part_stripped:
            continue
        # 尝试加入当前累积块
        candidate = current + separator + part_stripped if current else part_stripped
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                merged.append(current)
            current = part_stripped

    if current:
        merged.append(current)

    return merged


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    最后手段：按 chunk_size 硬切字符

    尽可能在段落边界（\n）或句子边界（。！？）处下刀，
    找不到边界时才在字符位置硬切。
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break

        # 回头找最佳切分点
        cut = _find_best_cut(text, start, end)
        chunk = text[start:cut].strip()
        if chunk:
            chunks.append(chunk)

        # 下一个 start 往前退 overlap，保证上下文衔接
        start = max(cut - overlap, cut - chunk_size // 2)

    return chunks


def _find_best_cut(text: str, start: int, end: int) -> int:
    """
    在 [start, end] 范围内找最佳切分点

    优先级:
      1. \n\n（段落边界）
      2. \n（行边界）
      3. 。！？（句子边界）
      4. ，；、（逗号边界）
      5. 直接 end（硬切）
    """
    region = text[start:end + 10]  # 多看 10 个字符

    for sep in ["\n\n", "\n", "。", "！", "？", "，", "；", "、"]:
        # 从 end 向前找最后一个分隔符
        pos = -1
        idx = 0
        while True:
            found = region.find(sep, idx)
            if found == -1:
                break
            if found <= chunk_size:
                pos = found
            idx = found + 1
            if idx > chunk_size + len(sep):
                break

        if pos != -1:
            return start + pos + len(sep)

    return min(end, len(text))


def _apply_overlap(chunks: list[str], overlap: int, chunk_size: int = 600) -> list[str]:
    """
    相邻 chunk 之间添加重叠字符：

    第 1 段:  [0:chunk_size]
    第 2 段:  [chunk_size-overlap : 2*chunk_size-overlap]
    第 3 段:  [2*chunk_size-2*overlap : 3*chunk_size-2*overlap]
    """
    if len(chunks) <= 1 or overlap <= 0:
        return chunks

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev = result[-1]
        curr = chunks[i]

        # 从前一个 chunk 尾部取 overlap 个字作为前缀
        prefix = prev[-overlap:] if len(prev) >= overlap else prev
        merged = prefix + curr
        # 如果合并后超过 chunk_size，不追加 prefix，只用 curr
        if len(merged) > chunk_size:
            result.append(curr)
        else:
            result.append(merged)

    return result



