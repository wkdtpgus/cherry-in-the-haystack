"""
워크플로우 노드 정의
핵심 아이디어 추출을 위한 LangGraph 노드들
"""
from langchain_core.prompts import ChatPromptTemplate

from src.model.model import get_default_llm
from src.model.schemas import ExtractedIdea
from src.prompts.extraction import EXTRACTION_PROMPT, HUMAN_PROMPT
from src.workflow.state import State
from src.db.connection import get_session
from src.db.models import ParagraphChunk as DBParagraphChunk, KeyIdea


def extract_core_idea(state: State) -> State:
    """
    핵심 아이디어 추출 노드

    입력 텍스트에서 핵심 아이디어를 추출하고 구조화된 형태로 반환
    """
    try:
        llm = get_default_llm()
        structured_llm = llm.with_structured_output(ExtractedIdea, method="json_mode")

        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_PROMPT),
            ("human", HUMAN_PROMPT),
        ])

        chain = prompt | structured_llm
        extracted = chain.invoke({"text": state.chunk.body_text})

        state.result = extracted
        return state

    except Exception as e:
        state.error = str(e)
        return state


def save_to_database(state: State) -> State:
    """
    데이터베이스 저장 노드

    추출된 핵심 아이디어를 데이터베이스에 저장
    """
    try:
        # 추출 실패 시 저장하지 않음
        if state.error or not state.result:
            return state

        # book_id 필수
        if not state.book_id:
            state.error = "book_id is required for database save"
            return state

        session = get_session()

        try:
            # 1. ParagraphChunk 저장 (이미 저장되었으면 스킵)
            if not state.chunk_id:
                db_chunk = DBParagraphChunk(
                    book_id=state.book_id,
                    page_number=state.chunk.page_number,
                    paragraph_index=state.chunk.paragraph_index,
                    body_text=state.chunk.body_text,
                )
                session.add(db_chunk)
                session.flush()  # Get ID without committing
                state.chunk_id = db_chunk.id

            # 2. KeyIdea 저장
            # core_idea_text에 concept(영어 기술 용어) 저장
            db_idea = KeyIdea(
                chunk_id=state.chunk_id,
                book_id=state.book_id,
                core_idea_text=state.result.concept or "",  # concept를 core_idea_text에 저장
            )
            session.add(db_idea)
            session.commit()

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

        return state

    except Exception as e:
        state.error = f"Database save failed: {str(e)}"
        return state
