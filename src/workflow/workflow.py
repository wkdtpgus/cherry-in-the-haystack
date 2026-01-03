"""
LangGraph 워크플로우 정의.

PDF → TOC 기반 챕터/섹션 감지 → 문단 분할 → 아이디어 추출 (+ 중복제거)
"""
from typing import Optional
from langgraph.graph import StateGraph, END

from src.workflow.state import PipelineState, create_initial_state
from src.workflow.nodes import (
    extract_text,
    detect_structure,
    create_book_node,
    process_section,
    route_sections,
    finalize,
)


def create_pdf_pipeline() -> StateGraph:
    """PDF 처리 LangGraph 워크플로우 생성."""
    workflow = StateGraph(PipelineState)

    # 노드 추가
    workflow.add_node("extract_text", extract_text)
    workflow.add_node("detect_structure", detect_structure)
    workflow.add_node("create_book", create_book_node)
    workflow.add_node("process_section", process_section)
    workflow.add_node("finalize", finalize)

    # 엣지 정의: 순차 흐름
    workflow.set_entry_point("extract_text")
    workflow.add_edge("extract_text", "detect_structure")
    workflow.add_edge("detect_structure", "create_book")
    workflow.add_edge("create_book", "process_section")

    # 조건부 라우팅: 섹션 순회 루프
    workflow.add_conditional_edges(
        "process_section",
        route_sections,
        {
            "continue": "process_section",  # 다음 섹션 처리
            "finalize": "finalize",         # 모든 섹션 완료
        }
    )

    workflow.add_edge("finalize", END)

    return workflow.compile()


# 컴파일된 파이프라인 그래프 인스턴스
pdf_pipeline = create_pdf_pipeline()


def run_pdf_pipeline(
    pdf_path: str,
    resume: bool = False,
    book_id: Optional[int] = None,
    model_version: str = "gemini-2.5-flash",
    enable_semantic_dedup: bool = False,
    semantic_threshold: float = 0.95,
) -> dict:
    """
    단일 LangGraph를 통해 전체 PDF 처리 수행:
    1. PDF → Plain Text + TOC 추출
    2. TOC 기반 챕터/섹션 구조 감지
    3. DB에 책/챕터/섹션 저장
    4. 각 섹션별 문단 분할 및 아이디어 추출 (+ 해시/임베딩 중복제거)
    5. 처리 결과 요약

    Args:
        pdf_path: PDF 파일 경로
        resume: 이전 진행 상황에서 재개 여부
        book_id: 기존 책 ID (재개 시 사용)
        model_version: LLM 모델 버전
        enable_semantic_dedup: 임베딩 기반 중복제거 활성화 (기본 False)
        semantic_threshold: 코사인 유사도 임계값 (기본 0.95)
    """
    # 초기 상태 생성
    initial_state = create_initial_state(
        pdf_path=pdf_path,
        book_id=book_id,
        resume=resume,
        model_version=model_version,
    )

    # 중복제거 옵션 설정
    initial_state["enable_semantic_dedup"] = enable_semantic_dedup
    initial_state["semantic_threshold"] = semantic_threshold

    print(f"📄 PDF 파이프라인 시작: {pdf_path}")
    print(f"   → 모델: {model_version}")
    print(f"   → 시맨틱 중복제거: {'✅' if enable_semantic_dedup else '❌'}")

    # 그래프 실행 (섹션 수 + 여유분으로 recursion_limit 설정)
    result_state = pdf_pipeline.invoke(
        initial_state,
        config={"recursion_limit": 500}  # 최대 500개 섹션까지 지원
    )

    # 에러 체크
    if result_state.get("error"):
        return {"error": result_state["error"]}

    # 통계 출력 및 반환
    stats = result_state.get("stats", {})
    _print_summary(stats)
    return stats


def _print_summary(stats: dict) -> None:
    """처리 요약 출력."""
    print("\n" + "=" * 60)
    print("📊 처리 요약")
    print("=" * 60)
    print(f"총 챕터: {stats.get('total_chapters', 0)}")
    print(f"총 섹션: {stats.get('total_sections', 0)}")
    print(f"완료된 섹션: {stats.get('completed_sections', 0)}")
    print(f"실패한 섹션: {stats.get('failed_sections', 0)}")
    print(f"총 문단: {stats.get('total_paragraphs', 0)}")
    print(f"추출된 아이디어: {stats.get('total_ideas', 0)}")
    print("─" * 40)
    print("중복 스킵 상세:")
    print(f"  해시 기반: {stats.get('chunk_duplicates_skipped', 0)}")
    print(f"  임베딩 기반: {stats.get('semantic_duplicates_skipped', 0)}")
    print(f"  아이디어 기반: {stats.get('idea_duplicates_skipped', 0)}")
    print(f"  총 스킵: {stats.get('duplicates_skipped', 0)}")
    print("=" * 60)
