"""
Similarity calculation and duplicate detection

Features:
- Cosine similarity computation
- Threshold-based duplicate detection
- ChromaDB integration for vector storage and search
- Incremental deduplication (new vs existing chunks)
"""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None


@dataclass
class SimilarityResult:
    """
    Result of similarity search

    Attributes:
        query_chunk_id: ID of the query chunk
        similar_chunk_id: ID of the similar chunk found
        similarity: Cosine similarity score (0-1, higher = more similar)
        chunk_text: Text of the similar chunk
        metadata: Additional metadata from similar chunk
    """
    query_chunk_id: str
    similar_chunk_id: str
    similarity: float
    chunk_text: str
    metadata: Optional[Dict] = None


class SimilarityCalculator:
    """
    Calculate cosine similarity between vectors

    Provides both direct calculation and ChromaDB-based search
    """

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity score (0-1, higher = more similar)
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} vs {len(vec2)}")

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    @staticmethod
    def is_duplicate(similarity: float, threshold: float = 0.90) -> bool:
        """
        Determine if similarity score indicates a duplicate

        Args:
            similarity: Similarity score
            threshold: Minimum similarity to consider duplicate (default: 0.90)

        Returns:
            True if similarity >= threshold
        """
        return similarity >= threshold


class ChromaDBDeduplicator:
    """
    Chunk-level deduplication using ChromaDB vector database

    Features:
    - Store chunk embeddings with metadata
    - Fast similarity search with ivfflat index
    - Incremental updates (add new chunks)
    - Batch operations for efficiency
    """

    def __init__(
        self,
        collection_name: str = "handbook_chunks",
        persist_directory: Optional[str] = "./chroma_db",
        similarity_threshold: float = 0.90,
    ):
        """
        Initialize ChromaDB deduplicator

        Args:
            collection_name: Name of ChromaDB collection
            persist_directory: Directory to persist database (None for in-memory)
            similarity_threshold: Similarity threshold for duplicate detection
        """
        if chromadb is None:
            raise ImportError(
                "chromadb package not installed. "
                "Install with: pip install chromadb"
            )

        self.collection_name = collection_name
        self.similarity_threshold = similarity_threshold

        # Initialize ChromaDB client
        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine distance
        )

        print(f"Initialized ChromaDB collection: {collection_name}")
        print(f"Existing chunks: {self.collection.count()}")

    def add_chunks(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: Optional[List[Dict]] = None,
    ):
        """
        Add chunks to the database

        Args:
            chunk_ids: List of unique chunk IDs
            embeddings: List of embedding vectors
            texts: List of chunk texts
            metadatas: Optional list of metadata dictionaries
        """
        if not chunk_ids:
            return

        if metadatas is None:
            metadatas = [{} for _ in chunk_ids]

        self.collection.add(
            ids=chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        print(f"Added {len(chunk_ids)} chunks to collection")

    def find_similar(
        self,
        query_embedding: List[float],
        query_chunk_id: str,
        top_k: int = 5,
        include_self: bool = False,
    ) -> List[SimilarityResult]:
        """
        Find similar chunks for a given embedding

        Args:
            query_embedding: Query embedding vector
            query_chunk_id: ID of the query chunk (to filter self-matches)
            top_k: Number of similar chunks to return
            include_self: Whether to include the query chunk itself in results

        Returns:
            List of SimilarityResult objects
        """
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k + 1 if not include_self else top_k,
        )

        similar_chunks = []

        if not results['ids'] or not results['ids'][0]:
            return similar_chunks

        for i in range(len(results['ids'][0])):
            similar_id = results['ids'][0][i]

            # Skip self-match
            if not include_self and similar_id == query_chunk_id:
                continue

            # ChromaDB returns distance (lower = more similar)
            # Convert to similarity: similarity = 1 - distance
            distance = results['distances'][0][i]
            similarity = 1 - distance

            # Only include results above threshold
            if similarity < self.similarity_threshold:
                continue

            similar_chunks.append(SimilarityResult(
                query_chunk_id=query_chunk_id,
                similar_chunk_id=similar_id,
                similarity=similarity,
                chunk_text=results['documents'][0][i],
                metadata=results['metadatas'][0][i] if results['metadatas'] else None,
            ))

        return similar_chunks

    def find_duplicates_batch(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        top_k: int = 5,
    ) -> Dict[str, List[SimilarityResult]]:
        """
        Find duplicates for multiple chunks

        Args:
            chunk_ids: List of chunk IDs
            embeddings: List of embedding vectors
            top_k: Number of similar chunks to check per query

        Returns:
            Dictionary mapping chunk_id -> list of similar chunks
        """
        results = {}

        for chunk_id, embedding in zip(chunk_ids, embeddings):
            similar = self.find_similar(
                query_embedding=embedding,
                query_chunk_id=chunk_id,
                top_k=top_k,
            )
            results[chunk_id] = similar

        return results

    def deduplicate_new_chunks(
        self,
        new_chunk_ids: List[str],
        new_embeddings: List[List[float]],
        new_texts: List[str],
        new_metadatas: Optional[List[Dict]] = None,
    ) -> Tuple[List[str], List[str], Dict[str, List[SimilarityResult]]]:
        """
        Deduplicate new chunks against existing database

        Args:
            new_chunk_ids: IDs of new chunks
            new_embeddings: Embeddings of new chunks
            new_texts: Texts of new chunks
            new_metadatas: Optional metadata of new chunks

        Returns:
            Tuple of:
            - List of unique chunk IDs (no duplicates found)
            - List of duplicate chunk IDs
            - Dictionary of duplicate mappings
        """
        unique_ids = []
        duplicate_ids = []
        duplicate_mappings = {}

        print(f"\nChecking {len(new_chunk_ids)} new chunks for duplicates...")

        for i, (chunk_id, embedding, text) in enumerate(zip(new_chunk_ids, new_embeddings, new_texts)):
            # Find similar chunks in existing database
            similar = self.find_similar(
                query_embedding=embedding,
                query_chunk_id=chunk_id,
                top_k=5,
            )

            if similar:
                # Duplicate found
                duplicate_ids.append(chunk_id)
                duplicate_mappings[chunk_id] = similar

                print(f"  [{i+1}/{len(new_chunk_ids)}] DUPLICATE: {chunk_id[:16]}... "
                      f"(similarity: {similar[0].similarity:.3f})")
            else:
                # Unique chunk
                unique_ids.append(chunk_id)
                print(f"  [{i+1}/{len(new_chunk_ids)}] UNIQUE: {chunk_id[:16]}...")

        print(f"\nResults: {len(unique_ids)} unique, {len(duplicate_ids)} duplicates")

        # Add unique chunks to database
        if unique_ids:
            unique_indices = [i for i, cid in enumerate(new_chunk_ids) if cid in unique_ids]
            unique_embeddings = [new_embeddings[i] for i in unique_indices]
            unique_texts = [new_texts[i] for i in unique_indices]
            unique_metadatas = [new_metadatas[i] for i in unique_indices] if new_metadatas else None

            self.add_chunks(unique_ids, unique_embeddings, unique_texts, unique_metadatas)

        return unique_ids, duplicate_ids, duplicate_mappings

    def get_stats(self) -> Dict:
        """Get database statistics"""
        return {
            'collection_name': self.collection_name,
            'total_chunks': self.collection.count(),
            'similarity_threshold': self.similarity_threshold,
        }

    def clear_collection(self):
        """Clear all chunks from collection (use with caution!)"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"Cleared collection: {self.collection_name}")


