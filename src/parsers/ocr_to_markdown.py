"""
A2-Step2：用 qwen3.5-ocr 把每张图片识别成 Markdown
支持批量处理，统计耗时和 token
"""
import os
import base64
import time
from pathlib import Path
from openai import OpenAI


BASE_URL = "https://llm-mqq0qggh7ed4t502.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
OCR_MODEL = "qwen3.5-ocr"


def _get_client() -> OpenAI:
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise EnvironmentError("环境变量 DASHSCOPE_API_KEY 未设置")
    return OpenAI(base_url=BASE_URL, api_key=api_key)


def _encode_image(img_path: str) -> str:
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def ocr_single_image(
    img_path: str,
    client: OpenAI = None,
) -> dict:
    """单张图片 OCR"""
    if client is None:
        client = _get_client()

    img_b64 = _encode_image(img_path)

    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=OCR_MODEL,
        messages=[{
            "role": "user",
            "content": [{
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            }]
        }]
    )
    elapsed = time.perf_counter() - t0

    usage = resp.usage
    return {
        "image": img_path,
        "markdown": resp.choices[0].message.content,
        "elapsed_sec": round(elapsed, 2),
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }


def images_to_markdown(
    image_paths: list[str],
    output_path: str = "outputs/parsed/document.md",
) -> dict:
    """批量 OCR 多张图片，合并为单个 Markdown 文档"""
    client = _get_client()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"🔍 开始 OCR 识别，共 {len(image_paths)} 张图片")
    print(f"   模型: {OCR_MODEL}")
    print("=" * 60)

    pages = []
    full_md_parts = []

    total_t0 = time.perf_counter()

    for i, img_path in enumerate(image_paths, 1):
        print(f"\n📖 第 {i}/{len(image_paths)} 页: {os.path.basename(img_path)}")

        result = ocr_single_image(img_path, client)
        pages.append(result)

        full_md_parts.append(f"\n\n---\n\n# 第 {i} 页\n\n")
        full_md_parts.append(result["markdown"])

        print(f"   ⏱️  耗时: {result['elapsed_sec']}s")
        print(f"   📊 Token: prompt={result['prompt_tokens']} "
              f"completion={result['completion_tokens']} total={result['total_tokens']}")
        print(f"   📝 前 80 字: {result['markdown'][:80]}...")

    total_elapsed = time.perf_counter() - total_t0
    total_tokens = sum(p["total_tokens"] for p in pages)

    full_md = "".join(full_md_parts)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_md)

    summary = {
        "output_path": output_path,
        "total_pages": len(image_paths),
        "total_elapsed_sec": round(total_elapsed, 2),
        "total_tokens": total_tokens,
        "avg_tokens_per_page": round(total_tokens / len(image_paths), 1),
        "pages": pages,
    }

    print("\n" + "=" * 60)
    print("🎉 OCR 完成!")
    print(f"   📄 输出文件: {output_path}")
    print(f"   ⏱️  总耗时: {total_elapsed:.2f}s")
    print(f"   📊 总 Token: {total_tokens}")
    print(f"   📊 平均每页: {total_tokens // len(image_paths)} token")

    return summary


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python ocr_to_markdown.py <images_dir> [output.md]")
        sys.exit(1)
    images_dir = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "outputs/parsed/document.md"
    imgs = sorted([
        os.path.join(images_dir, f)
        for f in os.listdir(images_dir)
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    ])
    images_to_markdown(imgs, output)
