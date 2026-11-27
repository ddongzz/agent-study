"""
step4: 검색 품질 평가 — 청킹 방식 3가지 중 무엇이 '정답 조각'을 잘 찾아오나?
- 실행: python step4_retrieval_eval.py
- 평가 데이터: eval_set.json (질문 + 정답 조각에 반드시 들어 있어야 할 핵심 문구)
- 결과: retrieval_report.md
- 지표 (QA의 '테스트 통과율'과 같은 개념)
  * Hit@1 : 1위로 가져온 조각에 정답 문구가 있었던 비율
  * Hit@3 : Top-3 안에 정답 문구가 있는 조각이 하나라도 있었던 비율
  * MRR   : 정답 조각이 몇 위에 있었는지의 평균 (1위=1.0, 2위=0.5, 3위=0.33, 못 찾음=0)
- 포인트: 이 단계는 답변 생성(LLM) 없이 '검색'만 평가해요.
  검색이 틀리면 뒤의 답변도 틀리기 때문에, RAG 평가는 검색부터 따로 봐요.
"""

import argparse
import json                        # eval_set.json 읽기
from datetime import datetime      # 실행 시각 기록
from pathlib import Path

from chunkers import DEFAULT_NOTES, STRATEGIES, load_notes
from llm import EMBED_MODEL
from vector_store import VectorStore, embed_cached


def rank_of_answer(results, expected: str) -> int | None:
    """검색 결과에서 정답 문구가 들어 있는 첫 조각의 순위(1부터). 없으면 None
    'int | None' : 정수 또는 None 을 돌려준다는 뜻"""
    for rank, (chunk, _) in enumerate(results, start=1):
        if expected in chunk.text:  # 'A in B' : 문자열 B 안에 A가 들어 있으면 True
            return rank
    return None  # 끝까지 못 찾으면


if __name__ == "__main__":
    # ── 실행 옵션 ──
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", default=str(DEFAULT_NOTES))
    parser.add_argument("--eval", default="eval_set.json")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    text = load_notes(args.notes)
    # JSON 파일 → [{"id":..., "question":..., "expected":...}, ...] 리스트
    cases = json.loads(Path(args.eval).read_text(encoding="utf-8"))

    # ── 0. 평가 데이터 자체 검증 ──
    # 정답 문구가 노트에 아예 없으면 어떤 청킹으로도 못 찾으니 평가가 무의미해요
    # (QA로 치면 '테스트 케이스의 기대값이 틀린 경우'를 먼저 걸러내는 단계)
    missing = [c["id"] for c in cases if c["expected"] not in text]
    if missing:
        print(f"⚠️ 노트에 정답 문구가 없는 문항: {missing} → eval_set.json 을 노트에 맞게 고쳐주세요")

    # 질문 10개를 한 번에 미리 임베딩해서 캐시에 넣어둬요 (API 호출 10번 → 1번)
    embed_cached([c["question"] for c in cases], task="RETRIEVAL_QUERY")

    summary, details = [], []  # 요약 표 줄들, 상세 표 줄들
    # ── 1. 청킹 방식마다 같은 질문 10개로 검색 ──
    for name, func in STRATEGIES.items():
        print(f"\n[{name}] 평가 중...")
        store = VectorStore(func(text))
        ranks = []  # 문항별 정답 순위 (못 찾으면 None)
        rows = []   # 상세 표의 줄들
        for c in cases:
            results = store.search(c["question"], k=args.k)
            r = rank_of_answer(results, c["expected"])
            ranks.append(r)
            top1 = results[0][0].id  # results[0] = 1위 (조각, 점수) → [0] = 조각 → .id
            # 한 줄 if 를 두 번 겹친 것: r==1 이면 ✅, r 이 있으면(2~k위) 🔸, 없으면 ❌
            mark = "✅" if r == 1 else ("🔸" if r else "❌")
            # {r or '-'} : r 이 None 이면 '-' 표시
            rows.append(f"| {c['id']} | {c['question']} | `{c['expected']}` | {mark} {r or '-'} | {top1} |")

        # ── 2. 지표 계산 ──
        n = len(cases)
        hit1 = sum(1 for r in ranks if r == 1) / n        # 1위로 찾은 문항 수 ÷ 전체
        hitk = sum(1 for r in ranks if r) / n             # k위 안에서 찾은 문항 수 ÷ 전체
        mrr = sum(1 / r for r in ranks if r) / n          # (1/순위)의 평균. 못 찾은 문항은 0점
        # {hit1:.0%} : 0.6 → "60%" 처럼 퍼센트로 표시
        summary.append(f"| {name} | {len(store.chunks)} | {hit1:.0%} | {hitk:.0%} | {mrr:.2f} |")
        print(f"  Hit@1 {hit1:.0%} / Hit@{args.k} {hitk:.0%} / MRR {mrr:.2f}")

        # *rows : 리스트를 풀어서 하나씩 넣기
        details += [f"\n## {name}", "", f"| ID | 질문 | 정답 문구 | 정답 순위 | 1위 조각 |", "|---|---|---|---|---|", *rows]

    # ── 3. 리포트 저장 ──
    report = [
        "# 검색 품질 평가 리포트",
        f"- 실행 시각: {datetime.now():%Y-%m-%d %H:%M}",
        f"- 임베딩 모델: {EMBED_MODEL}",
        f"- 노트: {Path(args.notes).name} ({len(text)}자) / 평가 문항: {len(cases)}개 / Top-{args.k}",
        "",
        "## 요약",
        "",
        f"| 청킹 방식 | 조각 수 | Hit@1 | Hit@{args.k} | MRR |",
        "|---|---|---|---|---|",
        *summary,
        "",
        "> ✅ 1위로 찾음 / 🔸 Top-k 안에서 찾음 / ❌ 못 찾음",
        *details,
        "",
        "## 분석 (직접 작성)",
        "- 가장 좋은 청킹 방식과 이유:",
        "- ❌가 나온 문항은 왜 실패했나? (조각이 잘려서? 질문 표현이 달라서?):",
        "- 이 평가 방식의 한계:",
    ]
    Path("retrieval_report.md").write_text("\n".join(report), encoding="utf-8")
    print("\n완료! retrieval_report.md 를 열어보세요.")
