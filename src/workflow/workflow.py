"""
LangGraph 워크플로우 정의
핵심 아이디어 추출 파이프라인
"""
from langgraph.graph import StateGraph, END

from src.model.schemas import ParagraphChunk
from src.workflow.state import State
from src.workflow.nodes import extract_core_idea


def create_extraction_workflow() -> StateGraph:
    """
    핵심 아이디어 추출 워크플로우 생성

    현재 구조:
    [입력] → [extract_core_idea] → [출력]

    추후 확장 가능:
    - 중복 체크 노드
    - DB 저장 노드
    - 검증 노드
    """
    workflow = StateGraph(State)

    # 노드 추가
    workflow.add_node("extract", extract_core_idea)

    # 엣지 정의
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", END)

    return workflow.compile()


# 컴파일된 워크플로우 인스턴스
extraction_graph = create_extraction_workflow()


def run_extraction(
    body_text: str,
    book_id: int | None = None,
    page_number: int | None = None,
    paragraph_index: int | None = None,
) -> State:
    """
    핵심 아이디어 추출 실행

    Args:
        body_text: 추출할 문단 텍스트
        book_id: 책 ID
        page_number: 페이지 번호
        paragraph_index: 문단 인덱스

    Returns:
        State: 추출 결과가 포함된 상태 객체
    """
    initial_state = State(
        chunk=ParagraphChunk(
            book_id=book_id,
            page_number=page_number,
            paragraph_index=paragraph_index,
            body_text=body_text,
        )
    )

    result_dict = extraction_graph.invoke(initial_state)
    return State(**result_dict)
