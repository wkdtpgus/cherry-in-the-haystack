#!/usr/bin/env python3
"""문단 청킹 전략 실험 및 비교

다양한 청킹 전략을 테스트하여 최적의 방법 찾기
"""

import sys
import os
import re
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.parser import extract_page_text


def strategy_current(text: str) -> List[str]:
    """현재 전략: 이중 개행 기반"""
    MIN_LENGTH = 50
    MAX_LENGTH = 3000

    chunks = text.split("\n\n")
    chunks = [c.strip() for c in chunks if c.strip()]

    # Merge short chunks
    merged = []
    buffer = ""
    for chunk in chunks:
        normalized = re.sub(r"\s+", " ", chunk)
        if len(buffer) < MIN_LENGTH:
            buffer += " " + normalized if buffer else normalized
        else:
            merged.append(buffer)
            buffer = normalized
    if buffer and len(buffer) >= MIN_LENGTH:
        merged.append(buffer)

    # Split long chunks
    final = []
    for chunk in merged:
        if len(chunk) <= MAX_LENGTH:
            final.append(chunk)
        else:
            sentences = re.split(r"(?<=[.!?])\s+", chunk)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) <= MAX_LENGTH:
                    current += (" " if current else "") + sent
                else:
                    if current:
                        final.append(current.strip())
                    current = sent
            if current:
                final.append(current.strip())

    return [c for c in final if len(c) >= MIN_LENGTH]


def strategy_single_newline(text: str) -> List[str]:
    """전략 1: 단일 개행도 분리 기준"""
    MIN_LENGTH = 100
    MAX_LENGTH = 1500

    # Split by single newline
    chunks = text.split("\n")
    chunks = [c.strip() for c in chunks if c.strip()]

    # Merge until MIN_LENGTH
    merged = []
    buffer = ""
    for chunk in chunks:
        if len(buffer) == 0:
            buffer = chunk
        elif len(buffer) < MIN_LENGTH:
            buffer += " " + chunk
        else:
            merged.append(buffer)
            buffer = chunk
    if buffer and len(buffer) >= MIN_LENGTH:
        merged.append(buffer)

    # Split long chunks
    final = []
    for chunk in merged:
        if len(chunk) <= MAX_LENGTH:
            final.append(chunk)
        else:
            sentences = re.split(r"(?<=[.!?])\s+", chunk)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) <= MAX_LENGTH:
                    current += (" " if current else "") + sent
                else:
                    if current:
                        final.append(current.strip())
                    current = sent
            if current:
                final.append(current.strip())

    return [c for c in final if len(c) >= MIN_LENGTH]


def strategy_sentence_count(text: str) -> List[str]:
    """전략 2: 문장 개수 기반 (5-10문장)"""
    MIN_SENTENCES = 3
    MAX_SENTENCES = 8
    MIN_LENGTH = 100

    # Normalize text
    normalized = re.sub(r"\s+", " ", text).strip()

    # Split into sentences
    sentences = re.split(r"(?<=[.!?])\s+", normalized)

    chunks = []
    current = []

    for sent in sentences:
        current.append(sent)

        if len(current) >= MIN_SENTENCES:
            chunk_text = " ".join(current)
            if len(current) >= MAX_SENTENCES or len(chunk_text) >= 1500:
                if len(chunk_text) >= MIN_LENGTH:
                    chunks.append(chunk_text)
                current = []

    # Last chunk
    if current:
        chunk_text = " ".join(current)
        if len(chunk_text) >= MIN_LENGTH:
            chunks.append(chunk_text)

    return chunks


