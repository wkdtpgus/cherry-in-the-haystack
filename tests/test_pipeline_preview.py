#!/usr/bin/env python3
"""파이프라인 미리보기 테스트 - DB 저장 전 각 단계 확인

PDF 처리 파이프라인의 각 단계가 잘 동작하는지 확인:
1. PDF 메타데이터 추출
2. 페이지 텍스트 추출
3. 문단 분리
4. 핵심 아이디어 추출 (LLM)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.parser import extract_page_text, get_pdf_metadata
from src.pdf.chunker import split_paragraphs, get_paragraph_stats
from src.model.schemas import ParagraphChunk
from src.workflow.state import State
from src.workflow.nodes import extract_core_idea


def print_section(title):
    """섹션 구분선 출력"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")


def test_metadata(pdf_path):
    """1단계: PDF 메타데이터 확인"""
    print_section("1️⃣  PDF 메타데이터 확인")

    metadata = get_pdf_metadata(pdf_path)

    print(f"📚 제목: {metadata['title']}")
    print(f"✍️  저자: {metadata['author']}")
    print(f"📄 총 페이지: {metadata['total_pages']}")
    print(f"🛠️  생성 도구: {metadata['creator']}")
    print(f"📦 PDF 생성기: {metadata['producer']}")

    return metadata


def test_page_extraction(pdf_path, page_num=30):
    """2단계: 페이지 텍스트 추출 확인"""
    print_section(f"2️⃣  페이지 {page_num+1} 텍스트 추출 확인")

    page_text = extract_page_text(pdf_path, page_num)

    print(f"📊 추출된 텍스트 길이: {len(page_text)} 글자")
    print(f"\n📝 텍스트 미리보기 (처음 500자):")
    print("-" * 80)
    print(page_text[:500])
    print("-" * 80)

    return page_text


def test_paragraph_splitting(page_text, show_full=False):
    """3단계: 문단 분리 확인"""
    print_section("3️⃣  문단 분리 확인")

    paragraphs = split_paragraphs(page_text)
    stats = get_paragraph_stats(paragraphs)

    print(f"📊 통계:")
    print(f"   - 총 문단 수: {stats['count']}")
    print(f"   - 평균 길이: {stats['avg_length']:.0f} 글자")
    print(f"   - 최소 길이: {stats['min_length']} 글자")
    print(f"   - 최대 길이: {stats['max_length']} 글자")
    print(f"   - 총 글자 수: {stats['total_chars']} 글자")

    if show_full:
        print(f"\n📝 전체 문단 내용:")
        for idx, para in enumerate(paragraphs):
            print(f"\n{'='*100}")
            print(f"[문단 {idx+1}/{len(paragraphs)}] ({len(para)} 글자)")
            print(f"{'='*100}")
            print(para)
    else:
        print(f"\n📝 각 문단 미리보기:")
        for idx, para in enumerate(paragraphs):
            preview = para[:100].replace('\n', ' ')
            print(f"\n   [{idx+1}] ({len(para)} 글자)")
            print(f"       {preview}...")

    return paragraphs


def test_idea_extraction(paragraphs, page_num, max_paragraphs=3):
    """4단계: 핵심 아이디어 추출 확인 (LLM)"""
    print_section("4️⃣  핵심 아이디어 추출 확인 (LLM)")

    print(f"⚡ 처음 {min(max_paragraphs, len(paragraphs))}개 문단에 대해 LLM으로 핵심 아이디어 추출 중...\n")

    results = []

    for idx, para_text in enumerate(paragraphs[:max_paragraphs]):
        print(f"📍 문단 {idx+1}/{min(max_paragraphs, len(paragraphs))}")
        print(f"   텍스트: {para_text[:80].replace(chr(10), ' ')}...")

        # Create chunk
        chunk = ParagraphChunk(
            page_number=page_num,
            paragraph_index=idx,
            body_text=para_text,
        )

        # Create state
        state = State(
            chunk=chunk,
            book_id=None,  # DB 저장 안 함
            model_version="gemini-2.5-flash",
        )

        # Extract core idea
        state = extract_core_idea(state)

        if state.error:
            print(f"   ❌ 오류: {state.error}\n")
            continue

        # Display results
        print(f"   ✅ 추출 완료:")
        print(f"      🏷️  Core Idea: {state.result.concept or '(없음)'}\n")

        results.append({
            'paragraph_index': idx,
            'core_idea': state.result.concept,
        })

    return results


def main():
    """메인 테스트 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="PDF 처리 파이프라인 미리보기")
    parser.add_argument("--pdf", type=str, default="AI Engineering.pdf", help="PDF 파일 경로")
    parser.add_argument("--page", type=int, default=30, help="테스트할 페이지 번호 (0부터 시작)")
    parser.add_argument("--max-paragraphs", type=int, default=3, help="LLM으로 추출할 최대 문단 수")
    parser.add_argument("--full", action="store_true", help="문단 전체 내용 표시")
    parser.add_argument("--no-llm", action="store_true", help="LLM 추출 건너뛰기 (문단만 확인)")

    args = parser.parse_args()

    print_section("🚀 PDF 처리 파이프라인 미리보기 테스트")
    print(f"📄 PDF: {args.pdf}")
    print(f"📍 페이지: {args.page + 1}")

    try:
        # 1. 메타데이터
        metadata = test_metadata(args.pdf)

        # 2. 페이지 추출
        page_text = test_page_extraction(args.pdf, args.page)

        # 3. 문단 분리
        paragraphs = test_paragraph_splitting(page_text, show_full=args.full)

        if not paragraphs:
            print("\n⚠️  추출된 문단이 없습니다. 다른 페이지를 시도해보세요.")
            return

        # 4. 핵심 아이디어 추출
        if args.no_llm:
            print_section("4️⃣  핵심 아이디어 추출 건너뛰기")
            print("ℹ️  --no-llm 옵션으로 LLM 추출을 건너뜁니다.")
            results = []
        else:
            results = test_idea_extraction(paragraphs, args.page, args.max_paragraphs)

        # 최종 요약
        print_section("✅ 테스트 완료 - 요약")
        print(f"📚 책: {metadata['title']}")
        print(f"📄 페이지: {args.page + 1}/{metadata['total_pages']}")
        print(f"📝 문단 수: {len(paragraphs)}")

        if not args.no_llm:
            print(f"💡 아이디어 추출: {len(results)}/{min(args.max_paragraphs, len(paragraphs))}")

            if results:
                print(f"\n🏷️  추출된 Core Ideas:")
                unique_core_ideas = set(r['core_idea'] for r in results if r['core_idea'])
                if unique_core_ideas:
                    for core_idea in unique_core_ideas:
                        print(f"   - {core_idea}")
                else:
                    print(f"   (Core Idea가 추출되지 않았습니다)")

        print(f"\n{'='*80}")
        print("🎉 모든 단계가 정상적으로 동작합니다!")
        print(f"{'='*80}\n")

    except FileNotFoundError:
        print(f"\n❌ 오류: PDF 파일을 찾을 수 없습니다: {args.pdf}")
        print(f"   현재 디렉토리: {os.getcwd()}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
