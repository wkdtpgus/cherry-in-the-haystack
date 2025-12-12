"""SQLAlchemy models for the database schema.

Maps to the existing PostgreSQL schema with additional fields for
progress tracking and metadata.
"""

from sqlalchemy import Column, Integer, Text, ForeignKey, String, Sequence
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Book(Base):
    """책 정보 테이블 (서버 PostgreSQL 스키마와 일치)"""

    __tablename__ = "books"

    id = Column(Integer, Sequence('books_id_seq'), primary_key=True)
    title = Column(Text, nullable=False)
    author = Column(Text)
    source_path = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ParagraphChunk(Base):
    """문단(청크) 테이블 (기존 스키마 유지)"""

    __tablename__ = "paragraph_chunks"

    id = Column(Integer, Sequence('paragraph_chunks_id_seq'), primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    page_number = Column(Integer)
    paragraph_index = Column(Integer)
    body_text = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class IdeaGroup(Base):
    """아이디어 묶음 (중복 제거용) - 기존 스키마 유지"""

    __tablename__ = "idea_groups"

    id = Column(Integer, Sequence('idea_groups_id_seq'), primary_key=True)
    canonical_idea_text = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class KeyIdea(Base):
    """핵심 아이디어 테이블

    core_idea_text에 concept(영어 기술 용어)를 저장
    예: "Transformer", "LoRA", "RAG"
    """

    __tablename__ = "key_ideas"

    id = Column(Integer, Sequence('key_ideas_id_seq'), primary_key=True)
    chunk_id = Column(Integer, ForeignKey("paragraph_chunks.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    core_idea_text = Column(Text, nullable=False)  # concept를 여기에 저장
    idea_group_id = Column(Integer, ForeignKey("idea_groups.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ProcessingProgress(Base):
    """처리 진행상황 테이블 (신규)"""

    __tablename__ = "processing_progress"

    id = Column(Integer, Sequence('processing_progress_id_seq'), primary_key=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    page_number = Column(Integer)
    status = Column(String(50))  # 'pending', 'processing', 'completed', 'failed'
    error_message = Column(Text)
    attempt_count = Column(Integer, default=0)
    last_attempt_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now())
