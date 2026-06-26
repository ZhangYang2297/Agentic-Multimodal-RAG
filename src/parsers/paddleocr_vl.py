"""
百度 PaddleOCR-VL-1.6 异步 PDF 解析模块
官方参考: https://paddleocr.aistudio-app.com/api/v2/ocr/jobs
特点:
  - 返回结构: result["layoutParsingResults"][i]["markdown"]["text"]
  - 直接产出 Markdown（含表格、图片）
  - 与 PaddleOCR-VL-1.6 接口完全一致（接口中 model 字段值不同）
"""
import os
import json
import time
import requests


JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
DEFAULT_MODEL = "PaddleOCR-VL-1.6"


def parse_pdf_via_paddleocr_vl(
    pdf_path: str,
    token: str = None,
    model: str = DEFAULT_MODEL,
    output_image_dir: str = "outputs/parsed/paddleocr_vl_images",
) -> dict:
    """
    通过百度 PaddleOCR-VL-1.6 异步解析 PDF → Markdown

    返回:
        {
            "full_markdown": str,    # 合并后的 Markdown
            "md_lines": int,
            "md_chars": int,
            "elapsed_sec": float,
            "total_pages": int,
            "image_count": int,
            "model": str,
        }
    """
    if token is None:
        token = os.environ.get("OCR-TOKEN", "").strip()
        if not token:
            raise EnvironmentError("环境变量 OCR-TOKEN 未设置")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    headers = {"Authorization": f"bearer {token}"}
    # PaddleOCR-VL 用 chart recognition
    optional_payload = {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }

    # === Step 1: 提交任务 ===
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

        time.sleep(3)

    # === Step 3: 下载结果 ===
    print(f"📥 下载 jsonl 结果...")
    md_resp = requests.get(jsonl_url, timeout=30)
    md_resp.raise_for_status()

    # === Step 4: 解析 Markdown + 下载图片 ===
    os.makedirs(output_image_dir, exist_ok=True)

    md_parts = []
    image_count = 0

    for line_num, line in enumerate(md_resp.text.strip().split("\n"), 1):
        if not line.strip():
            continue
        result = json.loads(line)["result"]
        layout_results = result.get("layoutParsingResults", [])

        for page_idx, res in enumerate(layout_results):
            # 1. 提取 Markdown 文本
            md_obj = res.get("markdown", {})
            md_text = md_obj.get("text", "")
            md_parts.append(md_text)

            # 2. 下载图片到本地
            images_dict = md_obj.get("images", {})
            for img_name, img_url in images_dict.items():
                try:
                    img_resp = requests.get(img_url, timeout=15)
                    if img_resp.status_code == 200:
                        img_path = os.path.join(output_image_dir, f"page{line_num:03d}_{img_name}")
                        with open(img_path, "wb") as f:
                            f.write(img_resp.content)
                        image_count += 1
                except Exception as e:
                    print(f"   ⚠️  图片下载失败: {e}")

    full_md = "\n\n---\n\n".join(md_parts)
    md_lines = len([l for l in full_md.split("\n") if l.strip()])

    return {
        "full_markdown": full_md,
        "md_lines": md_lines,
        "md_chars": len(full_md),
        "elapsed_sec": elapsed,
        "total_pages": total_pages,
        "image_count": image_count,
        "model": model,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python paddleocr_vl.py <pdf_path>")
        sys.exit(1)
    pdf = sys.argv[1]
    result = parse_pdf_via_paddleocr_vl(pdf)
    out_path = "outputs/parsed/paddleocr_vl_result.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result["full_markdown"])
    print(f"\n💾 Markdown 已保存: {out_path}")
