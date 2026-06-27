"""Pipeline - Document processing orchestrator

Flow: Load -> Clean -> Split -> Registry

Supports incremental update:
  - new:       full pipeline
  - skip:      MD5 unchanged, skip
  - reindex:   MD5 changed, re-index (version+1)
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.processing.document_registry import DocumentRegistry, generate_doc_id, compute_md5, detect_format_from_ext
from src.loaders.document_loader import load_document
from src.chunking.splitter import split_document
from src.vectorstore.chroma_store import ChromaStore


class Pipeline:
    """Document processing orchestrator with incremental update support."""

    def __init__(
        self,
        registry_path: str = "outputs/registry/documents.json",
        chunk_size: int = 600,
        overlap: int = 100,
        vectorstore: Optional[ChromaStore] = None,
        auto_index: bool = True,
    ):
        self.registry = DocumentRegistry(registry_path=registry_path)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.auto_index = auto_index
        self.vectorstore = vectorstore

    def process_file(
        self,
        file_path: str,
        ocr_engine: str = "auto",
        clean_md: bool = True,
        verbose: bool = True,
    ) -> dict:
        """Process a single file with incremental update."""
        if not os.path.exists(file_path):
            return {"action": "error", "message": "File not found: " + file_path}

        t_start = time.perf_counter()
        embed_elapsed = 0
        doc_id = generate_doc_id(file_path)
        doc_name = os.path.basename(file_path)
        current_md5 = compute_md5(file_path)

        # Check registry for action
        check = self.registry.check_file(file_path)

        if check["action"] == "skip":
            if verbose:
                print("  [SKIP] " + doc_name + " - MD5 unchanged")
            return {
                "action": "skip",
                "doc_id": doc_id,
                "doc_name": doc_name,
                "md5": current_md5,
                "version": check["current_version"],
                "chunks": [],
                "chunk_count": 0,
                "doc_format": check["record"]["doc_format"],
                "elapsed_sec": 0,
                "embed_elapsed": 0,
                "message": check["message"],
            }

        # Load document
        try:
            content = load_document(file_path, ocr_engine=ocr_engine, clean_markdown=clean_md)
        except Exception as e:
            return {"action": "error", "doc_id": doc_id, "embed_elapsed": 0, "message": "Load failed: " + str(e)}

        # Split with document metadata
        version = check["current_version"] + 1
        doc_format = detect_format_from_ext(file_path)

        chunks = split_document(
            content,
            file_path=file_path,
            chunk_size=self.chunk_size,
            overlap=self.overlap,
            doc_id=doc_id,
            doc_name=doc_name,
            md5=current_md5,
            version=version,
        )

        # If reindex, deprecate old version chunks in vectorstore
        if check["action"] == "reindex" and self.vectorstore is not None:
            old_v = check["current_version"]
            deprecated = self.vectorstore.deprecate_version(doc_id, old_v)
            if verbose and deprecated:
                print("  Deprecated old v" + str(old_v) + ": " + str(deprecated) + " chunks")

        # Register to registry
        self.registry.register(
            file_path=file_path,
            md5=current_md5,
            doc_format=doc_format,
            chunk_count=len(chunks),
            version=version,
        )

        # Embed and store in vectorstore
        if self.vectorstore is not None and chunks:
            t_embed = time.perf_counter()
            n = self.vectorstore.add_chunks(chunks)
            embed_elapsed = time.perf_counter() - t_embed

        elapsed = time.perf_counter() - t_start

        msg = check["message"]
        if verbose:
            print("  " + str(len(chunks)) + " chunks | v" + str(version) + " | " + "{:.2f}s".format(elapsed))

        return {
            "action": check["action"],
            "doc_id": doc_id,
            "doc_name": doc_name,
            "md5": current_md5,
            "version": version,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "doc_format": doc_format,
            "elapsed_sec": round(elapsed, 2),
            "embed_elapsed": round(embed_elapsed, 2) if self.vectorstore and chunks else 0,
            "message": msg + ", v" + str(version) + ", " + str(len(chunks)) + " chunks",
        }

    def process_batch(self, file_paths, ocr_engine='auto', clean_md=True, verbose=True, max_workers=4):
        """Batch process with ThreadPoolExecutor. Single file failure is isolated."""
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self.process_file, fp, ocr_engine=ocr_engine, clean_md=clean_md, verbose=verbose): fp
                for fp in file_paths
            }
            for future in as_completed(future_map):
                fp = future_map[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({"action": "error", "file_path": fp, "message": str(e)})
        # Restore original order
        order = {fp: i for i, fp in enumerate(file_paths)}
        results.sort(key=lambda r: order.get(r.get("file_path", r.get("doc_name", "")), 999))
        return results
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <file_path> [ocr_engine]")
        sys.exit(1)
    file_path = sys.argv[1]
    engine = sys.argv[2] if len(sys.argv) > 2 else "auto"
    pipeline = Pipeline()
    result = pipeline.process_file(file_path, ocr_engine=engine)
    print("Result:", result["action"], "|", result.get("message", ""))