"""Paragraph chunking algorithm - Hybrid Strategy.

Optimized multi-pass algorithm for splitting PDF page text into meaningful paragraphs.
Uses hybrid approach: paragraph structure + sentence count + length constraints.
"""

import re
from typing import List


# Configuration - Hybrid Strategy (Optimized)
MIN_PARAGRAPH_LENGTH = 150   # Minimum 150 characters
MAX_PARAGRAPH_LENGTH = 1000  # Maximum 1000 characters
TARGET_SENTENCES = 5         # Target 5 sentences per chunk
HEADER_MAX_LENGTH = 80       # Lines shorter than this might be headers


def split_paragraphs(page_text: str) -> List[str]:
    """Split page text into paragraphs using hybrid strategy.

    Hybrid algorithm:
    1. Split by double newlines (preserve paragraph structure)
    2. Normalize whitespace
    3. Handle length constraints (MIN: 150, MAX: 1000)
    4. Split long chunks by sentence count (target: 5 sentences)
    5. Merge short chunks
    6. Remove headers/footers

    Args:
        page_text: Raw text from PDF page

    Returns:
        List of paragraph texts (150-1000 chars each)
    """
    if not page_text or len(page_text.strip()) < MIN_PARAGRAPH_LENGTH:
        return []

    # Clean up PDF artifacts
    # Remove footnote numbers at start of lines
    text = re.sub(r'^\d+\s+', '', page_text, flags=re.MULTILINE)
    # Remove page break markers (| at end of lines)
    text = re.sub(r'\s*\|\s*$', '', text, flags=re.MULTILINE)
    # Remove hyphenation at line breaks (word- \n word → word)
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)

    # Step 1: Split by double newlines (paragraph boundaries)
    paragraphs = text.split("\n\n")

    chunks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Step 2: Normalize whitespace
        normalized = re.sub(r"\s+", " ", para)

        # Step 3: Check length
        if MIN_PARAGRAPH_LENGTH <= len(normalized) <= MAX_PARAGRAPH_LENGTH:
            # Good size - keep as is
            chunks.append(normalized)
        elif len(normalized) < MIN_PARAGRAPH_LENGTH:
            # Too short - will merge later
            chunks.append(normalized)
        else:
            # Too long - split by sentences
            sentences = re.split(r"(?<=[.!?])\s+", normalized)
            current = []

            for sent in sentences:
                current.append(sent)
                chunk_text = " ".join(current)

                # Split when reaching target sentences or max length
                if len(current) >= TARGET_SENTENCES or len(chunk_text) >= MAX_PARAGRAPH_LENGTH:
                    if len(chunk_text) >= MIN_PARAGRAPH_LENGTH:
                        chunks.append(chunk_text)
                    current = []

            # Don't forget remaining sentences
            if current:
                chunk_text = " ".join(current)
                if len(chunk_text) >= MIN_PARAGRAPH_LENGTH:
                    chunks.append(chunk_text)

    # Step 4: Merge short chunks
    merged = []
    buffer = ""

    for chunk in chunks:
        if len(buffer) == 0:
            buffer = chunk
        elif len(buffer) < MIN_PARAGRAPH_LENGTH:
            # Merge with buffer
            buffer += " " + chunk
        else:
            # Buffer is good, save it
            merged.append(buffer)
            buffer = chunk

    # Don't forget last buffer
    if buffer and len(buffer) >= MIN_PARAGRAPH_LENGTH:
        merged.append(buffer)

    # Step 5: Filter headers/footers
    filtered = [
        chunk
        for chunk in merged
        if not is_header_footer(chunk) and len(chunk) >= MIN_PARAGRAPH_LENGTH
    ]

    return filtered


def is_header_footer(text: str) -> bool:
    """Check if text looks like a header or footer.

    Headers/footers are typically:
    - Very short (< 20 chars)
    - Contain page numbers
    - All caps and short
    - Repeated patterns

    Args:
        text: Text to check

    Returns:
        True if text looks like header/footer
    """
    text = text.strip()

    # Too short
    if len(text) < 20:
        return True

    # Only digits (page number)
    if re.match(r"^\d+$", text):
        return True

    # Pattern like "Page 123" or "Chapter 5"
    if re.match(r"^(page|chapter)\s+\d+$", text, re.IGNORECASE):
        return True

    # All caps and short
    if text.isupper() and len(text) < 50:
        return True

    return False


def get_paragraph_stats(paragraphs: List[str]) -> dict:
    """Get statistics about paragraphs.

    Args:
        paragraphs: List of paragraph texts

    Returns:
        Dictionary with statistics:
        - count: Number of paragraphs
        - total_chars: Total characters
        - avg_length: Average paragraph length
        - min_length: Minimum paragraph length
        - max_length: Maximum paragraph length
    """
    if not paragraphs:
        return {
            "count": 0,
            "total_chars": 0,
            "avg_length": 0,
            "min_length": 0,
            "max_length": 0,
        }

    lengths = [len(p) for p in paragraphs]

    return {
        "count": len(paragraphs),
        "total_chars": sum(lengths),
        "avg_length": sum(lengths) / len(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
    }
