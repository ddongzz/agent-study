"""
step3: RAG 답변 — 검색한 조각만 근거로 답하고, 출처 번호를 달기
- 실행: python step3_rag_answer.py "soft target이 뭐야?"
        python step3_rag_answer.py "벡터 DB는 뭘 써야 해?"     ← 노트에 없는 질문도 해보세요
        python step3_rag_answer.py "질문" --strategy fixed --k 2
- 1주차 step3와 차이: 노트 '전체'가 아니라 '관련 조각 k개'만 넣어요 → 토큰 절약 + 출처 추적 가능
- QA 미션:
  1) 답변의 [1], [2] 출처 번호가 실제로 그 조각 내용과 맞는지 확인
  2) 노트에 없는 질문에 "노트에 없음"이라고 하는지, 지어내는지 확인
"""

import argparse

from chunkers import DEFAULT_NOTES, STRATEGIES, load_notes
from llm import MODEL, ask
from vector_store import VectorStore

# ── 시스템 프롬프트: RAG 답변 규칙 ──────────────────────────────────
# 규칙 2(출처 번호)가 있어야 사람이 '답이 어디서 왔는지' 검증할 수 있어요 (QA 포인트)
# 규칙 3이 없으면 모델이 자기 지식으로 그럴듯하게 지어낼 수 있어요
SYSTEM = """너는 사용자의 공부 노트를 근거로 답하는 학습 도우미야.
규칙:
1. 반드시 <sources> 안의 자료만 근거로 답해. 네가 원래 알던 지식은 쓰지 마.
2. 문장마다 근거가 된 자료 번호를 [1], [2]처럼 붙여.
3. 자료로 답할 수 없으면 지어내지 말고 "노트에 없는 내용이에요."라고만 답해.
4. 한국어로 간결하게 답해."""


def build_prompt(question: str, results) -> str:
    """검색 결과를 번호 붙은 자료 목록으로 만들어 질문과 합쳐요.
    만들어지는 모양:
        <sources>
        <source id="1"> 조각 내용 </source>
        <source id="2"> 조각 내용 </source>
        </sources>
        질문: ...
    """
    # (chunk, _) : (조각, 유사도) 중 유사도는 안 쓰니까 _ 로 받기
    sources = "\n\n".join(
        f'<source id="{i}">\n{chunk.text}\n</source>' for i, (chunk, _) in enumerate(results, start=1)
    )
    return f"<sources>\n{sources}\n</sources>\n\n질문: {question}"


if __name__ == "__main__":
    # ── 실행 옵션 ──
    parser = argparse.ArgumentParser()
    parser.add_argument("question")  # '--' 없는 인자 = 필수 인자 (질문)
    parser.add_argument("--strategy", default="heading", choices=list(STRATEGIES))
    parser.add_argument("--notes", default=str(DEFAULT_NOTES))
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    # ── R (Retrieval): 검색 ──
    store = VectorStore(STRATEGIES[args.strategy](load_notes(args.notes)))
    results = store.search(args.question, k=args.k)

    # 어떤 조각을 찾아왔는지 먼저 보여주기 (답변 검증할 때 이 목록과 대조)
    print(f"\n📚 검색된 조각 (Top-{args.k}, {args.strategy})")
    for i, (chunk, score) in enumerate(results, start=1):
        # chr(10) : 줄바꿈 문자(\n). f-string 중괄호 안에서 쓰려고 이렇게 표현
        print(f"  [{i}] {chunk.id} (유사도 {score:.3f}): {chunk.text.replace(chr(10), ' ')[:80]}...")

    # ── A + G (Augmented Generation): 찾은 조각을 질문에 붙여서(증강) 답변 생성 ──
    result = ask(build_prompt(args.question, results), system=SYSTEM, temperature=0)

    print(f"\n🤖 답변 ({MODEL})\n{result.text.strip()}")
    print(f"\n[토큰] 입력 {result.input_tokens} / 출력 {result.output_tokens}")
    print("  ↳ 1주차 step3(노트 전체 투입)의 입력 토큰과 비교해보세요!")
