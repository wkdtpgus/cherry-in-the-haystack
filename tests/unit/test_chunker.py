"""
Test script for chunking pipeline

Tests:
1. Basic chunking functionality
2. Metadata preservation
3. Chunk ID generation
4. Batch processing
5. Edge cases (empty content, very long content)
"""

import os
import sys

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from handbook.pipeline.deduplication.chunker import ChunkingPipeline, SemanticChunker, Chunk


def test_basic_chunking():
    """Test basic chunking with simple text"""
    print("="*60)
    print("TEST 1: Basic Chunking")
    print("="*60)

    article = {
        'id': 'test_001',
        'title': 'Sample Article',
        'content': '''
        This is the first paragraph. It contains multiple sentences.
        This helps test the chunking behavior.

        This is the second paragraph. It should be in a separate chunk
        if the chunk size is small enough.

        And here is a third paragraph for good measure.
        ''',
        'source': 'Test',
        'source_url': 'https://test.com/article',
        'created_time': '2024-11-15T10:00:00Z',
    }

    pipeline = ChunkingPipeline(
        chunk_size=150,
        chunk_overlap=30,
        min_chunk_size=20
    )

    chunks = pipeline.process_article(article)

    print(f"\nGenerated {len(chunks)} chunks from {len(article['content'])} chars\n")

    for chunk in chunks:
        print(f"Chunk {chunk.chunk_index}:")
        print(f"  ID: {chunk.chunk_id[:16]}...")
        print(f"  Length: {len(chunk.chunk_text)} chars")
        print(f"  Text: {chunk.chunk_text[:80]}...")
        print()

    stats = pipeline.get_statistics(chunks)
    print(f"Statistics: {stats}\n")

    assert len(chunks) > 0, "Should generate at least one chunk"
    assert all(c.article_id == 'test_001' for c in chunks), "All chunks should have correct article_id"
    print("✓ Basic chunking test passed\n")


def test_metadata_preservation():
    """Test that metadata is correctly preserved"""
    print("="*60)
    print("TEST 2: Metadata Preservation")
    print("="*60)

    article = {
        'id': 'test_002',
        'title': 'Metadata Test',
        'content': 'Short content for metadata test. ' * 20,
        'source': 'Twitter',
        'source_url': 'https://twitter.com/test/status/123',
        'created_time': '2024-11-15T12:00:00Z',
    }

    pipeline = ChunkingPipeline(chunk_size=100, chunk_overlap=20)
    chunks = pipeline.process_article(article)

    print(f"\nGenerated {len(chunks)} chunks\n")

    for chunk in chunks:
        print(f"Chunk {chunk.chunk_index}:")
        print(f"  Article ID: {chunk.article_id}")
        print(f"  Source: {chunk.source}")
        print(f"  Source URL: {chunk.source_url}")
        print(f"  Created Time: {chunk.created_time}")
        print(f"  Metadata: {chunk.metadata}")
        print()

        # Verify metadata
        assert chunk.article_id == 'test_002'
        assert chunk.source == 'Twitter'
        assert chunk.source_url == 'https://twitter.com/test/status/123'
        assert chunk.created_time == '2024-11-15T12:00:00Z'
        assert chunk.metadata['title'] == 'Metadata Test'

    print("✓ Metadata preservation test passed\n")


def test_chunk_id_uniqueness():
    """Test that chunk IDs are unique and deterministic"""
    print("="*60)
    print("TEST 3: Chunk ID Uniqueness")
    print("="*60)

    article = {
        'id': 'test_003',
        'content': 'Different content. ' * 50,
        'source': 'Test',
    }

    pipeline = ChunkingPipeline(chunk_size=100, chunk_overlap=20)
    chunks1 = pipeline.process_article(article)
    chunks2 = pipeline.process_article(article)

    print(f"\nFirst run: {len(chunks1)} chunks")
    print(f"Second run: {len(chunks2)} chunks\n")

    # Same article should produce same chunk IDs
    ids1 = [c.chunk_id for c in chunks1]
    ids2 = [c.chunk_id for c in chunks2]

    print("Checking deterministic chunk IDs...")
    assert ids1 == ids2, "Same content should produce same chunk IDs"

    # All chunk IDs should be unique within the article
    print("Checking uniqueness...")
    assert len(ids1) == len(set(ids1)), "All chunk IDs should be unique"

    print("✓ Chunk ID uniqueness test passed\n")


def test_batch_processing():
    """Test batch processing of multiple articles"""
    print("="*60)
    print("TEST 4: Batch Processing")
    print("="*60)

    articles = [
        {
            'id': f'batch_00{i}',
            'title': f'Article {i}',
            'content': f'This is article {i}. ' * 30,
            'source': 'Batch',
        }
        for i in range(1, 6)
    ]

    pipeline = ChunkingPipeline(chunk_size=150, chunk_overlap=30)
    results = pipeline.process_batch(articles)

    print(f"\nProcessed {len(results)} articles\n")

    total_chunks = 0
    for article_id, chunks in results.items():
        print(f"Article {article_id}: {len(chunks)} chunks")
        total_chunks += len(chunks)

    print(f"\nTotal chunks: {total_chunks}")

    assert len(results) == 5, "Should process all 5 articles"
    assert total_chunks > 0, "Should generate chunks"

    print("\n✓ Batch processing test passed\n")


