"""
Full deduplication pipeline integration test

Tests the complete flow:
1. Chunking (chunker.py)
2. Embedding generation (embedder.py)
3. Similarity detection (similarity.py)
4. Incremental deduplication
"""

import os
import sys

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from handbook.pipeline.deduplication.chunker import ChunkingPipeline
from handbook.pipeline.deduplication.embedder import EmbeddingGenerator
from handbook.pipeline.deduplication.similarity import ChromaDBDeduplicator, SimilarityCalculator


def test_pipeline_without_api():
    """Test pipeline components that don't require API calls"""
    print("="*60)
    print("TEST 1: Pipeline Without API")
    print("="*60)

    # Test articles
    article1 = {
        'id': 'test_001',
        'title': 'Introduction to Vector Databases',
        'content': '''
        Vector databases are specialized systems for storing and querying embeddings.
        They enable fast similarity search across millions of vectors.
        Popular options include Pinecone, Weaviate, and ChromaDB.

        These databases use approximate nearest neighbor (ANN) algorithms.
        This allows for sub-100ms query times even with large datasets.
        ''',
        'source': 'Article',
        'source_url': 'https://example.com/vector-db',
    }

    article2 = {
        'id': 'test_002',
        'title': 'Understanding Embeddings',
        'content': '''
        Embeddings are numerical representations of data in vector space.
        Text embeddings capture semantic meaning of words and sentences.
        Similar concepts are mapped to nearby points in the space.

        Modern embedding models like text-embedding-3-small produce 1536-dimensional vectors.
        These vectors enable powerful semantic search capabilities.
        ''',
        'source': 'Article',
        'source_url': 'https://example.com/embeddings',
    }

    # Step 1: Chunking
    print("\n1. Testing chunking...")
    chunker = ChunkingPipeline(
        chunk_size=200,
        chunk_overlap=50,
        min_chunk_size=50
    )

    chunks1 = chunker.process_article(article1)
    chunks2 = chunker.process_article(article2)

    print(f"   Article 1: {len(chunks1)} chunks")
    print(f"   Article 2: {len(chunks2)} chunks")

    all_chunks = chunks1 + chunks2
    print(f"   Total: {len(all_chunks)} chunks")

    # Verify chunk structure
    for chunk in all_chunks[:2]:
        print(f"\n   Sample chunk:")
        print(f"     ID: {chunk.chunk_id[:16]}...")
        print(f"     Article: {chunk.article_id}")
        print(f"     Index: {chunk.chunk_index}")
        print(f"     Text length: {len(chunk.chunk_text)}")

    # Step 2: Cosine similarity (direct calculation)
    print("\n2. Testing cosine similarity...")
    calc = SimilarityCalculator()

    # Test vectors
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    vec3 = [0.0, 1.0, 0.0]

    sim_identical = calc.cosine_similarity(vec1, vec2)
    sim_orthogonal = calc.cosine_similarity(vec1, vec3)

    print(f"   Identical vectors: {sim_identical:.3f} (expected: 1.000)")
    print(f"   Orthogonal vectors: {sim_orthogonal:.3f} (expected: 0.000)")

    assert abs(sim_identical - 1.0) < 0.001, "Identical vectors should have similarity 1.0"
    assert abs(sim_orthogonal - 0.0) < 0.001, "Orthogonal vectors should have similarity 0.0"

    # Test duplicate detection
    print(f"\n   Is duplicate (0.95 with threshold 0.90): {calc.is_duplicate(0.95, 0.90)}")
    print(f"   Is duplicate (0.85 with threshold 0.90): {calc.is_duplicate(0.85, 0.90)}")

    print("\n✓ Pipeline test (without API) passed\n")


