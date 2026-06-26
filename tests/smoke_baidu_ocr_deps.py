"""
冒烟脚本 5：百度 OCR 依赖安装验证
无需 token，仅检测 requests 库
"""
try:
    import requests
    print(f"✅ requests 已安装，版本: {requests.__version__}")
except ImportError:
    print("❌ requests 未安装")
