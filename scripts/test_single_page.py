#!/usr/bin/env python3
"""단일 페이지 DB 저장 테스트 - 로컬 SQLite"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.parser import extract_page_text, get_pdf_metadata
from src.pdf.chunker import split_paragraphs
from src.db.connection import get_session
from src.db.operations import create_book, get_book_by_title
from src.model.schemas import ParagraphChunk
from src.workflow.state import State
from src.workflow.nodes import extract_core_idea, save_to_database


def test_single_page(pdf_path: str, page_num: int = 100):
    """단일 페이지를 DB에 저장하는 테스트"""

    print("=" * 80)
    print("📋 로컬 SQLite 단일 페이지 저장 테스트")
    print("=" * 80)
    print(f"📄 PDF: {pdf_path}")
    print(f"📍 페이지: {page_num + 1}")
    print(f"💾 DB: local_dev.db (SQLite)")
    print()

    session = get_session()

    try:
        # 1. Book 확인/생성
        metadata = get_pdf_metadata(pdf_path)
        book = get_book_by_title(session, metadata["title"])

        if book:
            print(f"✅ 기존 Book 사용: '{book.title}' (ID: {book.id})")
        else:
            book = create_book(
                session,
                title=metadata["title"],
                author=metadata["author"],
                source_path=pdf_path
            )
            print(f"✅ 새 Book 생성: '{book.title}' (ID: {book.id})")

        # 2. 페이지 추출
        print(f"\n📖 페이지 {page_num + 1} 추출 중...")
        page_text = extract_page_text(pdf_path, page_num)

        # 3. 문단 분리
        paragraphs = split_paragraphs(page_text)
        print(f"📝 {len(paragraphs)}개 문단 발견")

        # 4. 각 문단 처리
        saved_count = 0
        for idx, para_text in enumerate(paragraphs):
            print(f"\n[문단 {idx + 1}/{len(paragraphs)}]")
            print(f"  길이: {len(para_text)} 글자")
            print(f"  미리보기: {para_text[:60]}...")

            # State 생성
            chunk = ParagraphChunk(
                page_number=page_num,
                paragraph_index=idx,
                body_text=para_text
            )

            state = State(
                chunk=chunk,
                book_id=book.id,
                model_version="gemini-2.5-flash"
            )

            # LLM 추출
            print(f"  ⚡ LLM 추출 중...", end=" ")
            state = extract_core_idea(state)

            if state.error:
                print(f"❌ 오류: {state.error}")
                continue

            print(f"✅")
            print(f"  🏷️  Core Idea: {state.result.concept or '(없음)'}")

            # DB 저장
            print(f"  💾 DB 저장 중...", end=" ")
            state = save_to_database(state)

            if state.error:
                print(f"❌ 오류: {state.error}")
                continue

            print(f"✅ (chunk_id: {state.chunk_id})")
            saved_count += 1

        # 5. 결과 요약
        print("\n" + "=" * 80)
        print("✅ 테스트 완료")
        print("=" * 80)
        print(f"📚 Book ID: {book.id}")
        print(f"📄 처리 페이지: {page_num + 1}")
        print(f"📝 총 문단: {len(paragraphs)}")
        print(f"💾 저장 성공: {saved_count}")
        print("=" * 80)

        # 6. DB 확인
        print("\n🔍 DB 확인:")
        from src.db.models import ParagraphChunk as DBChunk, KeyIdea

        chunks = session.query(DBChunk).filter_by(
            book_id=book.id,
            page_number=page_num
        ).all()

        print(f"  - paragraph_chunks: {len(chunks)}개 레코드")

        ideas = session.query(KeyIdea).filter_by(book_id=book.id).all()
        print(f"  - key_ideas: {len(ideas)}개 레코드")

        if ideas:
            print(f"\n📊 추출된 Core Ideas:")
            core_ideas = set(idea.core_idea_text for idea in ideas if idea.core_idea_text)
            for core_idea in sorted(core_ideas):
                count = sum(1 for idea in ideas if idea.core_idea_text == core_idea)
                print(f"  - {core_idea}: {count}개")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="단일 페이지 DB 저장 테스트")
    parser.add_argument("--pdf", type=str, default="AI Engineering.pdf")
    parser.add_argument("--page", type=int, default=100, help="페이지 번호 (0부터 시작)")

    args = parser.parse_args()

    test_single_page(args.pdf, args.page)
