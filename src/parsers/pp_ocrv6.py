"""
百度 PP-OCRv6 异步 PDF 解析模块（v2 - 已根据官方文档修正）
官方示例: https://paddleocr.aistudio-app.com/api/v2/ocr/jobs
关键差异:
  1. optionalPayload 字段名：useTextlineOrientation（不是 useChartRecognition）
  2. 返回结构：result["ocrResults"]（不是 layoutParsingResults）
  3. ocrResults 每项有 ocrImage 字段（识别结果图 URL）
"""
import os
import json
import time
import requests


JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
DEFAULT_MODEL = "PP-OCRv6"


def parse_pdf_via_ppocrv6(
    pdf_path: str,
    token: str = None,
    model: str = DEFAULT_MODEL,
    output_image_dir: str = "outputs/parsed/ppocrv6_images",
) -> dict:
    """
    通过百度 PP-OCRv6 异步解析 PDF → 纯文本 + 识别图

    返回:
        {
            "full_text": str,         # 合并后的纯文本
            "md_lines": int,          # 非空行数
            "md_chars": int,          # 字符数
            "elapsed_sec": float,     # 总耗时
            "total_pages": int,       # PDF 总页数
            "image_count": int,       # 识别结果图数量
            "model": str,             # 模型名
            "pages": list,            # 每页 OCR 文本列表
        }
    """
    if token is None:
        token = os.environ.get("OCR-TOKEN", "").strip()
        if not token:
            raise EnvironmentError("环境变量 OCR-TOKEN 未设置")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    # === Step 1: 提交任务（按官方文档格式）===
    headers = {"Authorization": f"bearer {token}"}
    # 官方示例的 optional_payload（修正：useTextlineOrientation 而非 useChartRecognition）
    optional_payload = {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useTextlineOrientation": False,
    }

    print(f"📤 提交任务: {os.path.basename(pdf_path)}")
    print(f"   模型: {model}")

    with open(pdf_path, "rb") as f:
        files = {"file": f}
        data = {
            "model": model,
            "optionalPayload": json.dumps(optional_payload),
        }
        resp = requests.post(JOB_URL, headers=headers, data=data, files=files, timeout=60)

    print(f"   HTTP 状态: {resp.status_code}")
    if resp.status_code != 200:
        raise RuntimeError(f"提交失败 (HTTP {resp.status_code}): {resp.text[:500]}")

    job_id = resp.json()["data"]["jobId"]
    print(f"✅ Job ID: {job_id}")
    print(f"⏳ 开始轮询...")

    # === Step 2: 轮询 ===
    t_start = time.perf_counter()
    poll_count = 0
    jsonl_url = ""
    total_pages = 0

    while True:
        poll_count += 1
        r = requests.get(f"{JOB_URL}/{job_id}", headers=headers, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"轮询失败: {r.text[:300]}")

        state = r.json()["data"]["state"]

        if state == "pending":
            print(f"  [{poll_count}] pending")
        elif state == "running":
            prog = r.json()["data"].get("extractProgress", {})
            tp = prog.get("totalPages", 0)
            ep = prog.get("extractedPages", 0)
            print(f"  [{poll_count}] running ({ep}/{tp} 页)")
        elif state == "done":
            prog = r.json()["data"]["extractProgress"]
            total_pages = prog.get("extractedPages", total_pages)
            elapsed = time.perf_counter() - t_start
            print(f"✅ 完成!")
            print(f"   总页数: {total_pages}")
            print(f"   总耗时: {elapsed:.2f}s (轮询 {poll_count} 次)")
            jsonl_url = r.json()["data"]["resultUrl"]["jsonUrl"]
            break
        elif state == "failed":
            err = r.json()["data"].get("errorMsg", "未知")
            raise RuntimeError(f"任务失败: {err}")

        time.sleep(5)  # 官方示例用 5 秒

    # === Step 3: 下载结果 ===
    print(f"📥 下载 jsonl 结果...")
    md_resp = requests.get(jsonl_url, timeout=30)
    md_resp.raise_for_status()

    # === Step 4: 解析 + 下载图片 ===
    os.makedirs(output_image_dir, exist_ok=True)

    pages_text = []
    image_count = 0

    for line_num, line in enumerate(md_resp.text.strip().split("\n"), 1):
        if not line.strip():
            continue
        result = json.loads(line)["result"]

        # 修正：官方返回的字段是 ocrResults（不是 layoutParsingResults）
        ocr_results = result.get("ocrResults", [])
        for page_idx, res in enumerate(ocr_results):
            page_num = line_num  # 一行 = 一页

            # 1. 下载识别结果图（可选）
            image_url = res.get("ocrImage")
            if image_url:
                try:
                    img_resp = requests.get(image_url, timeout=15)
                    if img_resp.status_code == 200:
                        img_path = os.path.join(output_image_dir, f"page_{page_num:03d}.jpg")
                        with open(img_path, "wb") as f:
                            f.write(img_resp.content)
                        image_count += 1
                except Exception as e:
                    print(f"   ⚠️  第 {page_num} 页图片下载失败: {e}")

            # 2. 提取文字（按官方结构尝试多种字段）
            page_text = _extract_page_text(res)
            pages_text.append(f"# 第 {page_num} 页\n\n{page_text}")

    full_text = "\n\n---\n\n".join(pages_text)
    md_lines = len([l for l in full_text.split("\n") if l.strip()])

    return {
        "full_text": full_text,
        "full_markdown": full_text,  # 别名保持兼容
        "md_lines": md_lines,
        "md_chars": len(full_text),
        "elapsed_sec": elapsed,
        "total_pages": total_pages,
        "image_count": image_count,
        "model": model,
        "pages": pages_text,
    }


def _extract_page_text(res: dict) -> str:
    """
    提取单页文字 - 容错处理官方返回结构变化
    """
    # 方式 1：尝试 layoutParsingResults（v2 多模态）
    if "layoutParsingResults" in res:
        parts = []
        for item in res["layoutParsingResults"]:
            if "markdown" in item and "text" in item["markdown"]:
                parts.append(item["markdown"]["text"])
        return "\n\n".join(parts)

    # 方式 2：尝试 ocrResults + prunedResult（v1 经典）
    if "prunedResult" in res:
        return res["prunedResult"]

    # 方式 3：尝试 rec_texts（paddleocr 原生）
    if "rec_texts" in res:
        return "\n".join(res["rec_texts"])

    # 方式 4：尝试 texts
    if "texts" in res:
        return "\n".join(res["texts"])

    # 兜底：打印原始结构
    return f"[未识别的返回结构]\n{json.dumps(res, ensure_ascii=False, indent=2)[:500]}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python pp_ocrv6.py <pdf_path>")
        sys.exit(1)
    pdf = sys.argv[1]
    result = parse_pdf_via_ppocrv6(pdf)
    out_path = "outputs/parsed/pp_ocrv6_result.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result["full_markdown"])
    print(f"\n💾 Markdown 已保存: {out_path}")
