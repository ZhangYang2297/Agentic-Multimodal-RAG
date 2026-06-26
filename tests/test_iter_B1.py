"""
B1 验收测试：多格式统一加载器
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.loaders import (
    load_document,
    load_documents_batch,
    detect_format,
    is_supported,
    SUPPORTED_EXTS,
)


def create_test_txt():
    txt_path = "data/raw/test_travel_tips.txt"
    content = """北京旅游小贴士

1. 必去景点：故宫、长城、颐和园、天坛
2. 美食推荐：烤鸭、炸酱面、豆汁
3. 最佳季节：春秋两季

交通建议：
- 地铁覆盖主要景点
- 出租车起步价 13 元
"""
    Path(txt_path).parent.mkdir(parents=True, exist_ok=True)
    Path(txt_path).write_text(content, encoding="utf-8")
    return txt_path


def create_test_docx():
    """创建一个真实的临时 docx 占位文件用于触发 ValueError"""
    # 使用临时目录 + 自动清理
    tmp = tempfile.NamedTemporaryFile(
        mode="wb", suffix=".docx", delete=False, prefix="test_"
    )
    tmp.write(b"fake docx content for testing")
    tmp.close()
    return tmp.name


def main():
    print("=" * 60)
    print("Iter B1 - multi-format loader")
    print("=" * 60)

    txt_path = create_test_txt()
    md_path = "outputs/parsed/sample_paddle_vl.md"

    print(f"\n[INFO] test files:")
    print(f"  txt: {txt_path}")
    print(f"  md:  {md_path}")

    # === Test 1: 常量 ===
    print(f"\n[TEST 1] module constants")
    print(f"   SUPPORTED_EXTS: {sorted(SUPPORTED_EXTS)}")
    checks_1 = {
        ".pdf supported": ".pdf" in SUPPORTED_EXTS,
        ".md supported": ".md" in SUPPORTED_EXTS,
        ".txt supported": ".txt" in SUPPORTED_EXTS,
    }
    for n, ok in checks_1.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")
    test1_ok = all(checks_1.values())

    # === Test 2: detect & is_supported ===
    print(f"\n[TEST 2] detect_format + is_supported")
    fmt_md = detect_format(md_path)
    fmt_txt = detect_format(txt_path)
    fmt_unsupported = detect_format("foo.docx")
    checks_2 = {
        "detect .md": fmt_md == ".md",
        "detect .txt": fmt_txt == ".txt",
        "detect .docx (unsupported)": fmt_unsupported == ".docx",
        "is_supported .md": is_supported(md_path),
        "is_supported .txt": is_supported(txt_path),
        "is_supported .docx (false)": not is_supported("foo.docx"),
    }
    for n, ok in checks_2.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")
    test2_ok = all(checks_2.values())

    # === Test 3: load .md ===
    print(f"\n[TEST 3] load .md")
    md_content = load_document(md_path)
    checks_3 = {
        "non-empty string": len(md_content) > 100,
        "contains content": "图片" in md_content or "API" in md_content,
        "is str type": isinstance(md_content, str),
    }
    for n, ok in checks_3.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")
    print(f"   chars: {len(md_content):,}")
    test3_ok = all(checks_3.values())

    # === Test 4: load .txt ===
    print(f"\n[TEST 4] load .txt")
    txt_content = load_document(txt_path)
    checks_4 = {
        "non-empty": len(txt_content) > 50,
        "contains expected": "故宫" in txt_content and "长城" in txt_content,
        "is str": isinstance(txt_content, str),
    }
    for n, ok in checks_4.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")
    print(f"   chars: {len(txt_content)}")
    print(f"   preview: {txt_content[:60]}...")
    test4_ok = all(checks_4.values())

    # === Test 5: 批量 ===
    print(f"\n[TEST 5] batch load (.md + .txt)")
    batch = load_documents_batch([md_path, txt_path])
    checks_5 = {
        "2 results": len(batch) == 2,
        "all success": all(r["success"] for r in batch),
        "has path field": all("path" in r for r in batch),
        "ext valid": all(r["ext"] in [".md", ".txt"] for r in batch),
    }
    for n, ok in checks_5.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")
    test5_ok = all(checks_5.values())

    # === Test 6: 错误处理 ===
    print(f"\n[TEST 6] error handling")
    checks_6 = {}

    # 6.1 不存在的文件
    try:
        load_document("nonexistent_file_xyz.md")
        checks_6["FileNotFoundError raised"] = False
    except FileNotFoundError:
        checks_6["FileNotFoundError raised"] = True

    # 6.2 不支持的格式（先创建真实 .docx 文件再测试）
    docx_path = create_test_docx()
    try:
        load_document(docx_path)
        checks_6["ValueError for unsupported"] = False
    except ValueError:
        checks_6["ValueError for unsupported"] = True
    finally:
        try:
            os.unlink(docx_path)
        except OSError:
            pass

    # 6.3 批量加载部分失败
    mixed = load_documents_batch([md_path, "missing_file_xyz.md"])
    checks_6["partial failure batch"] = (
        len(mixed) == 2
        and mixed[0]["success"]
        and not mixed[1]["success"]
        and "error" in mixed[1]
    )

    for n, ok in checks_6.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")
    test6_ok = all(checks_6.values())

    # === 总评 ===
    print("\n" + "=" * 60)
    print("[RESULT] B1 summary")
    print("=" * 60)
    all_tests = {
        "constants": test1_ok,
        "detect_format": test2_ok,
        "load .md": test3_ok,
        "load .txt": test4_ok,
        "batch load": test5_ok,
        "error handling": test6_ok,
    }
    for n, ok in all_tests.items():
        print(f"   {'OK' if ok else 'FAIL'} {n}")

    all_pass = all(all_tests.values())
    print(f"\n{'B1 PASSED' if all_pass else 'B1 NOT FULLY PASSED'}")

    print(f"\n[INFO] PDF \u8def\u5f84\u5df2\u5c01\u88c5\u5728 load_document()")
    print(f"   \u4f7f\u7528: load_document('xxx.pdf', ocr_engine='auto')")
    print(f"   \u672c\u6b21\u9a8c\u6536\u4e0d\u8c03\u7528 PDF \u8def\u5f84\uff08\u907f\u514d\u6d88\u8017 OCR \u989d\u5ea6\uff09")


if __name__ == "__main__":
    main()
