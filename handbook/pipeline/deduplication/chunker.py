import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class Chunk:
    """
    Represents a single chunk of content with metadata

    Attributes:
        chunk_id: Unique identifier (SHA256 hash of text)
        chunk_text: The actual chunk content
        chunk_index: Position in the original document (0-based)
        article_id: Parent article/document ID
        source: Content source (Twitter, Article, Youtube, RSS, etc.)
        source_url: Original URL of the content
        created_time: When the original content was created
        metadata: Additional metadata from the chunking process
    """
    chunk_id: str
    chunk_text: str
    chunk_index: int
    article_id: str
    source: str
    source_url: Optional[str] = None
    created_time: Optional[str] = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        """Generate chunk_id from text if not provided"""
        if not self.chunk_id:
            self.chunk_id = self._generate_chunk_id(self.chunk_text)

    @staticmethod
    def _generate_chunk_id(text: str) -> str:
        """Generate SHA256 hash for chunk text"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'chunk_id': self.chunk_id,
            'chunk_text': self.chunk_text,
            'chunk_index': self.chunk_index,
            'article_id': self.article_id,
            'source': self.source,
            'source_url': self.source_url,
            'created_time': self.created_time,
            'metadata': self.metadata or {},
        }


class SemanticChunker:
    """
    Semantic text chunker using RecursiveCharacterTextSplitter

    Respects text structure by splitting on:
    1. Double newlines (paragraphs)
    2. Single newlines
    3. Periods (sentences)
    4. Spaces (words)

    This ensures chunks maintain semantic coherence.
    """

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
        length_function: callable = len,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize semantic chunker

        Args:
            chunk_size: Maximum chunk size in characters (default: 1024 = ~256 tokens)
            chunk_overlap: Overlap between chunks in characters (default: 128 = ~32 tokens)
            length_function: Function to measure chunk length (default: character count)
            separators: Custom separators for splitting (default: ['\n\n', '\n', '. ', ' '])
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Default separators respect text structure
        if separators is None:
            separators = [
                '\n\n',  # Paragraph boundaries
                '\n',    # Line breaks
                '. ',    # Sentence boundaries
                ' ',     # Word boundaries
            ]

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_function,
            separators=separators,
            keep_separator=True,  # Keep separators for context
        )

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into semantic chunks

        Args:
            text: Input text to chunk

        Returns:
            List of chunk texts
        """
        if not text or not text.strip():
            return []

        # Use LangChain's RecursiveCharacterTextSplitter
        chunks = self.splitter.split_text(text)

        return [chunk.strip() for chunk in chunks if chunk.strip()]


class ChunkingPipeline:
    """
    Main chunking pipeline for article processing

    Handles:
    - Text chunking with configurable parameters
    - Metadata preservation
    - Chunk ID generation
    - Filtering (minimum chunk size)
    """

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 128,
        min_chunk_size: int = 100,
    ):
        """
        Initialize chunking pipeline

        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum chunk size to keep (filter out tiny chunks)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

        self.chunker = SemanticChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def process_article(self, article_data: Dict) -> List[Chunk]:
        """
        Process a single article into chunks

        Args:
            article_data: Dictionary with keys:
                - id: Article ID
                - content: Text content to chunk
                - source: Content source (Twitter, Article, etc.)
                - source_url: (optional) Original URL
                - created_time: (optional) Creation timestamp
                - title: (optional) Article title

        Returns:
            List of Chunk objects with metadata
        """
        article_id = article_data.get('id')
        content = article_data.get('content', '')
        source = article_data.get('source', 'Unknown')
        source_url = article_data.get('source_url') or article_data.get('url')
        created_time = article_data.get('created_time')
        title = article_data.get('title', '')

        if not article_id:
            raise ValueError("article_data must contain 'id' field")

        if not content or not content.strip():
            # Return empty list for articles with no content
            return []

        # Chunk the text
        chunk_texts = self.chunker.chunk_text(content)

        # Filter out too-small chunks
        chunk_texts = [
            text for text in chunk_texts
            if len(text) >= self.min_chunk_size
        ]

        # Create Chunk objects with metadata
        chunks = []
        for i, chunk_text in enumerate(chunk_texts):
            chunk = Chunk(
                chunk_id='',  # Will be auto-generated in __post_init__
                chunk_text=chunk_text,
                chunk_index=i,
                article_id=article_id,
                source=source,
                source_url=source_url,
                created_time=created_time,
                metadata={
                    'title': title,
                    'chunk_length': len(chunk_text),
                    'total_chunks': len(chunk_texts),
                }
            )
            chunks.append(chunk)

        return chunks

    def process_batch(self, articles: List[Dict]) -> Dict[str, List[Chunk]]:
        """
        Process multiple articles in batch

        Args:
            articles: List of article dictionaries

        Returns:
            Dictionary mapping article_id -> List[Chunk]
        """
        results = {}

        for article in articles:
            article_id = article.get('id')
            if not article_id:
                continue

            try:
                chunks = self.process_article(article)
                results[article_id] = chunks
            except Exception as e:
                print(f"Error processing article {article_id}: {e}")
                results[article_id] = []

        return results

    def get_statistics(self, chunks: List[Chunk]) -> Dict:
        """
        Calculate statistics for processed chunks

        Args:
            chunks: List of Chunk objects

        Returns:
            Dictionary with statistics
        """
        if not chunks:
            return {
                'total_chunks': 0,
                'total_characters': 0,
                'avg_chunk_size': 0,
                'min_chunk_size': 0,
                'max_chunk_size': 0,
            }

        chunk_sizes = [len(c.chunk_text) for c in chunks]

        return {
            'total_chunks': len(chunks),
            'total_characters': sum(chunk_sizes),
            'avg_chunk_size': sum(chunk_sizes) / len(chunks),
            'min_chunk_size': min(chunk_sizes),
            'max_chunk_size': max(chunk_sizes),
            'unique_articles': len(set(c.article_id for c in chunks)),
        }


# Example usage
if __name__ == "__main__":
    # Example article
    sample_article = {
        'id': 'article_001',
        'title': 'Introduction to LLM Engineering',
        'content': '''
        Large Language Models (LLMs) have revolutionized natural language processing.

        They enable a wide range of applications from chatbots to code generation.
        The key to effective LLM engineering is understanding prompting techniques.

        Prompt engineering involves crafting inputs that guide the model effectively.
        This includes techniques like few-shot learning and chain-of-thought prompting.

        RAG (Retrieval-Augmented Generation) combines LLMs with external knowledge.
        This approach helps ground responses in factual information.
        ''',
        'source': 'Article',
        'source_url': 'https://example.com/llm-intro',
        'created_time': '2024-11-15T10:00:00Z',
    }

    # Initialize pipeline
    pipeline = ChunkingPipeline(
        chunk_size=200,  # Small for demo
        chunk_overlap=50,
        min_chunk_size=50
    )

    # Process article
    chunks = pipeline.process_article(sample_article)

    # Print results
    print(f"Generated {len(chunks)} chunks:\n")
    for chunk in chunks:
        print(f"Chunk {chunk.chunk_index}:")
        print(f"  ID: {chunk.chunk_id[:16]}...")
        print(f"  Length: {len(chunk.chunk_text)} chars")
        print(f"  Text: {chunk.chunk_text[:100]}...")
        print()

    # Statistics
    stats = pipeline.get_statistics(chunks)
    print(f"Statistics: {stats}")
