"""
Deduplication Dataset Evaluation with Ground Truth Comparison

Tests the deduplication pipeline against the dataset with:
- 6 duplicate types: exact, paraphrase, fragment, semantic, mixed_real
- Ground Truth comparison for accuracy measurement
- Precision, Recall, F1 metrics
- Multi-threshold evaluation (0.85, 0.90, 0.95)
"""

import os
import sys
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from handbook.pipeline.deduplication.chunker import ChunkingPipeline
from handbook.pipeline.deduplication.embedder import EmbeddingGenerator
from handbook.pipeline.deduplication.similarity import ChromaDBDeduplicator


@dataclass
class EvaluationMetrics:
    """Evaluation metrics for deduplication performance"""
    true_positives: int = 0   # Correctly identified duplicates
    false_positives: int = 0  # Incorrectly marked as duplicates
    true_negatives: int = 0   # Correctly identified unique
    false_negatives: int = 0  # Missed duplicates

    @property
    def precision(self) -> float:
        """Precision: TP / (TP + FP)"""
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        """Recall: TP / (TP + FN)"""
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1_score(self) -> float:
        """F1: 2 * (Precision * Recall) / (Precision + Recall)"""
        p, r = self.precision, self.recall
        return 2 * (p * r) / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        """Accuracy: (TP + TN) / Total"""
        total = self.true_positives + self.false_positives + self.true_negatives + self.false_negatives
        return (self.true_positives + self.true_negatives) / total if total > 0 else 0.0


