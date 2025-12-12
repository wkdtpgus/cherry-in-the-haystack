#!/usr/bin/env python3
"""PostgreSQL 연결 테스트 스크립트"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import get_database_url, create_db_engine, get_session
from src.db.models import Book


def test_connection():
    """PostgreSQL 연결 테스트"""

    print("=" * 80)
    print("PostgreSQL 연결 테스트")
    print("=" * 80)

    # 1. DATABASE_URL 확인
    db_url = get_database_url()
    print(f"\n✅ DATABASE_URL: {db_url}")

    # 2. Engine 생성
    try:
        engine = create_db_engine(echo=False)
        print(f"✅ Engine 생성 완료")
    except Exception as e:
        print(f"❌ Engine 생성 실패: {str(e)}")
        return

    # 3. Session 연결 테스트
    session = get_session()
    try:
        # Books 테이블 조회
        books = session.query(Book).all()
        print(f"✅ 연결 성공! Books 레코드 수: {len(books)}")

        # 첫 번째 Book 출력
        if books:
            print(f"\n📚 샘플 Book:")
            book = books[0]
            print(f"   ID: {book.id}")
            print(f"   Title: {book.title}")
            print(f"   Author: {book.author}")
        else:
            print(f"\n📚 Books 테이블이 비어있습니다.")

        print("\n" + "=" * 80)
        print("✅ PostgreSQL 연결 테스트 성공!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 연결 실패: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == "__main__":
    test_connection()
