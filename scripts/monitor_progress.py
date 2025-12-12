#!/usr/bin/env python3
"""Monitor PDF processing progress."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import get_session
from src.db.models import ProcessingProgress, KeyIdea, ParagraphChunk


def monitor_progress(book_id: int, watch: bool = False):
    """Monitor processing progress for a book.

    Args:
        book_id: Book ID to monitor
        watch: If True, continuously update every 5 seconds
    """
    while True:
        session = get_session()

        try:
            # Get progress stats
            total = session.query(ProcessingProgress).filter_by(book_id=book_id).count()
            completed = session.query(ProcessingProgress).filter_by(
                book_id=book_id, status="completed"
            ).count()
            processing = session.query(ProcessingProgress).filter_by(
                book_id=book_id, status="processing"
            ).count()
            failed = session.query(ProcessingProgress).filter_by(
                book_id=book_id, status="failed"
            ).count()
            pending = session.query(ProcessingProgress).filter_by(
                book_id=book_id, status="pending"
            ).count()

            # Get data stats
            chunks = session.query(ParagraphChunk).filter_by(book_id=book_id).count()
            ideas = session.query(KeyIdea).filter_by(book_id=book_id).count()

            # Print stats
            if watch:
                print("\033[2J\033[H")  # Clear screen

            print("=" * 60)
            print(f"📊 Book ID {book_id} Processing Status")
            print("=" * 60)
            print(f"Total pages: {total}")

            # Calculate percentage (handle zero division)
            percentage = (completed/total*100) if total > 0 else 0
            print(f"✅ Completed: {completed} ({percentage:.1f}%)")
            print(f"🔄 Processing: {processing}")
            print(f"⏳ Pending: {pending}")
            print(f"❌ Failed: {failed}")
            print()
            print(f"📦 Paragraph chunks saved: {chunks}")
            print(f"💡 Core ideas extracted: {ideas}")
            print("=" * 60)

            if not watch:
                break

            time.sleep(5)

        finally:
            session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor processing progress")
    parser.add_argument("--book-id", type=int, required=True, help="Book ID to monitor")
    parser.add_argument("--watch", action="store_true", help="Continuously update every 5 seconds")

    args = parser.parse_args()

    try:
        monitor_progress(args.book_id, args.watch)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
