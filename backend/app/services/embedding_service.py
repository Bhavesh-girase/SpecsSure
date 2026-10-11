import logging
from typing import List, Union
import numpy as np
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    _instance = None
    _model = None
    _tried = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingService, cls).__new__(cls)
        return cls._instance

    def _get_model(self):
        if self._model is None and not self._tried:
            self._tried = True
            if settings.EMBEDDING_MODEL.lower() in ("none", "hash", "offline", ""):
                logger.info("Embedding model disabled — using deterministic hashed n-gram embeddings (offline mode).")
                return None
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading multilingual embedding model: {settings.EMBEDDING_MODEL}")
                self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
                logger.info("Embedding model loaded successfully.")
            except Exception as e:
                # No silent swap to a smaller model: a different dimension would corrupt the vector index.
                logger.warning(f"Could not load embedding model ({settings.EMBEDDING_MODEL}): {e}. "
                               "Using deterministic hashed n-gram embeddings (offline mode).")
                self._model = None
        return self._model

    def embed_query(self, text: str) -> List[float]:
        """Prefixes with query: (for E5/BGE models) and returns normalized float list."""
        if not text or not text.strip():
            return [0.0] * settings.EMBEDDING_DIMENSION
        model = self._get_model()
        if model is not None:
            prefix = "query: " if "e5" in settings.EMBEDDING_MODEL.lower() else ""
            formatted = f"{prefix}{text.strip()}"
            emb = model.encode(formatted, normalize_embeddings=True)
            return emb.tolist()
        else:
            # Deterministic pseudo-embedding fallback if no model is loaded
            return self._fallback_hash_embedding(text)

    def embed_document(self, text: str) -> List[float]:
        """Prefixes with passage: (for E5/BGE models) and returns normalized float list."""
        if not text or not text.strip():
            return [0.0] * settings.EMBEDDING_DIMENSION
        model = self._get_model()
        if model is not None:
            prefix = "passage: " if "e5" in settings.EMBEDDING_MODEL.lower() else ""
            formatted = f"{prefix}{text.strip()}"
            emb = model.encode(formatted, normalize_embeddings=True)
            return emb.tolist()
        else:
            return self._fallback_hash_embedding(text)

    def embed_batch(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        """Batch encodes texts."""
        if not texts:
            return []
        model = self._get_model()
        if model is not None:
            prefix = ("query: " if is_query else "passage: ") if "e5" in settings.EMBEDDING_MODEL.lower() else ""
            formatted_texts = [f"{prefix}{t.strip()}" if t and t.strip() else "" for t in texts]
            embeddings = model.encode(formatted_texts, normalize_embeddings=True, batch_size=32)
            return embeddings.tolist()
        else:
            return [self._fallback_hash_embedding(t) for t in texts]

    def _fallback_hash_embedding(self, text: str) -> List[float]:
        """Deterministic hashed word + character-trigram embedding (feature hashing) for offline mode.
        Uses a stable hash (blake2b) — Python's hash() is salted per process and would make stored
        vectors incomparable with query vectors after a restart."""
        import hashlib, re as _re
        dim = settings.EMBEDDING_DIMENSION
        vec = np.zeros(dim, dtype=np.float32)
        words = _re.findall(r"[a-z0-9\u0900-\u097f]+", text.lower())
        feats = words + [w[i:i + 3] for w in words if len(w) > 3 for i in range(len(w) - 2)]
        for f in feats:
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "little")
            vec[h % dim] += (1.0 if len(f) > 3 or f in words else 0.5) * (1 if (h >> 63) & 1 else -1)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

embedding_service = EmbeddingService()
