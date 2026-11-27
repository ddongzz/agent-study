"""
step2: 임베딩 + 검색 — 질문과 '의미가 비슷한' 조각 찾기
- 실행: python step2_search.py                  (기본: heading 방식)
        python step2_search.py --strategy fixed
- 질문을 입력하면 Top-3 조각과 유사도 점수를 보여줘요. 빈 줄 입력 시 종료.
- 포인트: 질문에 노트와 똑같은 단어가 없어도 '의미'가 비슷하면 찾아와요.
  예) "폰에서 인터넷 없이 모델 돌리는 방법" → '온디바이스' 내용이 있는 조각
"""

import argparse

from chunkers import DEFAULT_NOTES, STRATEGIES, load_notes
from vector_store import VectorStore

if __name__ == "__main__":
    # ── 실행 옵션 ──
    parser = argparse.ArgumentParser()
    # choices=[...] : 이 목록에 있는 값만 허용 (오타 방지)
    parser.add_argument("--strategy", default="heading", choices=list(STRATEGIES))
    parser.add_argument("--notes", default=str(DEFAULT_NOTES))
    parser.add_argument("--k", type=int, default=3, help="가져올 조각 개수")
    args = parser.parse_args()

    # ── 1. 노트 읽기 → 청킹 → 벡터 저장소 만들기 ──
    # STRATEGIES[args.strategy] : 선택한 청킹 함수 → (노트 텍스트) 를 넣어 실행
    chunks = STRATEGIES[args.strategy](load_notes(args.notes))
    print(f"[{args.strategy}] 조각 {len(chunks)}개 임베딩 준비 중...")
    store = VectorStore(chunks)  # 여기서 조각들을 벡터로 바꿔요 (두 번째 실행부터는 캐시 사용)

    # ── 2. 질문 받고 검색하기 (반복) ──
    print("\n질문을 입력하세요 (종료: 그냥 Enter)")
    while True:  # 무한 반복. 아래 break 를 만나면 빠져나와요
        query = input("\n❓ 질문> ").strip()  # input() : 키보드 입력 받기
        if not query:  # 아무것도 안 쓰고 Enter → 종료
            break
        # enumerate(..., start=1) : 순위를 1부터 세기
        # (chunk, score) : search() 가 돌려주는 (조각, 유사도) 쌍을 바로 풀어서 받기
        for rank, (chunk, score) in enumerate(store.search(query, k=args.k), start=1):
            preview = chunk.text.replace("\n", " ")[:120]  # 줄바꿈을 공백으로 바꾸고 앞 120자만
            # {score:.3f} : 소수점 셋째 자리까지 (예: 0.734)
            print(f"  {rank}위 [{score:.3f}] {chunk.id}: {preview}...")