def strategy_hybrid(text: str) -> List[str]:
    """전략 3: 하이브리드 - 개행 + 문장 수 + 길이"""
    MIN_LENGTH = 150
    MAX_LENGTH = 1000
    TARGET_SENTENCES = 5

    # First split by double newlines (paragraphs)
    paragraphs = text.split("\n\n")

    chunks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Normalize whitespace
        normalized = re.sub(r"\s+", " ", para)

        # If paragraph is good size, keep it
        if MIN_LENGTH <= len(normalized) <= MAX_LENGTH:
            chunks.append(normalized)
        elif len(normalized) < MIN_LENGTH:
            # Too short - will merge later
            chunks.append(normalized)
        else:
            # Too long - split by sentences
            sentences = re.split(r"(?<=[.!?])\s+", normalized)
            current = []

            for sent in sentences:
                current.append(sent)
                chunk_text = " ".join(current)

                if len(current) >= TARGET_SENTENCES or len(chunk_text) >= MAX_LENGTH:
                    if len(chunk_text) >= MIN_LENGTH:
                        chunks.append(chunk_text)
                    current = []

            if current:
                chunk_text = " ".join(current)
                if len(chunk_text) >= MIN_LENGTH:
                    chunks.append(chunk_text)

    # Merge short chunks
    merged = []
    buffer = ""
    for chunk in chunks:
        if len(buffer) == 0:
            buffer = chunk
        elif len(buffer) < MIN_LENGTH:
            buffer += " " + chunk
        else:
            merged.append(buffer)
            buffer = chunk
    if buffer and len(buffer) >= MIN_LENGTH:
        merged.append(buffer)

    return merged


def strategy_smart_semantic(text: str) -> List[str]:
    """전략 4: 스마트 의미 기반 - 문단 구조 + 문맥"""
    MIN_LENGTH = 200
    MAX_LENGTH = 800

    # Remove footnote numbers at start of lines
    text = re.sub(r'^\d+\s+', '', text, flags=re.MULTILINE)

    # Split by double newlines first
    blocks = text.split("\n\n")

    chunks = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Normalize
        normalized = re.sub(r"\s+", " ", block)

        # Check if it's a short header/title (merge with next)
        if len(normalized) < 80 and not normalized.endswith(('.', '!', '?', ':')):
            chunks.append(("header", normalized))
            continue

        chunks.append(("content", normalized))

    # Merge headers with following content
    merged = []
    i = 0
    while i < len(chunks):
        chunk_type, chunk_text = chunks[i]

        if chunk_type == "header" and i + 1 < len(chunks):
            next_type, next_text = chunks[i + 1]
            merged.append(chunk_text + " " + next_text)
            i += 2
        else:
            merged.append(chunk_text)
            i += 1

    # Handle length constraints
    final = []
    buffer = ""

    for chunk in merged:
        if len(buffer) == 0:
            buffer = chunk
        elif len(buffer) < MIN_LENGTH:
            buffer += " " + chunk
        elif len(buffer) >= MIN_LENGTH and len(buffer) <= MAX_LENGTH:
            final.append(buffer)
            buffer = chunk
        else:
            # Buffer too long, split it
            sentences = re.split(r"(?<=[.!?])\s+", buffer)
            current = ""
            for sent in sentences:
                if len(current) + len(sent) <= MAX_LENGTH:
                    current += (" " if current else "") + sent
                else:
                    if current and len(current) >= MIN_LENGTH:
                        final.append(current.strip())
                    current = sent
            if current and len(current) >= MIN_LENGTH:
                final.append(current.strip())
            buffer = chunk

    if buffer and len(buffer) >= MIN_LENGTH:
        final.append(buffer)

    return final


def analyze_chunks(chunks: List[str], strategy_name: str) -> Dict:
    """청크 분석"""
    if not chunks:
        return {
            "strategy": strategy_name,
            "count": 0,
            "avg_length": 0,
            "min_length": 0,
            "max_length": 0,
            "total_chars": 0,
        }

    lengths = [len(c) for c in chunks]

    return {
        "strategy": strategy_name,
        "count": len(chunks),
        "avg_length": sum(lengths) / len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "total_chars": sum(lengths),
    }


