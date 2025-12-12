"""Progress tracking and recovery logic."""

from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

from src.db.models import ProcessingProgress


def initialize_progress(session: Session, book_id: int, page_numbers: List[int]) -> None:
    """Initialize progress tracking for specified pages.

    Args:
        session: Database session
        book_id: Book ID
        page_numbers: List of page numbers to track
    """
    # Check if already initialized
    existing = session.query(ProcessingProgress).filter_by(book_id=book_id).first()
    if existing:
        print(f"⚠️  Progress already initialized for book {book_id}")
        return

    # Create pending status for all pages
    progress_records = [
        ProcessingProgress(
            book_id=book_id,
            page_number=page_num,
            status="pending",
            attempt_count=0,
        )
        for page_num in page_numbers
    ]

    session.bulk_save_objects(progress_records)
    session.commit()
    print(f"✅ Initialized progress tracking for {len(page_numbers)} pages")


def get_pending_pages(session: Session, book_id: int) -> List[int]:
    """Get list of pending page numbers.

    Args:
        session: Database session
        book_id: Book ID

    Returns:
        List of page numbers with status 'pending'
    """
    results = (
        session.query(ProcessingProgress.page_number)
        .filter_by(book_id=book_id, status="pending")
        .order_by(ProcessingProgress.page_number)
        .all()
    )
    return [r[0] for r in results]


def mark_page_processing(session: Session, book_id: int, page_number: int) -> None:
    """Mark page as being processed.

    Args:
        session: Database session
        book_id: Book ID
        page_number: Page number
    """
    progress = (
        session.query(ProcessingProgress)
        .filter_by(book_id=book_id, page_number=page_number)
        .first()
    )

    if progress:
        progress.status = "processing"
        progress.last_attempt_at = datetime.utcnow()
        progress.attempt_count += 1
        session.commit()


def mark_page_completed(session: Session, book_id: int, page_number: int) -> None:
    """Mark page as successfully completed.

    Args:
        session: Database session
        book_id: Book ID
        page_number: Page number
    """
    progress = (
        session.query(ProcessingProgress)
        .filter_by(book_id=book_id, page_number=page_number)
        .first()
    )

    if progress:
        progress.status = "completed"
        progress.completed_at = datetime.utcnow()
        session.commit()


def mark_page_failed(session: Session, book_id: int, page_number: int, error_message: str) -> None:
    """Mark page as failed with error message.

    Args:
        session: Database session
        book_id: Book ID
        page_number: Page number
        error_message: Error description
    """
    progress = (
        session.query(ProcessingProgress)
        .filter_by(book_id=book_id, page_number=page_number)
        .first()
    )

    if progress:
        progress.status = "failed"
        progress.error_message = error_message
        session.commit()


def save_batch_checkpoint(session: Session, book_id: int, completed_pages: List[int]) -> None:
    """Mark multiple pages as completed (batch update).

    Args:
        session: Database session
        book_id: Book ID
        completed_pages: List of page numbers to mark as completed
    """
    session.query(ProcessingProgress).filter(
        ProcessingProgress.book_id == book_id,
        ProcessingProgress.page_number.in_(completed_pages),
    ).update(
        {
            "status": "completed",
            "completed_at": datetime.utcnow(),
        },
        synchronize_session=False,
    )
    session.commit()


def get_progress_stats(session: Session, book_id: int) -> dict:
    """Get progress statistics for a book.

    Args:
        session: Database session
        book_id: Book ID

    Returns:
        Dictionary with progress stats:
        - total: Total pages
        - pending: Pending pages
        - processing: Pages being processed
        - completed: Completed pages
        - failed: Failed pages
        - completion_rate: Percentage completed
    """
    total = session.query(ProcessingProgress).filter_by(book_id=book_id).count()

    pending = (
        session.query(ProcessingProgress).filter_by(book_id=book_id, status="pending").count()
    )

    processing = (
        session.query(ProcessingProgress).filter_by(book_id=book_id, status="processing").count()
    )

    completed = (
        session.query(ProcessingProgress).filter_by(book_id=book_id, status="completed").count()
    )

    failed = (
        session.query(ProcessingProgress).filter_by(book_id=book_id, status="failed").count()
    )

    completion_rate = (completed / total * 100) if total > 0 else 0

    return {
        "total": total,
        "pending": pending,
        "processing": processing,
        "completed": completed,
        "failed": failed,
        "completion_rate": completion_rate,
    }


def reset_stuck_pages(session: Session, book_id: int) -> int:
    """Reset pages stuck in 'processing' status back to 'pending'.

    This is useful for recovery when processing was interrupted.

    Args:
        session: Database session
        book_id: Book ID

    Returns:
        Number of pages reset
    """
    stuck = session.query(ProcessingProgress).filter_by(book_id=book_id, status="processing").all()

    for progress in stuck:
        progress.status = "pending"

    session.commit()

    return len(stuck)
