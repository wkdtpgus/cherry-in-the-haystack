"""
핵심 아이디어 추출 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.samples import get_sample, get_all_samples
from src.workflow.workflow import run_extraction


def test_single_extraction(index: int = 0):
    """단일 문단 추출 테스트"""
    sample = get_sample(index)

    print("=" * 60)
    print(f"단일 추출 테스트 (샘플 {index + 1})")
    print("=" * 60)
    print(f"\n[입력 텍스트]")
    print(f"{sample['text'][:300]}...")
    print(f"\n[소스] {sample['source']['book_title']} p.{sample['source']['page']}")

    result = run_extraction(
        body_text=sample["text"],
        book_id=1,
        page_number=sample["source"]["page"],
        paragraph_index=sample["source"]["paragraph"],
    )

    if result.error:
        print(f"\n❌ 에러 발생: {result.error}")
        return False

    if result.result:
        print(f"\n✅ 추출 결과:")
        print(f"  concept: {result.result.concept}")
        print(f"  core_idea_text: {result.result.core_idea_text}")
        return True

    print("\n⚠️ 결과 없음")
    return False


def test_all_samples():
    """모든 샘플 추출 테스트"""
    samples = get_all_samples()

    print("=" * 60)
    print(f"전체 샘플 테스트 ({len(samples)}개)")
    print("=" * 60)

    results = []
    for i, sample in enumerate(samples):
        print(f"\n--- 샘플 {i + 1}: {sample['source']['book_title']} ---")
        print(f"[입력] {sample['text'][:100]}...")

        result = run_extraction(
            body_text=sample["text"],
            book_id=1,
            page_number=sample["source"]["page"],
            paragraph_index=sample["source"]["paragraph"],
        )

        if result.error:
            print(f"❌ 에러: {result.error}")
            results.append({"success": False, "error": result.error})
        elif result.result:
            print(f"✅ [{result.result.concept}] {result.result.core_idea_text}")
            results.append({
                "success": True,
                "concept": result.result.concept,
                "core_idea_text": result.result.core_idea_text
            })
        else:
            print("⚠️ 결과 없음")
            results.append({"success": False, "error": "No result"})

    # 요약
    print("\n" + "=" * 60)
    print("테스트 요약")
    print("=" * 60)
    success_count = sum(1 for r in results if r.get("success"))
    print(f"성공: {success_count}/{len(samples)}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="핵심 아이디어 추출 테스트")
    parser.add_argument("--all", action="store_true", help="모든 샘플 테스트")
    parser.add_argument("--index", type=int, default=0, help="테스트할 샘플 인덱스 (0-5)")

    args = parser.parse_args()

    if args.all:
        test_all_samples()
    else:
        test_single_extraction(args.index)
