"""PDF parsing module using PyMuPDF (fitz).

Provides lazy loading for memory-efficient page-by-page processing.
"""

import fitz  # PyMuPDF
from typing import Generator, Dict, Any


def extract_page_text(pdf_path: str, page_num: int) -> str:
    """Extract text from a specific page.

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (0-indexed)

    Returns:
        Extracted text from the page

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        IndexError: If page number is out of range
    """
    doc = fitz.open(pdf_path)
    try:
        if page_num >= len(doc):
            raise IndexError(f"Page {page_num} out of range (total: {len(doc)})")

        page = doc[page_num]
        text = page.get_text()
        return text
    finally:
        doc.close()


def extract_pages_lazy(pdf_path: str) -> Generator[tuple[int, str], None, None]:
    """Extract pages lazily (generator) for memory efficiency.

    Args:
        pdf_path: Path to PDF file

    Yields:
        Tuple of (page_number, page_text)

    Example:
        for page_num, text in extract_pages_lazy("book.pdf"):
            print(f"Page {page_num}: {len(text)} characters")
    """
    doc = fitz.open(pdf_path)
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            yield page_num, text
            # Explicitly delete page to free memory
            page = None
    finally:
        doc.close()


def get_pdf_metadata(pdf_path: str) -> Dict[str, Any]:
    """Extract PDF metadata.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Dictionary with metadata:
        - title: Document title
        - author: Document author
        - total_pages: Total number of pages
        - producer: PDF producer
        - creator: PDF creator application
    """
    doc = fitz.open(pdf_path)
    try:
        metadata = doc.metadata
        return {
            "title": metadata.get("title", ""),
            "author": metadata.get("author", ""),
            "total_pages": len(doc),
            "producer": metadata.get("producer", ""),
            "creator": metadata.get("creator", ""),
        }
    finally:
        doc.close()


def get_total_pages(pdf_path: str) -> int:
    """Get total number of pages in PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Total page count
    """
    doc = fitz.open(pdf_path)
    try:
        return len(doc)
    finally:
        doc.close()
