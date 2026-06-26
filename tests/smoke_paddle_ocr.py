import time
from paddleocr import PaddleOCR

# ----- 开始计时 -----
start_total = time.perf_counter()

# 初始化 OCR（可能会加载模型，耗时较长）
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)

# 本地图片路径
img_path = r"C:\Users\admin\Documents\Agentic-Multimodal-RAG\data\raw\test_ocr.png"

# ----- 预测计时 -----
start_predict = time.perf_counter()
result = ocr.predict(img_path)
predict_time = time.perf_counter() - start_predict

# 处理并输出结果
for res in result:
    res.print()                # 打印识别内容
    res.save_to_img("output")  # 保存可视化图片
    res.save_to_json("output") # 保存 JSON 结果

# ----- 总耗时计算 -----
total_time = time.perf_counter() - start_total

# 打印耗时信息
print("\n" + "=" * 40)
print(f"⏱️  预测耗时: {predict_time:.2f} 秒")
print(f"⏱️  总耗时（含模型加载）: {total_time:.2f} 秒")
print("=" * 40)