def print_comparison(results: List[Dict]):
    """결과 비교 출력"""
    print("\n" + "="*100)
    print("청킹 전략 비교 결과")
    print("="*100)

    print(f"\n{'전략':<25} {'문단수':>8} {'평균길이':>10} {'최소':>8} {'최대':>8} {'총글자':>10}")
    print("-"*100)

    for r in results:
        print(f"{r['strategy']:<25} {r['count']:>8} {r['avg_length']:>10.0f} {r['min_length']:>8} {r['max_length']:>8} {r['total_chars']:>10}")

    print("-"*100)


def show_samples(page_text: str, strategy_func, strategy_name: str, max_samples=3):
    """샘플 청크 미리보기"""
    chunks = strategy_func(page_text)

    print(f"\n{'='*100}")
    print(f"📋 {strategy_name} - 샘플 미리보기")
    print(f"{'='*100}")

    for idx, chunk in enumerate(chunks[:max_samples]):
        print(f"\n[문단 {idx+1}/{len(chunks)}] ({len(chunk)} 글자)")
        print("-"*100)
        preview = chunk[:200] + ("..." if len(chunk) > 200 else "")
        print(preview)


def main():
    """메인 실험"""
    import argparse

    parser = argparse.ArgumentParser(description="청킹 전략 실험")
    parser.add_argument("--pdf", type=str, default="AI Engineering.pdf")
    parser.add_argument("--page", type=int, default=100)
    parser.add_argument("--show-samples", action="store_true", help="샘플 미리보기 표시")

    args = parser.parse_args()

    print(f"\n{'='*100}")
    print(f"📄 PDF: {args.pdf}, 페이지: {args.page + 1}")
    print(f"{'='*100}")

    # Extract page
    page_text = extract_page_text(args.pdf, args.page)
    print(f"\n원본 텍스트 길이: {len(page_text)} 글자")

    # Test strategies
    strategies = [
        (strategy_current, "현재 전략 (이중개행)"),
        (strategy_single_newline, "전략1: 단일개행"),
        (strategy_sentence_count, "전략2: 문장개수 기반"),
        (strategy_hybrid, "전략3: 하이브리드"),
        (strategy_smart_semantic, "전략4: 스마트 의미기반"),
    ]

    results = []
    for func, name in strategies:
        chunks = func(page_text)
        stats = analyze_chunks(chunks, name)
        results.append(stats)

    # Compare
    print_comparison(results)

    # Show samples
    if args.show_samples:
        for func, name in strategies:
            show_samples(page_text, func, name, max_samples=2)

    # Recommendation
    print(f"\n{'='*100}")
    print("💡 권장사항")
    print(f"{'='*100}")

    # Find best strategy (good balance of count and length)
    valid_results = [r for r in results if r['count'] > 0]

    if valid_results:
        # 문단 수가 적절하고 (3-10개), 평균 길이가 적당한 (300-700자) 전략 찾기
        scored = []
        for r in valid_results:
            score = 0
            # Prefer 3-10 chunks
            if 3 <= r['count'] <= 10:
                score += 10
            elif r['count'] > 1:
                score += 5

            # Prefer avg length 300-700
            if 300 <= r['avg_length'] <= 700:
                score += 10
            elif 200 <= r['avg_length'] <= 1000:
                score += 5

            # Penalize too much variance
            if r['max_length'] - r['min_length'] < 800:
                score += 5

            scored.append((score, r))

        scored.sort(reverse=True, key=lambda x: x[0])
        best = scored[0][1]

        print(f"\n🏆 최적 전략: {best['strategy']}")
        print(f"   - 문단 수: {best['count']}")
        print(f"   - 평균 길이: {best['avg_length']:.0f} 글자")
        print(f"   - 범위: {best['min_length']}-{best['max_length']} 글자")
        print(f"\n   이 전략이 적절한 문단 수와 길이의 균형을 제공합니다.")

    print(f"\n{'='*100}\n")


if __name__ == "__main__":
    main()
