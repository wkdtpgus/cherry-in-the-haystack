#!/usr/bin/env python3
"""PostgreSQL 서버 파이프라인 테스트"""

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


def test_pg_pipeline(pdf_path: str, page_num: int = 10):
    """PostgreSQL 서버 파이프라인 테스트"""

    print("=" * 80)
    print("📋 PostgreSQL 서버 파이프라인 테스트")
    print("=" * 80)
    print(f"📄 PDF: {pdf_path}")
    print(f"📍 페이지: {page_num + 1}")
    print()

    session = get_session()

    try:
        # 1. Book 생성
        metadata = get_pdf_metadata(pdf_path)
        book = get_book_by_title(session, metadata["title"])

        if not book:
            book = create_book(
                session,
                title=metadata["title"],
                author=metadata["author"],
                source_path=pdf_path
            )
            print(f"✅ Book 생성: '{book.title}' (ID: {book.id})")
        else:
            print(f"✅ 기존 Book 사용: '{book.title}' (ID: {book.id})")

        # 2. 페이지 추출 및 처리
        page_text = extract_page_text(pdf_path, page_num)
        paragraphs = split_paragraphs(page_text)
        print(f"📝 {len(paragraphs)}개 문단 발견")

        # 3. 첫 번째 문단 처리
        if paragraphs:
            para_text = paragraphs[0]
            print(f"\n첫 번째 문단 처리 중...")
            print(f"문단 길이: {len(para_text)} 글자")

            chunk = ParagraphChunk(
                page_number=page_num,
                paragraph_index=0,
                body_text=para_text
            )

            state = State(
                chunk=chunk,
                book_id=book.id,
                model_version="gemini-2.5-flash"
            )

            # LLM 추출
            print(f"\n⚡ LLM 추출 중...", end=" ")
            state = extract_core_idea(state)

            if state.error:
                print(f"❌ 오류: {state.error}")
                return

            print(f"✅")
            print(f"🏷️  Core Idea: {state.result.concept}")

            # DB 저장
            print(f"\n💾 DB 저장 중...", end=" ")
            state = save_to_database(state)

            if state.error:
                print(f"❌ 오류: {state.error}")
                return

            print(f"✅ (chunk_id: {state.chunk_id})")

        print("\n" + "=" * 80)
        print("✅ PostgreSQL 파이프라인 테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PostgreSQL 파이프라인 테스트")
    parser.add_argument("--pdf", type=str, default="AI Engineering.pdf", help="PDF 파일 경로")
    parser.add_argument("--page", type=int, default=10, help="페이지 번호 (0부터 시작)")

    args = parser.parse_args()

    test_pg_pipeline(args.pdf, args.page)
