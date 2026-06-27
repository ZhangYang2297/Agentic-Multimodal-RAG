# 分块模块
# 从 .py 文件自动检测所有公开函数并导出

from .splitter import split_document, Chunk

__all__ = ["split_document", "Chunk"]
