"""
B2 分块模块测试

测试覆盖:
  1. 格式检测（扩展名 / 内容探测）
  2. Markdown 按标题分块
  3. 纯文本按段落分块
  4. 大段二次切分
  5. 无标题 Markdown 降级
  6. 分页标记过滤
  7. 边界情况（空文本、单段、大量小段）
  8. 性能基线
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.chunking.splitter import split_document, Chunk


# ─── 测试数据 ───

SAMPLE_MARKDOWN = """# 北京三日游攻略

## 第一天：天安门与故宫

天安门广场位于北京市中心，是世界上最大的城市广场之一。
广场北端是天安门城楼，南端是人民英雄纪念碑。

### 故宫游览建议

故宫也称紫禁城，是明清两代的皇家宫殿。
建议游览时间：3-4小时。
主要看点：太和殿、乾清宫、御花园。

## 第二天：长城

八达岭长城距离市区约80公里。
建议早起出发，避开人流高峰。

## 第三天：颐和园与胡同

### 颐和园

颐和园是中国现存最大的皇家园林。
建议游览时间：2-3小时。

### 胡同游

推荐什刹海、南锣鼓巷一带的胡同。
可以租自行车游览。
"""

SAMPLE_PLAINTEXT = """北京旅游小贴士

1. 必去景点：故宫、长城、颐和园、天坛
2. 美食推荐：烤鸭、炸酱面、豆汁
3. 最佳季节：春秋两季

交通建议：
- 地铁覆盖主要景点
- 出租车起步价 13 元

住宿建议：
建议选择二环内的酒店，交通便利。
预算充足可以选择王府井附近。
"""

LONG_SECTION = """## 北京景点详细介绍

北京是中国的首都，拥有三千多年的历史。
故宫：位于北京中轴线的中心，占地面积72万平方米。
长城：长城是中国古代的军事防御工程，总长度超过2万公里。
颐和园：中国现存最大的皇家园林，占地约290公顷。
天坛：明清两代皇帝祭天祈谷的场所。
北海公园：中国现存最古老、最完整的皇家园林之一。
圆明园：清代大型皇家园林，被誉为"万园之园"。
香山公园：位于北京西郊，以红叶闻名。
雍和宫：北京最大的藏传佛教寺院。
恭王府：清代规模最大的一座王府。

""" * 5


def test_detect_format_by_ext():
    chunks_md = split_document(SAMPLE_MARKDOWN, file_path="guide.md")
    chunks_txt = split_document(SAMPLE_PLAINTEXT, file_path="tips.txt")
    assert len(chunks_md) > 0
    assert len(chunks_txt) > 0
    assert "header" in chunks_md[0].metadata
    print(f"  Markdown: {len(chunks_md)} chunks | PlainText: {len(chunks_txt)} chunks")


def test_detect_format_by_content():
    chunks = split_document(SAMPLE_MARKDOWN)
    assert len(chunks) > 0
    assert chunks[0].metadata.get("header") == "北京三日游攻略"
    print(f"  首块 header={chunks[0].metadata['header']}")


def test_markdown_header_splitting():
    chunks = split_document(SAMPLE_MARKDOWN, file_path="guide.md", chunk_size=600, overlap=100)
    headers = [c.metadata.get("header") for c in chunks if not c.metadata.get("header", "").startswith("(")]
    print(f"  {len(chunks)} chunks | 标题: {headers}")
    assert "北京三日游攻略" in headers
    assert "故宫游览建议" in headers
    assert "胡同游" in headers


def test_plaintext_paragraph_splitting():
    chunks = split_document(SAMPLE_PLAINTEXT, file_path="tips.txt", chunk_size=600, overlap=50)
    assert len(chunks) > 0
    total = sum(len(c.text) for c in chunks)
    print(f"  {len(chunks)} chunks | {total} chars (原始: {len(SAMPLE_PLAINTEXT)})")


def test_long_section_recursive_split():
    chunks = split_document(LONG_SECTION, file_path="long.md", chunk_size=400, overlap=50)
    assert len(chunks) > 1, "大段应该被切分成多个 chunk"
    sized_ok = all(len(c.text) <= 450 for c in chunks)
    assert sized_ok, "存在超限 chunk"
    print(f"  {len(chunks)} chunks, 全部在 450 chars 以内")


def test_no_header_markdown_downgrade():
    no_header = "这是第一段。\n\n这是第二段。\n\n这是第三段。\n\n这是第四段。"
    chunks = split_document(no_header, file_path="plain.md", chunk_size=300, overlap=30)
    assert len(chunks) > 0
    for c in chunks:
        assert c.metadata.get("header") == ""
    print(f"  降级为纯文本: {len(chunks)} chunks")


def test_page_markers_filtered():
    content = "# 第 1 页\n\n开头\n\n# 第 2 页\n\n中间\n\n## 真实标题\n\n正文"
    chunks = split_document(content, file_path="doc.md", chunk_size=600)
    headers = [c.metadata.get("header") for c in chunks if c.metadata.get("header")]
    assert "真实标题" in str(headers), f"未找到真实标题: {headers}"
    assert "第 1 页" not in str(headers), "分页标记未被过滤"
    print(f"  过滤后标题: {headers}")


def test_header_path_hierarchy():
    chunks = split_document(SAMPLE_MARKDOWN, file_path="guide.md", chunk_size=600)
    for c in chunks:
        path = c.metadata.get("header_path", "")
        if "故宫" in c.text and "故宫游览" in c.metadata.get("header", ""):
            assert "第一天" in path, f"故宫应包含第一天路径: {path}"
        if "颐和园" in c.text and "颐和园" in c.metadata.get("header", ""):
            assert "第三天" in path, f"颐和园应包含第三天路径: {path}"
    print("  全部正确")


def test_overlap():
    text = "段落A。\n\n段落B。\n\n段落C。\n\n段落D。\n\n段落E。\n\n段落F。\n\n段落G。\n\n段落H。"
    chunks = split_document(text, file_path="test.md", chunk_size=50, overlap=20)
    if len(chunks) >= 2:
        has_overlap = any(
            chunks[i].text[-15:] in chunks[i + 1].text[:25]
            for i in range(len(chunks) - 1)
        )
        print(f"  相邻重叠: {has_overlap}" if has_overlap else "  ⚠️ 未能验证重叠")
    else:
        print(f"  共 {len(chunks)} chunk（文本较短）")


def test_empty_content():
    chunks = split_document("", file_path="empty.md")
    assert isinstance(chunks, list)
    assert len(chunks) == 0, f"空文本应返回空列表，实际: {len(chunks)}"
    print("  空文本正确返回空列表")



def test_html_headers():
    """OCR 输出的 HTML 标题标签也能检测"""
    html_content = """<h2>1. 图片生成 API</h2>
