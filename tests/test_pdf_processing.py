"""Test PDF processing functionality."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf.parser import extract_page_text, get_pdf_metadata, get_total_pages
from src.pdf.chunker import split_paragraphs, get_paragraph_stats


def test_pdf_metadata():
    """Test PDF metadata extraction."""
    pdf_path = "AI Engineering.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return

    print("📖 Testing PDF metadata extraction...")
    metadata = get_pdf_metadata(pdf_path)

    print(f"  Title: {metadata['title']}")
    print(f"  Author: {metadata['author']}")
    print(f"  Total Pages: {metadata['total_pages']}")
    print(f"  Creator: {metadata['creator']}")
    print()


def test_page_extraction():
    """Test page text extraction."""
    pdf_path = "AI Engineering.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return

    print("📄 Testing page extraction...")
    total_pages = get_total_pages(pdf_path)
    print(f"  Total pages: {total_pages}")

    # Test first page
    page_num = 10  # Try page 10
    text = extract_page_text(pdf_path, page_num)
    print(f"\n  Page {page_num + 1} sample (first 500 chars):")
    print(f"  {text[:500]}")
    print(f"  Total characters: {len(text)}")
    print()


def test_paragraph_chunking():
    """Test paragraph splitting."""
    pdf_path = "AI Engineering.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return

    print("✂️  Testing paragraph chunking...")

    # Extract page 10
    page_num = 10
    text = extract_page_text(pdf_path, page_num)

    # Split into paragraphs
    paragraphs = split_paragraphs(text)

    print(f"  Page {page_num + 1}: Found {len(paragraphs)} paragraphs")

    # Show statistics
    stats = get_paragraph_stats(paragraphs)
    print(f"\n  Statistics:")
    print(f"    Count: {stats['count']}")
    print(f"    Total chars: {stats['total_chars']}")
    print(f"    Avg length: {stats['avg_length']:.1f}")
    print(f"    Min length: {stats['min_length']}")
    print(f"    Max length: {stats['max_length']}")

    # Show first 2 paragraphs
    print(f"\n  First 2 paragraphs:")
    for i, para in enumerate(paragraphs[:2], 1):
        print(f"\n  [{i}] {para[:200]}...")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("PDF Processing Tests")
    print("=" * 60)
    print()

    test_pdf_metadata()
    test_page_extraction()
    test_paragraph_chunking()

    print("=" * 60)
    print("✅ Tests completed")
    print("=" * 60)
