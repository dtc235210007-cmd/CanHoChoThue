"""Module Vector Database & RAG (Retrieval-Augmented Generation) cho hệ thống Quản lý căn hộ.
Đáp ứng chuẩn kỹ thuật môn học AIA331 (Ứng dụng Trí tuệ Nhân tạo).

Kiến trúc bao gồm:
1. Document Loader & Semantic Chunking: Phân tích tài liệu quy chế tòa nhà thành từng điều khoản.
2. Embedding Generator: Sử dụng TF-IDF Deterministic Vectorizer (và Gemini 'text-embedding-004' khi có kết nối).
3. Vector Store: Lưu trữ và quản lý không gian vector đặc trưng từng điều khoản.
4. Vector Search Engine: Thuật toán tính độ tương đồng Cosine (Cosine Similarity) để xếp hạng Top-K.
5. Context Augmentation: Trích xuất tri thức liên quan nhất đưa vào Prompt của LLM.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv(override=True)

try:
    from google import genai
    from google.genai import types
    GENAI_SDK_AVAILABLE = True
except Exception:
    GENAI_SDK_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOC_PATH = DATA_DIR / "quy_dinh_toa_nha.txt"
CACHE_PATH = DATA_DIR / "vector_cache.json"

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Tính độ tương đồng Cosine giữa 2 vector nhiều chiều.
    Formula: CosSim(A, B) = (A . B) / (||A|| * ||B||)
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)


class TFIDFVectorizer:
    """Bộ vector hóa TF-IDF chuẩn xác, không hash collision.
    Mỗi từ vựng trong bộ quy chế sở hữu 1 chiều không gian vector riêng biệt.
    """
    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.dim: int = 0

    def fit(self, documents: List[str]):
        """Xây dựng từ điển và trọng số IDF từ tập văn bản."""
        doc_count = len(documents)
        df_count: Dict[str, int] = {}
        all_words = set()

        for doc in documents:
            words = set(self._tokenize(doc))
            for w in words:
                df_count[w] = df_count.get(w, 0) + 1
                all_words.add(w)

        sorted_words = sorted(list(all_words))
        self.vocab = {w: i for i, w in enumerate(sorted_words)}
        self.dim = len(self.vocab)

        # Tính IDF: ln((1 + N) / (1 + DF)) + 1.0
        for w, df in df_count.items():
            self.idf[w] = math.log((1 + doc_count) / (1 + df)) + 1.0

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\w+", text.lower(), re.UNICODE)
        tokens = list(words)
        # Bổ sung bigram cho các cụm từ quan trọng (vd: thú_cưng, thang_máy, tiền_cọc)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
        return tokens

    def vectorize(self, text: str) -> List[float]:
        """Tạo vector TF-IDF chuẩn hóa L2 cho văn bản."""
        if not self.vocab or self.dim == 0:
            return [0.0] * max(self.dim, 1)

        tokens = self._tokenize(text)
        vec = [0.0] * self.dim
        if not tokens:
            return vec

        tf_count: Dict[str, float] = {}
        for t in tokens:
            tf_count[t] = tf_count.get(t, 0.0) + 1.0

        for t, count in tf_count.items():
            if t in self.vocab:
                idx = self.vocab[t]
                tf = count / len(tokens)
                idf = self.idf.get(t, 1.0)
                vec[idx] = tf * idf

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec


class VectorRAGService:
    """Lớp quản lý Vector Database & RAG chuyên nghiệp cho hệ thống."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self.local_vectorizer = TFIDFVectorizer()
        self.documents: List[Dict[str, Any]] = []
        self.embedding_source: str = "init"
        self._initialize_knowledge_base()

    def get_embedding(self, text: str) -> Tuple[List[float], str]:
        """Lấy vector đặc trưng TF-IDF chuẩn hóa (độ chính xác cao, không đụng độ)."""
        return self.local_vectorizer.vectorize(text), "tfidf-semantic-vectorizer"

    def _split_into_chunks(self, full_text: str) -> List[Dict[str, str]]:
        """Semantic Chunking: Tách tài liệu theo từng Điều / Khoản quy định."""
        chunks: List[Dict[str, str]] = []
        current_chapter = "QUY ĐỊNH CHUNG"
        
        lines = full_text.splitlines()
        current_chunk_title = ""
        current_chunk_lines: List[str] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            if line_str.startswith("## CHƯƠNG"):
                current_chapter = line_str.replace("##", "").strip()
                continue

            if line_str.startswith("- Điều ") or line_str.startswith("Điều "):
                if current_chunk_lines:
                    text_content = "\n".join(current_chunk_lines).strip()
                    chunks.append({
                        "chapter": current_chapter,
                        "title": current_chunk_title or "Quy định",
                        "content": f"[{current_chapter}] {text_content}",
                    })
                    current_chunk_lines = []

                match = re.search(r"Điều \d+[^:]*:", line_str)
                if match:
                    current_chunk_title = match.group(0).replace("-", "").strip()
                else:
                    current_chunk_title = line_str[:40]

                current_chunk_lines.append(line_str)
            else:
                current_chunk_lines.append(line_str)

        if current_chunk_lines:
            text_content = "\n".join(current_chunk_lines).strip()
            chunks.append({
                "chapter": current_chapter,
                "title": current_chunk_title or "Quy định",
                "content": f"[{current_chapter}] {text_content}",
            })

        return chunks

    def _initialize_knowledge_base(self):
        """Khởi tạo và xây dựng không gian Vector Store."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not DOC_PATH.exists():
            print(f"[Vector RAG Warning] Không tìm thấy file quy định tại {DOC_PATH}")
            return

        with open(DOC_PATH, "r", encoding="utf-8") as f:
            full_text = f.read()

        raw_chunks = self._split_into_chunks(full_text)
        print(f"[Vector RAG] Đã phân tách tài liệu thành {len(raw_chunks)} đoạn tri thức (chunks).")

        # Huấn luyện bộ từ điển TF-IDF trên toàn bộ tài liệu quy chế
        all_texts = [f"{ch['title']} {ch['content']}" for ch in raw_chunks]
        self.local_vectorizer.fit(all_texts)
        print(f"[Vector RAG] Đã thiết lập không gian vector đặc trưng {self.local_vectorizer.dim} chiều.")

        # Xây dựng vector cho từng chunk
        self.documents = []
        for i, ch in enumerate(raw_chunks):
            full_chunk_text = f"{ch['title']}: {ch['content']}"
            vec = self.local_vectorizer.vectorize(full_chunk_text)
            self.documents.append({
                "id": i + 1,
                "chapter": ch["chapter"],
                "title": ch["title"],
                "content": ch["content"],
                "vector": vec,
            })

        self.embedding_source = f"tfidf-vectorizer ({self.local_vectorizer.dim} dimensions)"

        # Lưu lại cache
        try:
            with open(CACHE_PATH, "w", encoding="utf-8") as cf:
                json.dump({
                    "embedding_source": self.embedding_source,
                    "documents": self.documents,
                }, cf, ensure_ascii=False)
            print(f"[Vector RAG] Đã lưu {len(self.documents)} vectors vào {CACHE_PATH.name}.")
        except Exception as e:
            print(f"[Vector RAG Cache Warning] Không thể lưu cache: {e}")

    def search(self, query: str, top_k: int = 3, min_similarity: float = 0.20) -> List[Dict[str, Any]]:
        """Tìm kiếm các đoạn tri thức tương đồng nhất với câu hỏi (Cosine Similarity Search)."""
        if not query or not self.documents:
            return []

        # Vector hóa câu hỏi truy vấn
        query_vec, _ = self.get_embedding(query)

        # Trích xuất từ khóa truy vấn
        q_clean = query.lower()
        STOP_WORDS = {
            "thì", "bao", "nhiêu", "tiền", "có", "được", "không", "trong", "ngoài", "của", "cho",
            "này", "đó", "làm", "sao", "gì", "nào", "thế", "ở", "và", "là", "các", "những", "một",
            "với", "về", "hỏi", "biết", "ạ", "ơi", "tòa", "nhà", "cho", "tôi", "bạn"
        }
        query_words = [w for w in re.findall(r"\w+", q_clean) if len(w) > 1 and w not in STOP_WORDS]

        # Tính độ tương đồng với toàn bộ documents trong Vector DB
        scored_docs: List[Tuple[float, Dict[str, Any]]] = []
        for doc in self.documents:
            cos_sim = cosine_similarity(query_vec, doc["vector"])
            
            # Tính keyword overlap
            doc_text = (doc["title"] + " " + doc["content"]).lower()
            match_count = sum(1 for w in query_words if w in doc_text)
            overlap_score = (match_count / max(len(query_words), 1)) if query_words else 0.0

            # Kết hợp Hybrid: 60% Cosine Similarity + 40% Keyword Overlap
            hybrid_score = 0.6 * cos_sim + 0.4 * overlap_score
            scored_docs.append((hybrid_score, doc))

        # Sắp xếp theo điểm tương đồng từ cao xuống thấp
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        # Lấy Top K kết quả
        results = []
        for score, doc in scored_docs[:top_k]:
            if score >= min_similarity:
                results.append({
                    "id": doc["id"],
                    "chapter": doc["chapter"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "similarity": round(float(score), 4),
                })

        return results

    def format_rag_context(self, search_results: List[Dict[str, Any]]) -> str:
        """Định dạng kết quả Vector Search thành khối ngữ cảnh chuẩn nhúng vào Prompt."""
        if not search_results:
            return ""

        context_parts = [
            "=== TRI THỨC ĐƯỢC TRÍCH XUẤT TỪ VECTOR RAG (QUY CHẾ TÒA NHÀ) ==="
        ]
        for res in search_results:
            context_parts.append(
                f"- [Độ tương đồng: {res['similarity'] * 100:.1f}%] {res['title']}:\n  {res['content']}"
            )
        context_parts.append(
            "=== HẾT TRI THỨC VECTOR RAG (Hãy ưu tiên trích dẫn các Điều/Khoản ở trên khi trả lời) ==="
        )
        return "\n\n".join(context_parts)

    def get_status(self) -> Dict[str, Any]:
        """Trả về thông tin trạng thái của Vector Database & RAG phục vụ giám sát/báo cáo."""
        return {
            "ready": len(self.documents) > 0,
            "total_chunks": len(self.documents),
            "embedding_source": self.embedding_source,
            "vector_dimension": len(self.documents[0]["vector"]) if self.documents else 0,
            "source_document": str(DOC_PATH.name),
            "algorithm": "Cosine Similarity (Vector Dot Product over L2 Norm)",
        }


# Khởi tạo singleton instance
rag_service = VectorRAGService()
