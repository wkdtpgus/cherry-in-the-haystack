"""
Pydantic 스키마 정의
DB 테이블 구조에 맞춘 데이터 스키마
"""
from pydantic import BaseModel, Field


class Book(BaseModel):
    """books 테이블 매칭"""
    id: int | None = Field(default=None, description="책 ID (DB 자동생성)")
    title: str = Field(description="책 제목")
    author: str | None = Field(default=None, description="저자")
    source_path: str | None = Field(default=None, description="원본 파일 경로")


class ParagraphChunk(BaseModel):
    """paragraph_chunks 테이블 매칭"""
    id: int | None = Field(default=None, description="청크 ID (DB 자동생성)")
    book_id: int | None = Field(default=None, description="책 ID (FK)")
    page_number: int | None = Field(default=None, description="페이지 번호")
    paragraph_index: int | None = Field(default=None, description="문단 인덱스")
    body_text: str = Field(description="원본 문단 텍스트")


class KeyIdea(BaseModel):
    """
    key_ideas 테이블 매칭
    LLM이 추출하는 핵심 아이디어
    """
    id: int | None = Field(default=None, description="아이디어 ID (DB 자동생성)")
    chunk_id: int | None = Field(default=None, description="청크 ID (FK)")
    book_id: int | None = Field(default=None, description="책 ID (FK)")
    core_idea_text: str = Field(description="핵심 아이디어 텍스트")
    idea_group_id: int | None = Field(default=None, description="아이디어 그룹 ID (중복제거용)")


class IdeaGroup(BaseModel):
    """idea_groups 테이블 매칭 (중복 제거용)"""
    id: int | None = Field(default=None, description="그룹 ID (DB 자동생성)")
    canonical_idea_text: str = Field(description="정규화된 대표 아이디어 텍스트")


# LLM 출력용 스키마 (DB 스키마와 별도)
class ExtractedIdea(BaseModel):
    """LLM이 추출하는 핵심 아이디어 (프롬프트 출력용)"""
    concept: str = Field(description="온톨로지 노드 제목 (예: LoRA, Attention, Transformer)")