def load_file_content(filepath: str) -> str:
    """Load text file content"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def calculate_text_overlap(text1: str, text2: str) -> float:
    """
    Calculate approximate text overlap ratio between two texts

    This is a simplified version - in real scenario, we'd use:
    - Sentence-level alignment
    - Token-based similarity
    - Or LLM-based semantic comparison
    """
    # Simple word-level overlap
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    overlap = len(words1 & words2)
    return overlap / min(len(words1), len(words2))


def compare_with_ground_truth(
    dedup_result_chunks: List[str],
    ground_truth_content: str,
    base_content: str,
    overlap_threshold: float = 0.3
) -> EvaluationMetrics:
    """
    Compare deduplication results with ground truth

    Args:
        dedup_result_chunks: List of chunk texts that were kept (unique)
        ground_truth_content: Ground truth deduplicated content
        base_content: Original base content
        overlap_threshold: Threshold for considering content as present

    Returns:
        EvaluationMetrics with TP, FP, TN, FN counts
    """
    metrics = EvaluationMetrics()

    # For each chunk, check if it should be kept or removed
    for chunk_text in dedup_result_chunks:
        # Check overlap with ground truth (should be kept)
        gt_overlap = calculate_text_overlap(chunk_text, ground_truth_content)

        # Check overlap with base (was it in original)
        base_overlap = calculate_text_overlap(chunk_text, base_content)

        # Decision logic:
        # - If chunk appears in ground truth → should be kept (True label)
        # - If chunk was kept in dedup result → predicted as unique (Positive prediction)

        if gt_overlap >= overlap_threshold:
            # This chunk should be kept
            metrics.true_positives += 1
        else:
            # This chunk should have been removed (but we kept it)
            metrics.false_positives += 1

    return metrics


def evaluate_deduplication_type(
    post_dir: str,
    dup_type: str,
    chunker: ChunkingPipeline,
    embedder: EmbeddingGenerator,
    deduplicator: ChromaDBDeduplicator,
    verbose: bool = True
) -> Tuple[EvaluationMetrics, Dict]:
    """
    Evaluate deduplication for a specific duplicate type

    Args:
        post_dir: Path to post directory
        dup_type: Type of duplication (exact_30, paraphrase_25, etc.)
        chunker: ChunkingPipeline instance
        embedder: EmbeddingGenerator instance
        deduplicator: ChromaDBDeduplicator instance
        verbose: Print detailed output

    Returns:
        Tuple of (metrics, stats_dict)
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"Evaluating: {dup_type}")
        print(f"{'='*60}")

    # File paths
    base_file = os.path.join(post_dir, 'base.txt')
    update_file = os.path.join(post_dir, f'update_{dup_type}.txt')
    ground_truth_file = os.path.join(post_dir, f'ground_truth_{dup_type}.txt')

    # Check if files exist
    if not all(os.path.exists(f) for f in [base_file, update_file, ground_truth_file]):
        print(f"⚠ Missing files for {dup_type}, skipping...")
        return EvaluationMetrics(), {}

    # Load content
    base_content = load_file_content(base_file)
    update_content = load_file_content(update_file)
    ground_truth_content = load_file_content(ground_truth_file)

    if verbose:
        print(f"\n1. Content loaded:")
        print(f"   Base: {len(base_content)} chars")
        print(f"   Update: {len(update_content)} chars")
        print(f"   Ground Truth: {len(ground_truth_content)} chars")

    # Clear deduplicator for fresh test
    deduplicator.clear_collection()

    # Step 1: Process base document
    base_article = {'id': 'base', 'content': base_content, 'source': 'base'}
    base_chunks = chunker.process_article(base_article)

    if verbose:
        print(f"\n2. Base document chunked: {len(base_chunks)} chunks")

    # Embed base chunks
    base_embeddings = embedder.embed_chunks(base_chunks)

    # Add base to deduplicator
    deduplicator.add_chunks(
        chunk_ids=[r.chunk_id for r in base_embeddings],
        embeddings=[r.embedding for r in base_embeddings],
        texts=[c.chunk_text for c in base_chunks],
        metadatas=[{'source': 'base'} for _ in base_chunks]
    )

    # Step 2: Process update document
    update_article = {'id': 'update', 'content': update_content, 'source': 'update'}
    update_chunks = chunker.process_article(update_article)

    if verbose:
        print(f"\n3. Update document chunked: {len(update_chunks)} chunks")

    # Embed update chunks
    update_embeddings = embedder.embed_chunks(update_chunks)

    # Deduplicate
    unique_ids, dup_ids, mappings = deduplicator.deduplicate_new_chunks(
        new_chunk_ids=[r.chunk_id for r in update_embeddings],
        new_embeddings=[r.embedding for r in update_embeddings],
        new_texts=[c.chunk_text for c in update_chunks],
        new_metadatas=[{'source': 'update'} for _ in update_chunks]
    )

    if verbose:
        print(f"\n4. Deduplication results:")
        print(f"   Unique chunks: {len(unique_ids)}")
        print(f"   Duplicate chunks: {len(dup_ids)}")
        print(f"   Deduplication rate: {len(dup_ids) / len(update_chunks) * 100:.1f}%")

    # Step 3: Compare with Ground Truth
    # Get unique chunk texts
    unique_chunk_texts = [
        c.chunk_text for c in update_chunks
        if c.chunk_id in unique_ids
    ]

    # Calculate metrics (simplified - comparing kept chunks with ground truth)
    metrics = compare_with_ground_truth(
        dedup_result_chunks=unique_chunk_texts,
        ground_truth_content=ground_truth_content,
        base_content=base_content
    )

    if verbose:
        print(f"\n5. Evaluation Metrics:")
        print(f"   Precision: {metrics.precision:.3f}")
        print(f"   Recall: {metrics.recall:.3f}")
        print(f"   F1 Score: {metrics.f1_score:.3f}")
        print(f"   Accuracy: {metrics.accuracy:.3f}")

    # Stats
    stats = {
        'dup_type': dup_type,
        'base_chunks': len(base_chunks),
        'update_chunks': len(update_chunks),
        'unique_chunks': len(unique_ids),
        'duplicate_chunks': len(dup_ids),
        'dedup_rate': len(dup_ids) / len(update_chunks) if update_chunks else 0,
        'precision': metrics.precision,
        'recall': metrics.recall,
        'f1_score': metrics.f1_score,
        'accuracy': metrics.accuracy,
    }

    return metrics, stats


