"""
LLM 모델 관리 모듈
ChatVertexAI 모델을 초기화하고 다른 모듈에서 사용할 수 있도록 제공
"""
import os
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI

load_dotenv()


def get_llm(
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 50000,
) -> ChatVertexAI:
    """
    ChatVertexAI 모델 인스턴스를 반환

    Args:
        model: 모델명 (기본값: 환경변수 VERTEX_AI_MODEL)
        temperature: 생성 온도 (기본값: 0.0 - 결정적 출력)
        max_tokens: 최대 토큰 수

    Returns:
        ChatVertexAI 인스턴스
    """
    model_name = model or os.getenv("VERTEX_AI_MODEL", "gemini-2.5-flash")

    return ChatVertexAI(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )


# 기본 모델 인스턴스 (싱글톤 패턴)
_default_llm: ChatVertexAI | None = None


def get_default_llm() -> ChatVertexAI:
    """기본 설정의 LLM 인스턴스 반환 (싱글톤)"""
    global _default_llm
    if _default_llm is None:
        _default_llm = get_llm()
    return _default_llm
