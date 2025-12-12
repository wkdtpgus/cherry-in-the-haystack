#!/usr/bin/env python3
"""Resume helper script for PDF processing.

Lists incomplete processing jobs and provides resume commands.
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import get_session
from src.db.models import Book, ProcessingProgress
from sqlalchemy import func


def list_incomplete_books():
    """List all books with incomplete processing."""
    session = get_session()

    try:
        # Get all books
        books = session.query(Book).all()

        if not books:
            print("No books found in database.")
            return

        print("\n" + "=" * 80)
        print("Processing Status Report")
        print("=" * 80)

        incomplete_books = []

        for book in books:
            # Get progress statistics
            total_pages = book.total_pages or 0

            if total_pages == 0:
                print(f"\n⚠️  Book ID {book.id}: {book.title}")
                print(f"   No pages tracked (total_pages = 0)")
                continue

            # Count pages by status
            progress_stats = (
                session.query(
                    ProcessingProgress.status,
                    func.count(ProcessingProgress.id).label("count")
                )
                .filter(ProcessingProgress.book_id == book.id)
                .group_by(ProcessingProgress.status)
                .all()
            )

            status_counts = {status: count for status, count in progress_stats}

            pending = status_counts.get("pending", 0)
            processing = status_counts.get("processing", 0)
            completed = status_counts.get("completed", 0)
            failed = status_counts.get("failed", 0)

            total_tracked = pending + processing + completed + failed

            # Calculate completion percentage
            completion_pct = (completed / total_pages * 100) if total_pages > 0 else 0

            # Status indicator
            if completion_pct >= 100:
                status_icon = "✅"
                status_text = "COMPLETED"
            elif completion_pct == 0:
                status_icon = "📋"
                status_text = "NOT STARTED"
            else:
                status_icon = "🔄"
                status_text = "IN PROGRESS"
                incomplete_books.append(book)

            print(f"\n{status_icon} Book ID {book.id}: {book.title}")
            print(f"   Author: {book.author}")
            print(f"   Source: {book.source_path}")
            print(f"   Total pages: {total_pages}")
            print(f"   Status: {status_text} ({completion_pct:.1f}%)")
            print(f"   Progress: {completed} completed, {pending} pending, {processing} processing, {failed} failed")

            if total_tracked != total_pages:
                print(f"   ⚠️  Warning: Tracked pages ({total_tracked}) != total pages ({total_pages})")

            if book.created_at:
                print(f"   Created: {book.created_at}")

            if book.processed_at:
                print(f"   Last processed: {book.processed_at}")

        # Print resume commands for incomplete books
        if incomplete_books:
            print("\n" + "=" * 80)
            print("Resume Commands")
            print("=" * 80)

            for book in incomplete_books:
                print(f"\n# Resume Book ID {book.id}: {book.title}")
                print(f"python scripts/process_pdfs.py --resume --book-id {book.id}")

        else:
            print("\n✅ All books are fully processed!")

        print("\n" + "=" * 80)

    finally:
        session.close()


def show_book_details(book_id: int):
    """Show detailed progress for a specific book.

    Args:
        book_id: Book ID to show details for
    """
    session = get_session()

    try:
        book = session.query(Book).filter_by(id=book_id).first()

        if not book:
            print(f"❌ Book ID {book_id} not found")
            return

        print("\n" + "=" * 80)
        print(f"Book Details: {book.title}")
        print("=" * 80)
        print(f"ID: {book.id}")
        print(f"Title: {book.title}")
        print(f"Author: {book.author}")
        print(f"Source: {book.source_path}")
        print(f"Total pages: {book.total_pages}")
        print(f"Created: {book.created_at}")
        if book.processed_at:
            print(f"Last processed: {book.processed_at}")

        # Get failed pages
        failed_pages = (
            session.query(ProcessingProgress)
            .filter(
                ProcessingProgress.book_id == book_id,
                ProcessingProgress.status == "failed"
            )
            .all()
        )

        if failed_pages:
            print(f"\n❌ Failed Pages ({len(failed_pages)}):")
            for progress in failed_pages[:10]:  # Show first 10
                print(f"   Page {progress.page_number + 1}: {progress.error_message}")

            if len(failed_pages) > 10:
                print(f"   ... and {len(failed_pages) - 10} more")

        # Get stuck pages (processing for too long)
        stuck_pages = (
            session.query(ProcessingProgress)
            .filter(
                ProcessingProgress.book_id == book_id,
                ProcessingProgress.status == "processing"
            )
            .all()
        )

        if stuck_pages:
            print(f"\n⚠️  Stuck Pages ({len(stuck_pages)}):")
            for progress in stuck_pages:
                print(f"   Page {progress.page_number + 1}: Last updated {progress.updated_at}")

        print("\n" + "=" * 80)

    finally:
        session.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Resume helper for PDF processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--book-id",
        type=int,
        help="Show details for specific book ID"
    )

    args = parser.parse_args()

    if args.book_id:
        show_book_details(args.book_id)
    else:
        list_incomplete_books()


if __name__ == "__main__":
    main()