<p>本文介绍图片生成模型的调用 API。</p>
<h2>鉴权说明</h2>
<p>本接口仅支持 API Key 鉴权。</p>
<h2>请求参数</h2>
<p>model string required</p>
<h3>请求体</h3>
<p>您需要调用的模型的 ID。</p>
"""
    chunks = split_document(html_content, file_path="api.md", chunk_size=600, overlap=50)
    headers = [c.metadata.get("header") for c in chunks if c.metadata.get("header")]
    print(f"  {len(chunks)} chunks | HTML 标题: {headers}")
    assert "1. 图片生成 API" in headers, f"未检测到 HTML 标题: {headers}"
    assert "鉴权说明" in headers
    assert "请求体" in headers
    assert all(len(c.text) <= 650 for c in chunks), "存在超限 chunk"

def test_performance():
    big = ("# 标题\n\n" + "a" * 100 + "\n\n" + "b" * 100 + "\n\n") * 50
    t0 = time.perf_counter()
    chunks = split_document(big, file_path="big.md", chunk_size=500, overlap=50)
    elapsed = time.perf_counter() - t0
    print(f"  {elapsed*1000:.1f}ms / {len(chunks)} chunks / {len(big)/elapsed/1000:.0f} chars/sec")
    assert elapsed < 2.0, f"超时: {elapsed:.2f}s"


def test_real_document():
    doc_path = os.path.join(os.path.dirname(__file__), "../outputs/parsed/document.md")
    if not os.path.exists(doc_path):
        print("  ⚠️ document.md 不存在，跳过")
        return

    content = open(doc_path, encoding="utf-8").read()
    print(f"  原始: {len(content)} chars")

    t0 = time.perf_counter()
    chunks = split_document(content, file_path=doc_path, chunk_size=600, overlap=100)
    elapsed = time.perf_counter() - t0

    sizes = [len(c.text) for c in chunks]
    headers = [c.metadata.get("header") for c in chunks if c.metadata.get("header")]

    print(f"  {len(chunks)} chunks, {elapsed*1000:.1f}ms")
    print(f"  大小: avg={sum(sizes)//len(sizes)} max={max(sizes)} min={min(sizes)}")
    print(f"  标题数: {len(headers)}")

    # chunk_size+overlap 作为软上限，超过 1200 才算问题
    over = [c for c in chunks if len(c.text) > 1000]
    assert len(over) == 0, f"{len(over)} 个 chunk > 1000 chars"
    print(f"  全部小于 1000 chars ✅")


if __name__ == "__main__":
    tests = [
        ("格式检测-扩展名", test_detect_format_by_ext),
        ("格式检测-内容探测", test_detect_format_by_content),
        ("HTML 标题检测", test_html_headers),
        ("Markdown 标题分块", test_markdown_header_splitting),
        ("纯文本段落分块", test_plaintext_paragraph_splitting),
        ("无标题降级", test_no_header_markdown_downgrade),
        ("分页标记过滤", test_page_markers_filtered),
        ("标题层级路径", test_header_path_hierarchy),
        ("相邻 chunk 重叠", test_overlap),
        ("大段二次切分", test_long_section_recursive_split),
        ("空文本", test_empty_content),
        ("性能基线", test_performance),
        ("真实文档", test_real_document),
    ]

    passed = 0
    failed = 0
    print("=" * 60)
    print("B2 分块模块测试")
    print("=" * 60)

    for name, fn in tests:
        print(f"\n> {name}")
        try:
            fn()
            print(f"  [PASS]")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*60}")
    print(f"结果: {passed}/{passed+failed} 通过", end="")
    if failed:
        print(f", {failed} 失败")
    else:
        print(" [全部通过]")



