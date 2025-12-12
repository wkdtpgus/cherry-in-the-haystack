"""Test single page processing to verify end-to-end pipeline."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.parser import extract_page_text, get_pdf_metadata
from src.pdf.chunker import split_paragraphs
from src.model.schemas import ParagraphChunk
from src.workflow.state import State
from src.workflow.nodes import extract_core_idea, save_to_database
from src.db.connection import get_session
from src.db.models import Book
from src.db.operations import create_book


def test_single_page_processing():
    """Test processing a single page end-to-end."""

    pdf_path = "AI Engineering.pdf"
    page_num = 10  # Test with page 10

    print(f"\n{'='*60}")
    print(f"Testing Single Page Processing")
    print(f"{'='*60}")

    # 1. Get PDF metadata
    print(f"\n1. Getting PDF metadata...")
    metadata = get_pdf_metadata(pdf_path)
    print(f"   Title: {metadata['title']}")
    print(f"   Author: {metadata['author']}")
    print(f"   Total pages: {metadata['total_pages']}")

    # 2. Create book record
    print(f"\n2. Creating book record...")
    session = get_session()
    try:
        book = create_book(
            session,
            title=metadata["title"],
            author=metadata["author"],
            source_path=pdf_path,
        )
        print(f"   Created book ID: {book.id}")

        # 3. Extract page text
        print(f"\n3. Extracting text from page {page_num}...")
        page_text = extract_page_text(pdf_path, page_num)
        print(f"   Page text length: {len(page_text)} characters")

        # 4. Split into paragraphs
        print(f"\n4. Splitting into paragraphs...")
        paragraphs = split_paragraphs(page_text)
        print(f"   Found {len(paragraphs)} paragraphs")

        # 5. Process first paragraph
        if paragraphs:
            print(f"\n5. Processing first paragraph...")
            para_text = paragraphs[0]
            print(f"   Paragraph text: {para_text[:100]}...")

            # Create chunk
            chunk = ParagraphChunk(
                page_number=page_num,
                paragraph_index=0,
                body_text=para_text,
            )

            # Create state
            state = State(
                chunk=chunk,
                book_id=book.id,
                model_version="gemini-2.5-flash",
            )

            # Extract core idea
            print(f"\n6. Extracting core idea with LLM...")
            state = extract_core_idea(state)

            if state.error:
                print(f"   ❌ Error: {state.error}")
                return

            print(f"   ✅ Extracted:")
            print(f"      Core Idea: {state.result.concept}")

            # Save to database
            print(f"\n7. Saving to database...")
            state = save_to_database(state)

            if state.error:
                print(f"   ❌ Error: {state.error}")
                return

            print(f"   ✅ Saved successfully!")
            print(f"      Chunk ID: {state.chunk_id}")

        print(f"\n{'='*60}")
        print(f"✅ Single Page Test Complete!")
        print(f"{'='*60}\n")

    finally:
        session.close()


if __name__ == "__main__":
    test_single_page_processing()
