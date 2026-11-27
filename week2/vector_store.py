"""
vector_store.py: 아주 작은 '벡터 DB'를 직접 만들어보기
- 실무에서는 Chroma, FAISS, pgvector 같은 벡터 DB를 쓰지만,
  원리는 이 파일이 하는 일과 똑같아요:
    1) 저장: 조각마다 임베딩(벡터)을 만들어 보관
    2) 검색: 질문도 벡터로 바꾼 뒤, 가장 '방향이 비슷한' 조각을 찾기 (코사인 유사도)
- 같은 텍스트를 매번 다시 임베딩하면 시간과 무료 한도가 아까우니 결과를 파일에 저장(캐시)해요.
- 이 파일도 직접 실행하지 않고 step2~4에서 가져다 써요.
"""

import hashlib          # 해시: 긴 문자열을 짧은 고유 문자열(지문)로 바꾸는 도구
import json             # 캐시를 JSON 파일로 저장/읽기
import math             # 제곱근(sqrt) 계산
from pathlib import Path

from chunkers import Chunk
from llm import EMBED_MODEL, embed

# 임베딩 캐시 파일 위치: week2/.cache/embeddings.json
# (.gitignore 에 등록 → GitHub에 안 올라감. 지워도 다음 실행 때 다시 만들어져요)
CACHE_PATH = Path(__file__).parent / ".cache" / "embeddings.json"


def _load_cache() -> dict:
    """캐시 파일이 있으면 읽어서 딕셔너리로, 없으면 빈 딕셔너리를 돌려줘요."""
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))  # JSON 문자열 → 딕셔너리
    return {}


def _save_cache(cache: dict) -> None:
    """딕셔너리를 JSON 파일로 저장해요."""
    CACHE_PATH.parent.mkdir(exist_ok=True)  # .cache 폴더가 없으면 만들기 (있으면 그냥 넘어감)
    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")  # 딕셔너리 → JSON 문자열


def _key(text: str, task: str) -> str:
    """텍스트+모델+용도를 짧은 고유 문자열(해시)로 바꿔 캐시의 이름표로 써요.
    텍스트가 한 글자라도 바뀌면 이름표도 완전히 바뀌어서 새로 임베딩해요.
    .encode("utf-8") : 문자열 → 바이트 (해시 함수는 바이트를 받아요)
    .hexdigest()     : 결과를 'a3f9...' 같은 16진수 문자열로"""
    return hashlib.sha1(f"{EMBED_MODEL}|{task}|{text}".encode("utf-8")).hexdigest()


def embed_cached(texts: list[str], task: str) -> list[list[float]]:
    """캐시에 있는 건 꺼내 쓰고, 없는 것만 API로 임베딩해요."""
    cache = _load_cache()
    # 캐시에 없는 텍스트만 골라내기
    missing = [t for t in texts if _key(t, task) not in cache]
    if missing:
        print(f"  (임베딩 API 호출: {len(missing)}개, 캐시 사용: {len(texts) - len(missing)}개)")
        # zip(A, B) : 두 리스트를 같은 순서끼리 짝지어 함께 돌기 → (텍스트, 벡터)
        for t, v in zip(missing, embed(missing, task=task)):
            cache[_key(t, task)] = v
        _save_cache(cache)
    # 요청받은 순서 그대로 벡터를 돌려주기
    return [cache[_key(t, task)] for t in texts]


def cosine(a: list[float], b: list[float]) -> float:
    """코사인 유사도: 두 벡터가 가리키는 방향이 얼마나 비슷한지 (-1 ~ 1, 클수록 비슷)
    = (a·b) / (|a| × |b|)
    텍스트 길이(벡터 크기)와 상관없이 '의미의 방향'만 비교할 수 있어서 검색에 많이 써요."""
    dot = sum(x * y for x, y in zip(a, b))           # 내적: 같은 위치끼리 곱해서 모두 더하기
    na = math.sqrt(sum(x * x for x in a))            # 벡터 a의 길이 (각 값을 제곱해서 더한 뒤 제곱근)
    nb = math.sqrt(sum(y * y for y in b))            # 벡터 b의 길이
    return dot / (na * nb) if na and nb else 0.0     # 길이가 0이면 나눌 수 없으니 0 반환


class VectorStore:
    """조각들과 그 벡터를 들고 있다가, 질문이 오면 비슷한 조각 Top-k를 돌려주는 상자
    사용 예)
        store = VectorStore(chunks)          # 저장 (조각들을 벡터로 변환)
        store.search("soft target?", k=3)    # 검색
    """

    def __init__(self, chunks: list[Chunk]):
        # __init__ : 'VectorStore(chunks)' 로 만들 때 자동으로 실행되는 준비 함수
        # self : 이 상자 자신. self.xxx 에 저장한 값은 상자 안에 계속 보관돼요
        self.chunks = chunks
        # 조각 내용만 뽑아서 한꺼번에 임베딩 (용도: 검색 '대상' 문서)
        self.vectors = embed_cached([c.text for c in chunks], task="RETRIEVAL_DOCUMENT")

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        """질문과 가장 비슷한 조각 k개를 (조각, 유사도) 형태로, 비슷한 순서대로 돌려줘요."""
        # 1) 질문을 벡터로 (용도: 검색 '질문')
        qv = embed_cached([query], task="RETRIEVAL_QUERY")[0]
        # 2) 모든 조각과 유사도 계산 → [(조각, 점수), (조각, 점수), ...]
        scored = [(c, cosine(qv, v)) for c, v in zip(self.chunks, self.vectors)]
        # 3) 점수가 높은 순서로 정렬
        #    key=lambda x: x[1] → (조각, 점수) 중 x[1](점수)를 기준으로 / reverse=True → 큰 값부터
        scored.sort(key=lambda x: x[1], reverse=True)
        # 4) 앞에서부터 k개만
        return scored[:k]
