import os
from typing import List, Dict, Any
from pathlib import Path
import hashlib


class VectorStore:
    """
    Simple in-memory vector store for RAG.
    Loads documents from knowledge/ directory and creates embeddings.
    """

    def __init__(self, knowledge_dir: str = "knowledge"):
        self.documents: List[str] = []
        self.embeddings: List[List[float]] = []
        self.metadata: List[Dict[str, Any]] = []
        self.knowledge_dir = Path(knowledge_dir)

        # Load documents from knowledge directory on init
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Load all markdown files from knowledge directory"""
        if not self.knowledge_dir.exists():
            print(f"Knowledge directory not found: {self.knowledge_dir}")
            return

        for md_file in self.knowledge_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            self.add_document(content, {"source": md_file.name})

        print(f"Loaded {len(self.documents)} documents from knowledge base")
    ## Creates embeddings using a simple hash-based approach (for demonstration purposes).
    def _create_embedding(self, text: str) -> List[float]:
        """Create a simple hash-based embedding (placeholder for production)"""
        embedding = []
        for i in range(384):
            hash_val = hash(text + str(i))
            embedding.append((hash_val % 1000) / 1000.0)
        return embedding
## for semantic search
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 * norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

    def add_document(self, content: str, metadata: Dict[str, Any] = None):
        """Add a document to the vector store"""
        self.documents.append(content)
        self.embeddings.append(self._create_embedding(content))
        self.metadata.append(metadata or {})
# top-3
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for most relevant documents to the query.

        Args:
            query: The search query
            top_k: Number of top results to return

        Returns:
            List of results with content and score
        """
        query_embedding = self._create_embedding(query)

        # Calculate similarities
        similarities = []
        for i, doc_emb in enumerate(self.embeddings):
            sim = self._cosine_similarity(query_embedding, doc_emb)
            similarities.append((i, sim))

        # Sort by similarity and get top_k
        similarities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in similarities[:top_k]:
            results.append({
                "content": self.documents[idx],
                "score": score,
                "metadata": self.metadata[idx]
            })

        return results

    def count(self) -> int:
        """Return number of documents in the store"""
        return len(self.documents)
