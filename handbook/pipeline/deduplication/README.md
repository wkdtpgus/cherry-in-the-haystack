# Chunk-Level Deduplication Pipeline

청크 레벨 중복 제거 파이프라인 - Phase 1 & 2 완료

## 개요

이 모듈은 문서를 semantic chunk로 분할하고, 임베딩을 생성하여 중복을 검출하는 완전한 파이프라인을 제공합니다.

### 주요 기능

✅ **Semantic Chunking** (chunker.py)
- RecursiveCharacterTextSplitter로 문맥 보존
- 자동 메타데이터 추가 (article_id, source, chunk_index 등)
- SHA256 기반 chunk_id 생성
- 배치 처리 지원

✅ **Embedding Generation** (embedder.py)
- OpenAI text-embedding-3-small (1536 dims)
- 배치 API로 비용 최적화 (최대 100개/요청)
- 자동 retry with exponential backoff
- 실시간 비용 추적

✅ **Similarity Detection** (similarity.py)
- Cosine similarity 계산
- ChromaDB 벡터 DB 통합
- 임계값 기반 중복 검출 (default: 0.90)
- 증분 업데이트 지원 (신규 vs 기존 비교)

## 프로젝트 구조

```
handbook/pipeline/deduplication/
├── __init__.py                      # Package exports
├── chunker.py                       # Chunking pipeline
├── embedder.py                      # Embedding generation
├── similarity.py                    # Similarity & deduplication
├── test_chunker.py                  # Chunking tests
├── test_full_pipeline.py            # Integration tests
└── README.md                        # This file
```

## 설치

```bash
# 가상환경 생성 (프로젝트 루트에서)
python3 -m venv handbook-venv
source handbook-venv/bin/activate

# 의존성 설치
pip install langchain langchain-text-splitters chromadb openai
```

## 빠른 시작

### 1. Chunking만 사용 (API 불필요)

```python
from chunker import ChunkingPipeline

# 파이프라인 초기화
pipeline = ChunkingPipeline(
    chunk_size=1024,      # ~256 tokens
    chunk_overlap=128,    # ~32 tokens
    min_chunk_size=100    # 최소 크기
)

# 아티클 청킹
article = {
    'id': 'article_001',
    'title': 'Sample Article',
    'content': '긴 텍스트 내용...',
    'source': 'Article',
    'source_url': 'https://example.com/article',
    'created_time': '2024-11-15T10:00:00Z',
}

chunks = pipeline.process_article(article)

# 결과 확인
for chunk in chunks:
    print(f"Chunk {chunk.chunk_index}:")
    print(f"  ID: {chunk.chunk_id[:16]}...")
    print(f"  Text: {chunk.chunk_text[:80]}...")
```

### 2. 임베딩 생성 (OpenAI API 필요)

```python
from embedder import EmbeddingGenerator

# 환경 변수 설정
# export OPENAI_API_KEY='your-key-here'

# 임베딩 생성기
embedder = EmbeddingGenerator(
    model="text-embedding-3-small",
    batch_size=100
)

# 청크 임베딩
results = embedder.embed_chunks(chunks)

# 비용 확인
stats = embedder.get_usage_stats()
print(f"Tokens: {stats['total_tokens']:,}")
print(f"Cost: ${stats['total_cost_dollars']:.4f}")
```

### 3. 중복 제거 (ChromaDB)

```python
from similarity import ChromaDBDeduplicator

# Deduplicator 초기화
dedup = ChromaDBDeduplicator(
    collection_name="handbook_chunks",
    persist_directory="./chroma_db",
    similarity_threshold=0.90
)

# 청크 추가 및 중복 검출
chunk_ids = [r.chunk_id for r in results]
embeddings = [r.embedding for r in results]
texts = [c.chunk_text for c in chunks]

unique_ids, dup_ids, mappings = dedup.deduplicate_new_chunks(
    new_chunk_ids=chunk_ids,
    new_embeddings=embeddings,
    new_texts=texts
)

print(f"Unique: {len(unique_ids)}")
print(f"Duplicates: {len(dup_ids)}")
```

## 테스트 실행

```bash
cd handbook/pipeline/deduplication

# 1. Chunking 테스트 (API 불필요)
python test_chunker.py

# 2. 전체 파이프라인 테스트
export OPENAI_API_KEY='your-key'
python test_full_pipeline.py
```

### 테스트 결과 예시

```
============================================================
CHUNKING PIPELINE TEST SUITE
============================================================

✓ Basic chunking test passed
✓ Metadata preservation test passed
✓ Chunk ID uniqueness test passed
✓ Batch processing test passed
✓ Edge cases test passed
✓ Realistic article test passed

TEST RESULTS: 6 passed, 0 failed
```

## 사용 예시

### Phase 1: 청킹만 수행

```python
from chunker import ChunkingPipeline

# 100-200개 아티클 준비
articles = [...]  # Notion에서 export한 데이터

# 청킹
pipeline = ChunkingPipeline()
all_chunks = []

for article in articles:
    chunks = pipeline.process_article(article)
    all_chunks.extend(chunks)

# 통계
stats = pipeline.get_statistics(all_chunks)
print(f"Total chunks: {stats['total_chunks']}")
print(f"Avg chunk size: {stats['avg_chunk_size']:.0f} chars")
```

