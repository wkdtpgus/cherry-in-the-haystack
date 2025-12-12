"""
LangGraph 워크플로우 상태 정의
"""
from pydantic import BaseModel, Field

from src.model.schemas import ParagraphChunk, ExtractedIdea


class State(BaseModel):
    """워크플로우 상태"""
    chunk: ParagraphChunk = Field(description="입력 문단 청크")
    result: ExtractedIdea | None = Field(default=None, description="추출된 핵심 아이디어")
    error: str | None = Field(default=None, description="에러 메시지")

    # 메타데이터 (DB 저장용)
    book_id: int | None = Field(default=None, description="책 ID")
    chunk_id: int | None = Field(default=None, description="저장된 청크 ID")
    model_version: str = Field(default="gemini-2.5-flash", description="LLM 모델 버전")