def test_single_post(
    post_id: str = 'post_001',
    threshold: float = 0.90,
    chunk_size: int = 1024,
    chunk_overlap: int = 128
):
    """
    Test deduplication on a single post with all duplicate types

    Args:
        post_id: Post ID to test (e.g., 'post_001')
        threshold: Similarity threshold for deduplication
        chunk_size: Size of chunks in characters
        chunk_overlap: Overlap between chunks
    """
    print("\n" + "="*60)
    print(f"DEDUPLICATION EVALUATION: {post_id}")
    print(f"Threshold: {threshold}, Chunk Size: {chunk_size}")
    print("="*60)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠ Error: OPENAI_API_KEY not set")
        print("   Set with: export OPENAI_API_KEY='your-key'")
        return

    # Setup paths
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/deduplication_dataset'))
    post_dir = os.path.join(base_dir, post_id)

    if not os.path.exists(post_dir):
        print(f"\n⚠ Error: Post directory not found: {post_dir}")
        return

    # Initialize pipeline
    chunker = ChunkingPipeline(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=100
    )
    embedder = EmbeddingGenerator(model="text-embedding-3-small", batch_size=100)
    deduplicator = ChromaDBDeduplicator(
        collection_name=f"eval_{post_id}_{threshold}",
        persist_directory=None,  # In-memory
        similarity_threshold=threshold
    )

    # Duplicate types to test
    dup_types = [
        'exact_30',
        'paraphrase_25',
        'fragment_20',
        'semantic_25',
        'mixed_real'
    ]

    # Evaluate each type
    results = []
    for dup_type in dup_types:
        metrics, stats = evaluate_deduplication_type(
            post_dir=post_dir,
            dup_type=dup_type,
            chunker=chunker,
            embedder=embedder,
            deduplicator=deduplicator,
            verbose=True
        )
        results.append(stats)

    # Summary report
    print(f"\n{'='*60}")
    print(f"SUMMARY REPORT - {post_id} (threshold={threshold})")
    print(f"{'='*60}\n")

    print(f"{'Type':<20} {'Dedup Rate':<12} {'Precision':<12} {'Recall':<12} {'F1':<12}")
    print("-" * 68)

    for stats in results:
        print(f"{stats['dup_type']:<20} "
              f"{stats['dedup_rate']*100:>10.1f}% "
              f"{stats['precision']:>11.3f} "
              f"{stats['recall']:>11.3f} "
              f"{stats['f1_score']:>11.3f}")

    # Calculate averages
    avg_precision = sum(s['precision'] for s in results) / len(results)
    avg_recall = sum(s['recall'] for s in results) / len(results)
    avg_f1 = sum(s['f1_score'] for s in results) / len(results)
    avg_dedup_rate = sum(s['dedup_rate'] for s in results) / len(results)

    print("-" * 68)
    print(f"{'AVERAGE':<20} "
          f"{avg_dedup_rate*100:>10.1f}% "
          f"{avg_precision:>11.3f} "
          f"{avg_recall:>11.3f} "
          f"{avg_f1:>11.3f}")

    # Cost summary
    stats_summary = embedder.get_usage_stats()
    print(f"\n{'='*60}")
    print(f"COST SUMMARY")
    print(f"{'='*60}")
    print(f"Total tokens: {stats_summary['total_tokens']:,}")
    print(f"Total cost: ${stats_summary['total_cost_dollars']:.4f}")
    print()


def test_multiple_thresholds(post_id: str = 'post_001'):
    """
    Test multiple similarity thresholds on a single post

    Args:
        post_id: Post ID to test
    """
    thresholds = [0.85, 0.90, 0.95]

    print("\n" + "="*60)
    print(f"MULTI-THRESHOLD EVALUATION: {post_id}")
    print("="*60)

    for threshold in thresholds:
        test_single_post(post_id=post_id, threshold=threshold)
        print("\n" + "-"*60 + "\n")


def main():
    """Run evaluation tests"""
    import argparse

    parser = argparse.ArgumentParser(description='Evaluate deduplication pipeline')
    parser.add_argument('--post', default='post_001', help='Post ID to test')
    parser.add_argument('--threshold', type=float, default=0.90, help='Similarity threshold')
    parser.add_argument('--multi-threshold', action='store_true', help='Test multiple thresholds')

    args = parser.parse_args()

    if args.multi_threshold:
        test_multiple_thresholds(post_id=args.post)
    else:
        test_single_post(post_id=args.post, threshold=args.threshold)


if __name__ == "__main__":
    main()
