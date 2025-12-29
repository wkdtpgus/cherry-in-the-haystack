"""
LangGraph 워크플로우 노드들.

각 노드는 PipelineState를 받아 업데이트된 상태를 반환.
"""

# 기존 파이프라인 노드
from src.workflow.nodes.extract_text import extract_text
from src.workflow.nodes.detect_structure import detect_structure
from src.workflow.nodes.create_book import create_book_node
from src.workflow.nodes.process_section import process_section, route_sections
from src.workflow.nodes.finalize import finalize

# dedup 관련 노드
from src.workflow.nodes.chunk_paragraphs import chunk_paragraphs
from src.workflow.nodes.extract_ideas import extract_idea
from src.workflow.nodes.check_duplicate import (
    check_chunk_duplicate,
    check_idea_duplicate,
)
from src.workflow.nodes.save_to_db import save_to_db

__all__ = [
    # 기존 파이프라인
    "extract_text",
    "detect_structure",
    "create_book_node",
    "process_section",
    "route_sections",
    "finalize",
    # dedup 관련
    "chunk_paragraphs",
    "extract_idea",
    "check_chunk_duplicate",
    "check_idea_duplicate",
    "save_to_db",
]
