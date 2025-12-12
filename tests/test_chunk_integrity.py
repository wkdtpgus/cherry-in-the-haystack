#!/usr/bin/env python3
"""문단 청킹 무결성 테스트 - 내용이 끊기거나 누락되는지 확인"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.parser import extract_page_text
from src.pdf.chunker import split_paragraphs


def check_sentence_integrity(chunks):
    """각 문단이 완전한 문장으로 끝나는지 확인"""
    issues = []

    for idx, chunk in enumerate(chunks):
        # 마지막 문자 확인
        last_char = chunk.strip()[-1] if chunk.strip() else ""

        # 문장 종결 부호가 아니면 경고
        if last_char not in ['.', '!', '?', ':', '"', "'", ')', ']']:
            issues.append({
                'chunk_idx': idx,
                'last_chars': chunk.strip()[-50:],
                'issue': 'incomplete_sentence'
            })

    return issues


def check_content_coverage(original_text, chunks):
    """청킹 후 원본 대비 내용 손실 확인"""
    # 원본 정규화
    original_normalized = original_text.replace('\n', ' ').replace('  ', ' ').strip()
    original_length = len(original_normalized)

    # 청크 합친 것 정규화
    chunks_combined = ' '.join(chunks)
    chunks_length = len(chunks_combined)

    # 손실률 계산
    coverage = (chunks_length / original_length) * 100 if original_length > 0 else 0
    loss_percentage = 100 - coverage

    return {
        'original_length': original_length,
        'chunks_length': chunks_length,
        'coverage_percentage': coverage,
        'loss_percentage': loss_percentage,
    }


def show_chunk_boundaries(chunks):
    """문단 경계 부분 확인 (끝 50자 + 다음 시작 50자)"""
    print("\n" + "="*100)
    print("📍 문단 경계 확인 (끊김 여부)")
    print("="*100)

    for idx in range(len(chunks) - 1):
        current_end = chunks[idx].strip()[-80:]
        next_start = chunks[idx + 1].strip()[:80:]

        print(f"\n[문단 {idx+1} → 문단 {idx+2}]")
        print("-"*100)
        print(f"문단 {idx+1} 끝: ...{current_end}")
        print(f"문단 {idx+2} 시작: {next_start}...")

        # 마지막 문자 확인
        last_char = chunks[idx].strip()[-1]
        if last_char not in ['.', '!', '?', ':']:
            print(f"⚠️  경고: 문단 {idx+1}이 문장 중간에서 끊김 (마지막 문자: '{last_char}')")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="문단 청킹 무결성 테스트")
    parser.add_argument("--pdf", type=str, default="AI Engineering.pdf")
    parser.add_argument("--page", type=int, default=100)
    parser.add_argument("--show-boundaries", action="store_true", help="문단 경계 표시")

    args = parser.parse_args()

    print(f"\n{'='*100}")
    print(f"📋 문단 청킹 무결성 테스트")
    print(f"{'='*100}")
    print(f"📄 PDF: {args.pdf}")
    print(f"📍 페이지: {args.page + 1}\n")

    # Extract and chunk
    page_text = extract_page_text(args.pdf, args.page)
    chunks = split_paragraphs(page_text)

    print(f"원본 텍스트 길이: {len(page_text)} 글자")
    print(f"추출된 문단 수: {len(chunks)}")

    # 1. 문장 완결성 확인
    print(f"\n{'='*100}")
    print("1️⃣  문장 완결성 검사")
    print(f"{'='*100}")

    integrity_issues = check_sentence_integrity(chunks)

    if not integrity_issues:
        print("✅ 모든 문단이 완전한 문장으로 끝납니다.")
    else:
        print(f"⚠️  {len(integrity_issues)}개 문단에서 불완전한 문장 종결 발견:")
        for issue in integrity_issues:
            print(f"\n   문단 {issue['chunk_idx'] + 1}:")
            print(f"   끝부분: ...{issue['last_chars']}")

    # 2. 내용 손실률 확인
    print(f"\n{'='*100}")
    print("2️⃣  내용 손실률 검사")
    print(f"{'='*100}")

    coverage = check_content_coverage(page_text, chunks)

    print(f"원본 길이: {coverage['original_length']:,} 글자")
    print(f"청크 길이: {coverage['chunks_length']:,} 글자")
    print(f"커버리지: {coverage['coverage_percentage']:.1f}%")
    print(f"손실률: {coverage['loss_percentage']:.1f}%")

    if coverage['loss_percentage'] < 5:
        print("✅ 내용 손실이 거의 없습니다 (< 5%)")
    elif coverage['loss_percentage'] < 10:
        print("⚠️  약간의 내용 손실이 있습니다 (5-10%)")
    else:
        print("❌ 심각한 내용 손실이 있습니다 (> 10%)")

    # 3. 문단별 상세 정보
    print(f"\n{'='*100}")
    print("3️⃣  문단별 상세 정보")
    print(f"{'='*100}")

    for idx, chunk in enumerate(chunks):
        last_sentence = chunk.split('.')[-2] if '.' in chunk else chunk[-100:]
        first_sentence = chunk.split('.')[0] if '.' in chunk else chunk[:100]

        print(f"\n[문단 {idx+1}] {len(chunk)} 글자")
        print(f"   시작: {first_sentence[:80]}...")
        print(f"   끝: ...{last_sentence[-80:]}")

    # 4. 문단 경계 확인 (옵션)
    if args.show_boundaries and len(chunks) > 1:
        show_chunk_boundaries(chunks)

    # 최종 결과
    print(f"\n{'='*100}")
    print("📊 최종 평가")
    print(f"{'='*100}")

    all_good = True

    if integrity_issues:
        print(f"⚠️  {len(integrity_issues)}개 문단에서 불완전한 종결")
        all_good = False
    else:
        print("✅ 문장 완결성: 통과")

    if coverage['loss_percentage'] < 5:
        print("✅ 내용 손실률: 통과 (< 5%)")
    else:
        print(f"⚠️  내용 손실률: {coverage['loss_percentage']:.1f}%")
        all_good = False

    if all_good:
        print("\n🎉 모든 검사 통과! 청킹이 안전하게 동작합니다.")
    else:
        print("\n⚠️  일부 문제가 발견되었습니다. 위 내용을 확인하세요.")

    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
