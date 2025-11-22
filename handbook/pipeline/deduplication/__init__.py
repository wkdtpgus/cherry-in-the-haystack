"""
Deduplication pipeline for chunk-level similarity detection

This module provides chunk-level deduplication using:
- Semantic chunking with RecursiveCharacterTextSplitter
- Embedding generation (OpenAI text-embedding-3-small)
- Cosine similarity search (pgvector/ChromaDB)
"""

from .chunker import ChunkingPipeline, SemanticChunker
from .embedder import EmbeddingGenerator
from .similarity import SimilarityCalculator

__all__ = [
    'ChunkingPipeline',
    'SemanticChunker',
    'EmbeddingGenerator',
    'SimilarityCalculator',
]
