"""
A2-Step1：用 PyMuPDF 把 PDF 每一页转成高清图片
为后续 OCR 提供输入
"""
import os
from pathlib import Path
import fitz  # PyMuPDF


def pdf_to_images(
    pdf_path: str,
    output_dir: str = "outputs/parsed/pages",
    dpi: int = 200,
) -> list[str]:
    """
    将 PDF 的每一页保存为 PNG 图片

    参数:
        pdf_path:   PDF 文件路径
        output_dir: 图片输出目录
        dpi:        分辨率（200 适合 OCR，300 更高清但更慢）

    返回:
        图片文件路径列表
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 不存在: {pdf_path}")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    image_paths = []

    print(f"📄 PDF 共 {len(doc)} 页，开始转图片...")

    for page_num in range(len(doc)):
        page = doc[page_num]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        img_path = os.path.join(output_dir, f"page_{page_num+1:03d}.png")
        pix.save(img_path)
        image_paths.append(img_path)
        print(f"   ✅ 第 {page_num+1} 页 -> {img_path}  ({pix.width}x{pix.height})")

    doc.close()
    print(f"🎉 共生成 {len(image_paths)} 张图片")
    return image_paths


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python pdf_to_images.py <pdf_path>")
        sys.exit(1)
    pdf_to_images(sys.argv[1])
