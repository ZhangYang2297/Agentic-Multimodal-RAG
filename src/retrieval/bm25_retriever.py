"""
BM25Retriever - 关键词检索

基于 jieba 分词 + BM25Okapi 纯算法实现。
不需要模型、不需要下载、不需要 API。
"""

import os
import math
import jieba
from collections import Counter


class BM25Retriever:
    """BM25Okapi 纯算法检索器"""
    
    def __init__(self):
        self._corpus = []
        self._tokenized = []
        self._doc_freq = Counter()
        self._total_docs = 0
        self._avg_doc_len = 1.0
        self._fitted = False
        self._k1 = 1.5
        self._b = 0.75

    def _tokenize(self, text):
        return [w.strip() for w in jieba.lcut(text) if w.strip()]

    def add_documents(self, documents):
        for doc in documents:
            tokens = self._tokenize(doc)
            self._corpus.append(doc)
            self._tokenized.append(tokens)
            for term in set(tokens):
                self._doc_freq[term] += 1
        self._total_docs = len(self._corpus)
        total_len = sum(len(t) for t in self._tokenized)
        self._avg_doc_len = total_len / self._total_docs if self._total_docs else 1.0
        self._fitted = True

    def fit(self, documents):
        self._corpus = []
        self._tokenized = []
        self._doc_freq = Counter()
        self.add_documents(documents)

    def search(self, query, top_k=20):
        if not self._fitted or not self._corpus:
            return []
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        scores = []
        for i, doc_tokens in enumerate(self._tokenized):
            doc_len = len(doc_tokens)
            score = 0.0
            doc_counter = Counter(doc_tokens)
            for term in query_tokens:
                tf = doc_counter.get(term, 0)
                if tf == 0:
                    continue
                df = self._doc_freq.get(term, 0)
                if df == 0:
                    continue
                idf = math.log(1 + (self._total_docs - df + 0.5) / (df + 0.5))
                tf_norm = (tf * (self._k1 + 1)) / (tf + self._k1 * (1 - self._b + self._b * doc_len / self._avg_doc_len))
                score += idf * tf_norm
            scores.append(score)
        indexed = [(i, s) for i, s in enumerate(scores) if s > 0]
        indexed.sort(key=lambda x: x[1], reverse=True)
        indexed = indexed[:top_k]
        return [{"document": self._corpus[idx], "score": round(s, 4), "rank": r+1} for r, (idx, s) in enumerate(indexed)]

    @property
    def doc_count(self):
        return self._total_docs

    def __repr__(self):
        return f"BM25Retriever(docs={self._total_docs}, fitted={self._fitted})"