def test_edge_cases():
    """Test edge cases: empty content, very short, very long"""
    print("="*60)
    print("TEST 5: Edge Cases")
    print("="*60)

    pipeline = ChunkingPipeline(chunk_size=200, chunk_overlap=50, min_chunk_size=50)

    # Test 1: Empty content
    print("\n1. Empty content:")
    empty_article = {'id': 'empty', 'content': '', 'source': 'Test'}
    chunks = pipeline.process_article(empty_article)
    print(f"   Chunks: {len(chunks)} (expected 0)")
    assert len(chunks) == 0, "Empty content should produce no chunks"

    # Test 2: Very short content (below min_chunk_size)
    print("\n2. Very short content:")
    short_article = {'id': 'short', 'content': 'Too short', 'source': 'Test'}
    chunks = pipeline.process_article(short_article)
    print(f"   Chunks: {len(chunks)} (expected 0, filtered by min_chunk_size)")
    assert len(chunks) == 0, "Content below min_chunk_size should be filtered"

    # Test 3: Content exactly at chunk_size
    print("\n3. Content at chunk_size boundary:")
    exact_article = {'id': 'exact', 'content': 'X' * 200, 'source': 'Test'}
    chunks = pipeline.process_article(exact_article)
    print(f"   Chunks: {len(chunks)}")
    assert len(chunks) >= 1, "Should produce at least one chunk"

    # Test 4: Very long content
    print("\n4. Very long content (10000 chars):")
    long_article = {
        'id': 'long',
        'content': ('This is a long sentence. ' * 400),
        'source': 'Test'
    }
    chunks = pipeline.process_article(long_article)
    print(f"   Chunks: {len(chunks)}")
    print(f"   Avg chunk size: {sum(len(c.chunk_text) for c in chunks) / len(chunks):.0f} chars")
    assert len(chunks) > 5, "Long content should produce many chunks"

    print("\n✓ Edge cases test passed\n")


def test_realistic_article():
    """Test with realistic article content"""
    print("="*60)
    print("TEST 6: Realistic Article")
    print("="*60)

    article = {
        'id': 'realistic_001',
        'title': 'GPT-4.5 Released: What You Need to Know',
        'content': '''
        OpenAI has announced the release of GPT-4.5, the latest iteration of their
        flagship language model. This release brings several significant improvements
        over GPT-4, particularly in reasoning capabilities and context handling.

        Key Features

        The most notable enhancement is the expanded context window, now supporting
        up to 256K tokens. This allows the model to process and reason over much
        larger documents than before. Early benchmarks show a 15% improvement in
        complex reasoning tasks compared to GPT-4.

        Additionally, GPT-4.5 introduces better instruction following and reduced
        hallucination rates. The model has been trained with a new alignment technique
        that improves factual accuracy while maintaining creative capabilities.

        Performance Benchmarks

        In standardized tests, GPT-4.5 achieved 92% on the MMLU benchmark, up from
        86.4% for GPT-4. Code generation capabilities have also improved, with the
        model passing 89% of LeetCode hard problems compared to 67% for GPT-4.

        Availability and Pricing

        GPT-4.5 is available through the OpenAI API starting today. Pricing remains
        competitive at $0.01 per 1K input tokens and $0.03 per 1K output tokens.
        Enterprise customers can access additional features including fine-tuning
        and dedicated capacity.

        Conclusion

        GPT-4.5 represents a meaningful step forward in language model capabilities.
        The improvements in context handling and reasoning make it particularly
        well-suited for complex analytical tasks and long-form content generation.
        ''',
        'source': 'Article',
        'source_url': 'https://example.com/gpt45-release',
        'created_time': '2024-11-15T09:00:00Z',
    }

    pipeline = ChunkingPipeline(
        chunk_size=400,
        chunk_overlap=50,
        min_chunk_size=100
    )

    chunks = pipeline.process_article(article)

    print(f"\nArticle: {article['title']}")
    print(f"Content length: {len(article['content'])} chars")
    print(f"Generated {len(chunks)} chunks\n")

    for i, chunk in enumerate(chunks):
        print(f"--- Chunk {i} ---")
        print(f"Length: {len(chunk.chunk_text)} chars")
        print(f"Preview: {chunk.chunk_text[:150]}...")
        print()

    stats = pipeline.get_statistics(chunks)
    print(f"Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✓ Realistic article test passed\n")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("CHUNKING PIPELINE TEST SUITE")
    print("="*60 + "\n")

    tests = [
        test_basic_chunking,
        test_metadata_preservation,
        test_chunk_id_uniqueness,
        test_batch_processing,
        test_edge_cases,
        test_realistic_article,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n✗ Test failed: {test.__name__}")
            print(f"  Error: {e}\n")
            failed += 1

    print("="*60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("="*60 + "\n")


if __name__ == "__main__":
    run_all_tests()