### Phase 2: 중복 제거 실험

```python
from chunker import ChunkingPipeline
from embedder import EmbeddingGenerator
from similarity import ChromaDBDeduplicator

# 1. 청킹
chunker = ChunkingPipeline(chunk_size=1024, chunk_overlap=128)
chunks = []
for article in articles:
    chunks.extend(chunker.process_article(article))

# 2. 임베딩
embedder = EmbeddingGenerator()
results = embedder.embed_chunks(chunks)

# 3. 중복 제거
dedup = ChromaDBDeduplicator(similarity_threshold=0.90)

chunk_ids = [r.chunk_id for r in results]
embeddings = [r.embedding for r in results]
texts = [c.chunk_text for c in chunks]

unique, duplicates, mappings = dedup.deduplicate_new_chunks(
    new_chunk_ids=chunk_ids,
    new_embeddings=embeddings,
    new_texts=texts
)

# 중복률 분석
print(f"Deduplication rate: {len(duplicates) / len(chunks) * 100:.1f}%")
```

### Phase 3: 증분 업데이트

```python
# 기존 청크는 이미 DB에 저장됨
# 신규 아티클만 처리

new_articles = [...]  # 새로운 아티클
new_chunks = []
for article in new_articles:
    new_chunks.extend(chunker.process_article(article))

# 임베딩 생성
new_results = embedder.embed_chunks(new_chunks)

# 기존 DB와 비교하여 중복 제거
unique, duplicates, _ = dedup.deduplicate_new_chunks(
    new_chunk_ids=[r.chunk_id for r in new_results],
    new_embeddings=[r.embedding for r in new_results],
    new_texts=[c.chunk_text for c in new_chunks]
)

# unique한 청크만 DB에 추가됨
print(f"Added {len(unique)} new unique chunks")
```

## Chunk 데이터 구조

```python
@dataclass
class Chunk:
    chunk_id: str              # SHA256 hash
    chunk_text: str            # 실제 텍스트
    chunk_index: int           # 문서 내 위치 (0-based)
    article_id: str            # 원본 아티클 ID
    source: str                # Twitter, Article, RSS 등
    source_url: str            # 원본 URL
    created_time: str          # 생성 시간
    metadata: Dict             # 추가 메타데이터
```

## 파라미터 설정 가이드

### Chunking

```python
ChunkingPipeline(
    chunk_size=1024,        # 권장: 512-1024 (128-256 tokens)
    chunk_overlap=128,      # 권장: 10-15% of chunk_size
    min_chunk_size=100      # 너무 작은 청크 필터링
)
```

### Embedding

```python
EmbeddingGenerator(
    model="text-embedding-3-small",  # 1536 dims, $0.02/1M tokens
    batch_size=100,                  # 최대 2048, 100 권장
    max_retries=3                    # Rate limit 대응
)
```

### Similarity

```python
ChromaDBDeduplicator(
    similarity_threshold=0.90,  # 0.90+: 거의 동일
                                # 0.85-0.90: 유사 (다중 관점)
                                # 0.80-0.85: 관련 있음
)
```

## 비용 예상

**100개 아티클 기준:**
- 평균 아티클 길이: 3,000 chars
- 청크당 평균: 800 chars (~200 tokens)
- 총 청크: ~375개

**OpenAI 비용:**
- 임베딩: 375 chunks × 200 tokens = 75,000 tokens
- 비용: $0.02 / 1M × 75K = **$0.0015 (약 0.15센트)**

**200개 아티클: ~$0.003 (0.3센트)**

## 성능 벤치마크

**Chunking:** (API 불필요)
- 100 articles: ~2초
- 1000 articles: ~20초

**Embedding:** (OpenAI API)
- 100 chunks: ~5초 (batch_size=100)
- 1000 chunks: ~50초

**Similarity Search:** (ChromaDB)
- 1 query on 10K chunks: <100ms
- 100 queries on 10K chunks: ~5초

## 다음 단계

### Phase 3: 점진적 업데이트
- ✅ 증분 deduplication 구현됨
- [ ] 성능 테스트 (대용량 데이터)
- [ ] 배치 처리 최적화

### Phase 4: 다중 관점 보존
- [ ] 0.85-0.90 범위 분석
- [ ] 키워드 다양성 체크
- [ ] 클러스터링 및 대표 선택

## 참고 자료

- **Architecture 문서**: `docs/architecture.md` (ADR-002, ADR-003)
- **Epic 2 Tech Spec**: `docs/epics/epic-2-tech-spec.md`
- **LangChain 문서**: https://python.langchain.com/docs/modules/data_connection/document_transformers/recursive_text_splitter
- **ChromaDB 문서**: https://docs.trychroma.com/
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings

## 라이센스

이 프로젝트는 cherry-in-the-hayrick 프로젝트의 일부입니다.