def test_full_pipeline_with_api():
    """Test complete pipeline including embeddings (requires OpenAI API key)"""
    print("="*60)
    print("TEST 2: Full Pipeline With Embeddings")
    print("="*60)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠ Skipping: OPENAI_API_KEY not set")
        print("   Set with: export OPENAI_API_KEY='your-key'")
        return

    # Sample articles with some duplicate content
    articles = [
        {
            'id': 'full_001',
            'title': 'RAG Systems Overview',
            'content': '''
            Retrieval-Augmented Generation (RAG) is a powerful technique for LLMs.
            It combines pre-trained language models with external knowledge retrieval.
            This helps ground responses in factual information and reduce hallucinations.

            The RAG pipeline typically has three stages: retrieval, ranking, and generation.
            First, relevant documents are retrieved using semantic search.
            Then, the most relevant chunks are ranked and passed to the LLM.
            ''',
            'source': 'Article',
        },
        {
            'id': 'full_002',
            'title': 'Building RAG Applications',  # Similar to full_001
            'content': '''
            RAG (Retrieval-Augmented Generation) enhances LLMs with external knowledge.
            It combines language models with information retrieval systems.
            This approach helps reduce hallucinations in model outputs.

            A typical RAG system has retrieval, ranking, and generation components.
            Documents are retrieved via semantic search based on query embeddings.
            Top-ranked chunks are then provided as context to the language model.
            ''',
            'source': 'Article',
        },
        {
            'id': 'full_003',
            'title': 'Prompt Engineering Basics',  # Different content
            'content': '''
            Prompt engineering is the art of crafting effective LLM inputs.
            Well-designed prompts can dramatically improve model performance.
            Common techniques include few-shot learning and chain-of-thought.

            Few-shot prompting provides examples in the prompt itself.
            Chain-of-thought encourages step-by-step reasoning.
            These methods help guide the model toward better outputs.
            ''',
            'source': 'Article',
        },
    ]

    try:
        # Step 1: Chunk all articles
        print("\n1. Chunking articles...")
        chunker = ChunkingPipeline(
            chunk_size=300,
            chunk_overlap=75,
            min_chunk_size=50
        )

        all_chunks = []
        for article in articles:
            chunks = chunker.process_article(article)
            all_chunks.extend(chunks)
            print(f"   {article['id']}: {len(chunks)} chunks")

        print(f"   Total chunks: {len(all_chunks)}")

        # Step 2: Generate embeddings
        print("\n2. Generating embeddings...")
        embedder = EmbeddingGenerator(
            model="text-embedding-3-small",
            batch_size=100
        )

        embedding_results = embedder.embed_chunks(all_chunks)

        # Show cost
        stats = embedder.get_usage_stats()
        print(f"\n   Embedding stats:")
        print(f"     Tokens: {stats['total_tokens']:,}")
        print(f"     Cost: ${stats['total_cost_dollars']:.4f}")

        # Step 3: Deduplication
        print("\n3. Setting up ChromaDB...")
        deduplicator = ChromaDBDeduplicator(
            collection_name="test_full_pipeline",
            persist_directory=None,  # In-memory for test
            similarity_threshold=0.85,
        )

        # Clear any existing data
        deduplicator.clear_collection()

        # Process in two batches to simulate incremental updates
        print("\n4. Processing first batch (articles 1-2)...")
        first_batch_size = sum(1 for c in all_chunks if c.article_id in ['full_001', 'full_002'])

        first_chunk_ids = [r.chunk_id for r in embedding_results[:first_batch_size]]
        first_embeddings = [r.embedding for r in embedding_results[:first_batch_size]]
        first_texts = [c.chunk_text for c in all_chunks[:first_batch_size]]
        first_metadatas = [
            {'article_id': c.article_id, 'source': c.source, 'chunk_index': c.chunk_index}
            for c in all_chunks[:first_batch_size]
        ]

        unique1, dup1, map1 = deduplicator.deduplicate_new_chunks(
            new_chunk_ids=first_chunk_ids,
            new_embeddings=first_embeddings,
            new_texts=first_texts,
            new_metadatas=first_metadatas,
        )

        print(f"\n   Batch 1 results:")
        print(f"     Unique: {len(unique1)}")
        print(f"     Duplicates: {len(dup1)}")

        # Process second batch
        print("\n5. Processing second batch (article 3)...")
        second_chunk_ids = [r.chunk_id for r in embedding_results[first_batch_size:]]
        second_embeddings = [r.embedding for r in embedding_results[first_batch_size:]]
        second_texts = [c.chunk_text for c in all_chunks[first_batch_size:]]
        second_metadatas = [
            {'article_id': c.article_id, 'source': c.source, 'chunk_index': c.chunk_index}
            for c in all_chunks[first_batch_size:]
        ]

        unique2, dup2, map2 = deduplicator.deduplicate_new_chunks(
            new_chunk_ids=second_chunk_ids,
            new_embeddings=second_embeddings,
            new_texts=second_texts,
            new_metadatas=second_metadatas,
        )

        print(f"\n   Batch 2 results:")
        print(f"     Unique: {len(unique2)}")
        print(f"     Duplicates: {len(dup2)}")

        # Show duplicate details
        if dup1:
            print(f"\n6. Duplicate examples from batch 1:")
            for dup_id in dup1[:2]:
                similar = map1[dup_id][0]
                print(f"\n   Duplicate chunk: {dup_id[:16]}...")
                print(f"     Similarity: {similar.similarity:.3f}")
                print(f"     Text preview: {first_texts[first_chunk_ids.index(dup_id)][:80]}...")

        # Final stats
        print(f"\n7. Final database stats:")
        db_stats = deduplicator.get_stats()
        for key, value in db_stats.items():
            print(f"     {key}: {value}")

        print("\n✓ Full pipeline test passed\n")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("FULL DEDUPLICATION PIPELINE TEST")
    print("="*60 + "\n")

    # Test 1: Without API (always runs)
    test_pipeline_without_api()

    # Test 2: With API (requires OPENAI_API_KEY)
    test_full_pipeline_with_api()

    print("="*60)
    print("ALL TESTS COMPLETE")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
