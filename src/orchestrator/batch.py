"""Batch PDF processing orchestrator.

Main entry point for processing PDFs page-by-page with progress tracking.
"""

import os
from typing import List
from tqdm import tqdm

from src.pdf.parser import extract_pages_lazy, get_pdf_metadata
from src.pdf.chunker import split_paragraphs
from src.db.connection import get_session
from src.db.operations import create_book, get_book_by_title
from src.db.progress import (
    initialize_progress,
    get_pending_pages,
    mark_page_processing,
    mark_page_completed,
    mark_page_failed,
    get_progress_stats,
    reset_stuck_pages,
)
from src.model.schemas import ParagraphChunk
from src.workflow.state import State
from src.workflow.nodes import extract_core_idea, save_to_database


def process_pdf(
    pdf_path: str,
    resume: bool = False,
    book_id: int = None,
    model_version: str = "gemini-2.5-flash",
) -> dict:
    """Process a PDF file page by page.

    Args:
        pdf_path: Path to PDF file
        resume: If True, resume from last checkpoint
        book_id: Book ID (for resume mode)
        model_version: LLM model version to record

    Returns:
        Dictionary with processing statistics
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    session = get_session()

    try:
        # 1. Get or create book record
        if resume and book_id:
            print(f"📖 Resuming book ID: {book_id}")
            book = session.query(
                __import__("src.db.models", fromlist=["Book"]).Book
            ).filter_by(id=book_id).first()

            if not book:
                raise ValueError(f"Book ID {book_id} not found")

            # Reset stuck pages
            stuck_count = reset_stuck_pages(session, book_id)
            if stuck_count > 0:
                print(f"⚠️  Reset {stuck_count} stuck pages to pending")

        else:
            # Create new book
            metadata = get_pdf_metadata(pdf_path)
            print(f"📖 Processing: {metadata['title']}")
            print(f"   Author: {metadata['author']}")
            print(f"   Total pages: {metadata['total_pages']}")

            # Check if already exists
            existing_book = get_book_by_title(session, metadata["title"])
            if existing_book:
                print(f"⚠️  Book '{metadata['title']}' already exists (ID: {existing_book.id})")
                print(f"   Use --resume --book-id {existing_book.id} to resume")
                session.close()
                return {"error": "Book already exists"}

            book = create_book(
                session,
                title=metadata["title"],
                author=metadata["author"],
                source_path=pdf_path,
            )
            print(f"✅ Created book record (ID: {book.id})")

            # Initialize progress tracking
            page_numbers = list(range(metadata["total_pages"]))
            initialize_progress(session, book.id, page_numbers)

        # 2. Get pages to process
        pending_pages = get_pending_pages(session, book.id)

        if not pending_pages:
            print("✅ All pages already processed!")
            stats = get_progress_stats(session, book.id)
            return stats

        print(f"\n🚀 Processing {len(pending_pages)} pages...")

        # 3. Process pages
        stats = {
            "total_pages": len(pending_pages),
            "completed": 0,
            "failed": 0,
            "total_paragraphs": 0,
            "total_ideas": 0,
        }

        # Create page number to index mapping for lazy loading
        page_nums_set = set(pending_pages)

        # Get total pages for tqdm
        total_pages = session.query(
            __import__("src.db.models", fromlist=["ProcessingProgress"]).ProcessingProgress
        ).filter_by(book_id=book.id).count()

        for page_num, page_text in tqdm(
            extract_pages_lazy(pdf_path),
            total=total_pages,
            desc="Processing pages",
        ):
            # Skip if not in pending list
            if page_num not in page_nums_set:
                continue

            try:
                # Mark as processing
                mark_page_processing(session, book.id, page_num)

                # Split into paragraphs
                paragraphs = split_paragraphs(page_text)

                if not paragraphs:
                    # No content, mark as completed
                    mark_page_completed(session, book.id, page_num)
                    stats["completed"] += 1
                    continue

                stats["total_paragraphs"] += len(paragraphs)

                # Process each paragraph
                for para_idx, para_text in enumerate(paragraphs):
                    # Create workflow state
                    chunk = ParagraphChunk(
                        page_number=page_num,
                        paragraph_index=para_idx,
                        body_text=para_text,
                    )

                    state = State(
                        chunk=chunk,
                        book_id=book.id,
                        model_version=model_version,
                    )

                    # Extract idea
                    state = extract_core_idea(state)

                    if state.error:
                        print(f"\n⚠️  Error on page {page_num+1}, para {para_idx}: {state.error}")
                        continue

                    # Save to database
                    state = save_to_database(state)

                    if state.error:
                        print(f"\n⚠️  DB error on page {page_num+1}, para {para_idx}: {state.error}")
                        continue

                    stats["total_ideas"] += 1

                # Mark page as completed
                mark_page_completed(session, book.id, page_num)
                stats["completed"] += 1

            except Exception as e:
                # Mark page as failed
                mark_page_failed(session, book.id, page_num, str(e))
                stats["failed"] += 1
                print(f"\n❌ Page {page_num+1} failed: {str(e)}")

        # 4. Print summary
        print("\n" + "=" * 60)
        print("Processing Summary")
        print("=" * 60)
        print(f"Total pages: {stats['total_pages']}")
        print(f"Completed: {stats['completed']}")
        print(f"Failed: {stats['failed']}")
        print(f"Total paragraphs: {stats['total_paragraphs']}")
        print(f"Total ideas extracted: {stats['total_ideas']}")
        print("=" * 60)

        return stats

    finally:
        session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch PDF processing")
    parser.add_argument("--pdf", type=str, required=True, help="Path to PDF file")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--book-id", type=int, help="Book ID for resume mode")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Model version")

    args = parser.parse_args()

    process_pdf(
        pdf_path=args.pdf,
        resume=args.resume,
        book_id=args.book_id,
        model_version=args.model,
    )
