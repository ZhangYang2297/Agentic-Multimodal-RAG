"""
百度智能云 OCR 冒烟测试 - 双引擎对比
模型 1: PaddleOCR-VL-1.6  (异步任务流，PaddleOCR 官方服务)
模型 2: PP-OCRv6          (同步 REST 调用，传统 OCR)

统计：耗时 / 识别行数 / 引擎特征对比

依赖：requests 库
"""
import os
import sys
import json
import time
import base64
import requests

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"


def get_token() -> str:
    token = os.environ.get("OCR-TOKEN", "").strip()
    if not token:
        print("❌ 环境变量 OCR-TOKEN 未设置")
        sys.exit(1)
    return token


# ============================================================
#  模型 1：PaddleOCR-VL-1.6  异步任务流
# ============================================================
def test_paddleocr_vl(img_path: str, token: str) -> None:
    print("\n" + "=" * 60)
    print("🔍 模型 1: PaddleOCR-VL-1.6  （异步任务流）")
    print("=" * 60)

    headers = {"Authorization": f"bearer {token}"}
    optional_payload = {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }

    if not os.path.exists(img_path):
        print(f"❌ 图片不存在: {img_path}")
        return

    with open(img_path, "rb") as f:
        files = {"file": f}
        data = {
            "model": "PaddleOCR-VL-1.6",
            "optionalPayload": json.dumps(optional_payload),
        }
        t_submit = time.perf_counter()
        resp = requests.post(JOB_URL, headers=headers, data=data, files=files, timeout=30)
        t_submit_done = time.perf_counter()

    print(f"⏱️  提交任务耗时: {t_submit_done - t_submit:.2f}s")
    print(f"📨 HTTP 状态: {resp.status_code}")
    if resp.status_code != 200:
        print(f"❌ 提交失败: {resp.text}")
        return

    job_id = resp.json()["data"]["jobId"]
    print(f"✅ Job ID: {job_id}")
    print("⏳ 开始轮询任务状态...")

    t_start = time.perf_counter()
    poll_count = 0
    jsonl_url = ""
    while True:
        poll_count += 1
        r = requests.get(f"{JOB_URL}/{job_id}", headers=headers, timeout=30)
        if r.status_code != 200:
            print(f"❌ 轮询失败: {r.text}")
            return
        state = r.json()["data"]["state"]
        if state == "pending":
            print(f"  [{poll_count}] 状态: pending")
        elif state == "running":
            prog = r.json()["data"].get("extractProgress", {})
            tp = prog.get("totalPages", "?")
            ep = prog.get("extractedPages", "?")
            print(f"  [{poll_count}] 状态: running  ({ep}/{tp} 页)")
        elif state == "done":
            prog = r.json()["data"]["extractProgress"]
            print(f"✅ 完成! 总页数: {prog['extractedPages']}")
            print(f"   开始时间: {prog.get('startTime')}")
            print(f"   结束时间: {prog.get('endTime')}")
            jsonl_url = r.json()["data"]["resultUrl"]["jsonUrl"]
            break
        elif state == "failed":
            print(f"❌ 任务失败: {r.json()['data'].get('errorMsg')}")
            return
        time.sleep(3)

    total_elapsed = time.perf_counter() - t_start
    print(f"⏱️  处理总耗时: {total_elapsed:.2f}s  （轮询 {poll_count} 次）")

    if not jsonl_url:
        return

    print("📥 下载识别结果 jsonl...")
    r = requests.get(jsonl_url, timeout=30)
    r.raise_for_status()

    lines_out = []
    for line in r.text.strip().split("\n"):
        if not line.strip():
            continue
        result = json.loads(line)["result"]
        for res in result["layoutParsingResults"]:
            md_text = res["markdown"]["text"]
            lines_out.append(md_text)

    full_md = "\n\n".join(lines_out)
    output_dir = "outputs/ocr_results"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "paddleocr_vl_result.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_md)

    md_lines = [l for l in full_md.split("\n") if l.strip()]
    print(f"📊 识别行数: {len(md_lines)}")
    print(f"📄 输出: {out_path}")
    print("📝 识别内容（前 10 行）:")
    for i, l in enumerate(md_lines[:10], 1):
        print(f"  {i}. {l}")


# ============================================================
#  模型 2：PP-OCRv6  同步 REST
# ============================================================
def test_pp_ocrv6(img_path: str, token: str) -> None:
    print("\n" + "=" * 60)
    print("🔍 模型 2: PP-OCRv6  （同步 REST）")
    print("=" * 60)

    if not os.path.exists(img_path):
        print(f"❌ 图片不存在: {img_path}")
        return

    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/ocr"
    params = {
        "access_token": token,
        "language_type": "CHN_ENG",
        "image": img_b64,
    }

    t0 = time.perf_counter()
    try:
        r = requests.post(url, data=params, timeout=30)
        result = r.json()
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return
    elapsed = time.perf_counter() - t0

    if "error_code" in result and not result.get("words_result"):
        print(f"⏱️  耗时: {elapsed:.2f}s")
        print(f"❌ 错误: {result.get('error_code')} - {result.get('error_msg')}")
        print("   ℹ️  提示: OCR-TOKEN 可能是 PaddleOCR-VL 的 token，")
        print("          PP-OCRv6 需要百度智能云的 access_token")
        return

    lines = []
    if "words_result" in result:
        for item in result["words_result"]:
            if "words" in item:
                lines.append(item["words"])

    output_dir = "outputs/ocr_results"
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "pp_ocrv6_result.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"⏱️  耗时: {elapsed:.2f}s")
    print(f"📊 识别行数: {len(lines)}")
    print(f"📄 输出: {out_path}")
    print("📝 识别内容（前 10 行）:")
    for i, l in enumerate(lines[:10], 1):
        print(f"  {i}. {l}")


# ============================================================
#  Main
# ============================================================
def main():
    token = get_token()
    img_path = "data/raw/test_ocr.png"

    print("📷 测试图片:", img_path)
    if os.path.exists(img_path):
        print(f"📦 大小: {os.path.getsize(img_path)/1024:.1f} KB")

    test_paddleocr_vl(img_path, token)
    test_pp_ocrv6(img_path, token)

    print("\n" + "=" * 60)
    print("📊 对比汇总")
    print("=" * 60)
    print("| 模型              | 架构    | 计费单位 |")
    print("|-------------------|---------|----------|")
    print("| PaddleOCR-VL-1.6  | 异步    | 页       |")
    print("| PP-OCRv6          | 同步    | 页       |")


if __name__ == "__main__":
    main()
