#!/usr/bin/env python3
"""소규모 배치 처리 테스트 - 10페이지만"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.parser import extract_pages_lazy, get_pdf_metadata
from src.pdf.chunker import split_paragraphs
from src.db.connection import get_session
from src.db.operations import create_book, get_book_by_title
from src.model.schemas import ParagraphChunk
from src.workflow.state import State
from src.workflow.nodes import extract_core_idea, save_to_database
from tqdm import tqdm


def test_batch(pdf_path: str, start_page: int = 100, num_pages: int = 10):
    """소규모 배치 처리"""

    print("=" * 80)
    print(f"📋 소규모 배치 처리 테스트 ({num_pages}페이지)")
    print("=" * 80)
    print(f"📄 PDF: {pdf_path}")
    print(f"📍 페이지: {start_page + 1} ~ {start_page + num_pages}")
    print(f"💾 DB: local_dev.db (SQLite)")
    print()

    session = get_session()

    try:
        # Book 확인/생성
        metadata = get_pdf_metadata(pdf_path)
        book = get_book_by_title(session, metadata["title"])

        if not book:
            book = create_book(
                session,
                title=metadata["title"],
                author=metadata["author"],
                source_path=pdf_path,
                total_pages=metadata["total_pages"]
            )
            print(f"✅ Book 생성: '{book.title}' (ID: {book.id})")
        else:
            print(f"✅ Book 사용: '{book.title}' (ID: {book.id})")

        # 통계
        stats = {
            "total_pages": 0,
            "total_paragraphs": 0,
            "total_ideas": 0,
            "failed": 0,
        }

        # 페이지 범위
        target_pages = set(range(start_page, start_page + num_pages))

        print(f"\n🚀 {num_pages}페이지 처리 시작...\n")

        # 진행률 표시
        for page_num, page_text in tqdm(
            extract_pages_lazy(pdf_path),
            total=metadata["total_pages"],
            desc="Processing"
        ):
            if page_num not in target_pages:
                continue

            try:
                # 문단 분리
                paragraphs = split_paragraphs(page_text)

                if not paragraphs:
                    continue

                stats["total_pages"] += 1
                stats["total_paragraphs"] += len(paragraphs)

                # 각 문단 처리
                for para_idx, para_text in enumerate(paragraphs):
                    chunk = ParagraphChunk(
                        page_number=page_num,
                        paragraph_index=para_idx,
                        body_text=para_text
                    )

                    state = State(
                        chunk=chunk,
                        book_id=book.id,
                        model_version="gemini-2.5-flash"
                    )

                    # LLM 추출
                    state = extract_core_idea(state)
                    if state.error:
                        stats["failed"] += 1
                        continue

                    # DB 저장
                    state = save_to_database(state)
                    if state.error:
                        stats["failed"] += 1
                        continue

                    stats["total_ideas"] += 1

            except Exception as e:
                print(f"\n❌ 페이지 {page_num + 1} 오류: {str(e)}")
                stats["failed"] += 1

        # 결과
        print("\n" + "=" * 80)
        print("✅ 배치 처리 완료")
        print("=" * 80)
        print(f"📚 Book ID: {book.id}")
        print(f"📄 처리 페이지: {stats['total_pages']}")
        print(f"📝 총 문단: {stats['total_paragraphs']}")
        print(f"💾 저장 성공: {stats['total_ideas']}")
        print(f"❌ 실패: {stats['failed']}")
        print("=" * 80)

        # DB 통계
        from src.db.models import ParagraphChunk as DBChunk, KeyIdea

        total_chunks = session.query(DBChunk).filter_by(book_id=book.id).count()
        total_ideas = session.query(KeyIdea).filter_by(book_id=book.id).count()

        print(f"\n🔍 전체 DB 통계:")
        print(f"  - paragraph_chunks: {total_chunks}개")
        print(f"  - key_ideas: {total_ideas}개")

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="소규모 배치 처리 테스트")
    parser.add_argument("--pdf", type=str, default="AI Engineering.pdf")
    parser.add_argument("--start", type=int, default=100, help="시작 페이지 (0부터)")
    parser.add_argument("--count", type=int, default=10, help="처리할 페이지 수")

    args = parser.parse_args()

    test_batch(args.pdf, args.start, args.count)
