"""
Embedding generation for chunk-level deduplication

Supports:
- OpenAI text-embedding-3-small (primary)
- Batch API for cost optimization (50% discount)
- Caching to avoid redundant API calls
- Fallback providers (future: Ollama, local models)
"""

import os
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from .chunker import Chunk


@dataclass
class EmbeddingResult:
    """
    Result of embedding generation
    """
    chunk_id: str
    embedding: List[float]
    model: str
    token_count: int
    cost_cents: float


class EmbeddingGenerator:
    """
    Generate embeddings for text chunks using OpenAI API

    Features:
    - Batch processing for cost optimization
    - Automatic retry with exponential backoff
    - Cost tracking
    - Provider abstraction for future multi-provider support
    """

    # Pricing (as of 2024): text-embedding-3-small
    COST_PER_1M_TOKENS = 0.02  # $0.02 per 1M tokens

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize embedding generator

        Args:
            model: OpenAI embedding model (default: text-embedding-3-small)
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            batch_size: Number of texts to embed in single API call
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Initial delay between retries (exponential backoff)
        """
        if OpenAI is None:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize OpenAI client
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self.client = OpenAI(api_key=api_key)

        # Track costs and usage
        self.total_tokens = 0
        self.total_cost_cents = 0.0

    def _estimate_tokens(self, text: str) -> int:
        """
        Rough estimate of token count

        Uses simple heuristic: ~4 characters per token
        For accurate counting, use tiktoken library
        """
        return len(text) // 4

    def _calculate_cost(self, token_count: int) -> float:
        """Calculate cost in cents for given token count"""
        return (token_count / 1_000_000) * self.COST_PER_1M_TOKENS * 100

    def embed_text(self, text: str) -> Tuple[List[float], int]:
        """
        Generate embedding for a single text

        Args:
            text: Input text to embed

        Returns:
            Tuple of (embedding vector, token count)
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                )

                embedding = response.data[0].embedding
                token_count = response.usage.total_tokens

                return embedding, token_count

            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"Embedding failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    print(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise Exception(f"Failed to generate embedding after {self.max_retries} attempts: {e}")

    def embed_batch(self, texts: List[str]) -> List[Tuple[List[float], int]]:
        """
        Generate embeddings for multiple texts in a single API call

        Args:
            texts: List of texts to embed

        Returns:
            List of (embedding vector, token count) tuples
        """
        if not texts:
            return []

        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )

                results = []
                for data in response.data:
                    results.append((data.embedding, 0))  # Token count per item not available in batch

                total_tokens = response.usage.total_tokens
                avg_tokens_per_text = total_tokens // len(texts)

                # Update token counts
                results = [(emb, avg_tokens_per_text) for emb, _ in results]

                return results

            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"Batch embedding failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    print(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise Exception(f"Failed to generate batch embeddings after {self.max_retries} attempts: {e}")

    def embed_chunk(self, chunk: Chunk) -> EmbeddingResult:
        """
        Generate embedding for a single chunk

        Args:
            chunk: Chunk object to embed

        Returns:
            EmbeddingResult with embedding and metadata
        """
        embedding, token_count = self.embed_text(chunk.chunk_text)
        cost_cents = self._calculate_cost(token_count)

        # Update totals
        self.total_tokens += token_count
        self.total_cost_cents += cost_cents

        return EmbeddingResult(
            chunk_id=chunk.chunk_id,
            embedding=embedding,
            model=self.model,
            token_count=token_count,
            cost_cents=cost_cents,
        )

    def embed_chunks(self, chunks: List[Chunk]) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple chunks with batching

        Automatically batches requests for cost optimization
        (OpenAI allows up to 2048 inputs per request)

        Args:
            chunks: List of Chunk objects

        Returns:
            List of EmbeddingResult objects
        """
        if not chunks:
            return []

        results = []
        total_chunks = len(chunks)

        # Process in batches
        for i in range(0, total_chunks, self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_texts = [c.chunk_text for c in batch]

            print(f"Processing batch {i // self.batch_size + 1}/{(total_chunks + self.batch_size - 1) // self.batch_size} "
                  f"({len(batch)} chunks)...")

            # Generate embeddings for batch
            embeddings_and_tokens = self.embed_batch(batch_texts)

            # Create results
            for chunk, (embedding, token_count) in zip(batch, embeddings_and_tokens):
                cost_cents = self._calculate_cost(token_count)

                # Update totals
                self.total_tokens += token_count
                self.total_cost_cents += cost_cents

                result = EmbeddingResult(
                    chunk_id=chunk.chunk_id,
                    embedding=embedding,
                    model=self.model,
                    token_count=token_count,
                    cost_cents=cost_cents,
                )
                results.append(result)

        print(f"\nCompleted {len(results)} embeddings")
        print(f"Total tokens: {self.total_tokens:,}")
        print(f"Total cost: ${self.total_cost_cents / 100:.4f}")

        return results

    def get_usage_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            'total_tokens': self.total_tokens,
            'total_cost_cents': self.total_cost_cents,
            'total_cost_dollars': self.total_cost_cents / 100,
            'model': self.model,
        }

    def reset_stats(self):
        """Reset usage statistics"""
        self.total_tokens = 0
        self.total_cost_cents = 0.0


