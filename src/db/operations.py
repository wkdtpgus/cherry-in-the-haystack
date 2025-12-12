"""Database CRUD operations with bulk insert support."""

from typing import List
from sqlalchemy.orm import Session

from src.db.models import Book, ParagraphChunk, KeyIdea, ProcessingProgress


def create_book(session: Session, title: str, author: str = None, source_path: str = None) -> Book:
    """Create a new book record.

    Args:
        session: Database session
        title: Book title
        author: Book author (optional)
        source_path: Path to PDF file (optional)

    Returns:
        Created Book object
    """
    book = Book(
        title=title,
        author=author,
        source_path=source_path,
    )
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


def save_chunks_batch(session: Session, chunks: List[ParagraphChunk]) -> None:
    """Bulk insert paragraph chunks.

    Args:
        session: Database session
        chunks: List of ParagraphChunk objects
    """
    session.bulk_save_objects(chunks)
    session.commit()


def save_ideas_batch(session: Session, ideas: List[dict]) -> None:
    """Bulk insert key ideas using mappings (faster than objects).

    Args:
        session: Database session
        ideas: List of dictionaries with KeyIdea fields
            Required: chunk_id, book_id, core_idea_text
            Optional: idea_group_id
    """
    session.bulk_insert_mappings(KeyIdea, ideas)
    session.commit()


def get_book_by_id(session: Session, book_id: int) -> Book:
    """Get book by ID.

    Args:
        session: Database session
        book_id: Book ID

    Returns:
        Book object or None
    """
    return session.query(Book).filter_by(id=book_id).first()


def get_book_by_title(session: Session, title: str) -> Book:
    """Get book by title.

    Args:
        session: Database session
        title: Book title

    Returns:
        Book object or None
    """
    return session.query(Book).filter_by(title=title).first()


def is_book_processed(session: Session, book_id: int) -> bool:
    """Check if book processing is complete.

    Args:
        session: Database session
        book_id: Book ID

    Returns:
        True if all pages are processed, False otherwise
    """
    total = session.query(ProcessingProgress).filter_by(book_id=book_id).count()
    completed = session.query(ProcessingProgress).filter_by(
        book_id=book_id,
        status="completed"
    ).count()
    return total > 0 and total == completed


def get_chunks_by_book(session: Session, book_id: int) -> List[ParagraphChunk]:
    """Get all chunks for a book.

    Args:
        session: Database session
        book_id: Book ID

    Returns:
        List of ParagraphChunk objects
    """
    return session.query(ParagraphChunk).filter_by(book_id=book_id).order_by(ParagraphChunk.page_number, ParagraphChunk.paragraph_index).all()


def get_ideas_by_book(session: Session, book_id: int) -> List[KeyIdea]:
    """Get all key ideas for a book.

    Args:
        session: Database session
        book_id: Book ID

    Returns:
        List of KeyIdea objects
    """
    return session.query(KeyIdea).filter_by(book_id=book_id).all()


def get_ideas_by_concept(session: Session, concept: str) -> List[KeyIdea]:
    """Get all key ideas for a specific concept.

    Args:
        session: Database session
        concept: Concept name (e.g., "LoRA", "Transformer")

    Returns:
        List of KeyIdea objects
    """
    return session.query(KeyIdea).filter_by(core_idea_text=concept).all()
