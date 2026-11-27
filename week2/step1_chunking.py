"""
step1: 청킹 — 노트를 3가지 방법으로 잘라보고 눈으로 비교하기
- 실행: python step1_chunking.py
        python step1_chunking.py --notes 다른노트.txt
- 결과: chunks_preview.md (방법별 조각 목록)
- API 호출 없음 (무료, 즉시 실행)
- QA 미션: 각 방법에서 '문장이나 개념이 중간에 잘린 조각'을 찾아보세요.
"""

import argparse            # 실행 옵션(--notes ...)을 읽는 도구
from pathlib import Path   # 파일 저장용

# chunkers.py 에서 기본 노트 경로, 청킹 방법 모음, 노트 읽기 함수를 가져와요
from chunkers import DEFAULT_NOTES, STRATEGIES, load_notes

if __name__ == "__main__":
    # ── 실행 옵션 ──
    # --notes 를 안 적으면 기본 노트(week1/notes/my_notes.txt)를 사용
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", default=str(DEFAULT_NOTES))
    args = parser.parse_args()

    text = load_notes(args.notes)
    print(f"노트: {args.notes} ({len(text)}자)\n")

    # 결과 파일에 쓸 줄들을 모아둘 리스트
    # Path(...).name : 경로에서 파일 이름만 (예: my_notes.txt)
    lines = ["# 청킹 방식 비교", f"- 노트: {Path(args.notes).name} ({len(text)}자)", ""]

    # ── 1. 요약 표: 방법별 조각 개수와 길이 ──
    # 리스트 += [...] : 여러 줄을 한꺼번에 추가
    lines += ["| 방법 | 조각 수 | 평균 길이 | 최소 | 최대 |", "|---|---|---|---|---|"]
    results = {}  # {"fixed": [조각들], "overlap": [...], "heading": [...]} 형태로 저장할 딕셔너리
    for name, func in STRATEGIES.items():  # name="fixed", func=fixed_chunks ... 차례로
        chunks = func(text)                # 청킹 실행
        results[name] = chunks
        sizes = [len(c.text) for c in chunks]  # 조각별 글자 수 목록
        # // : 나눗셈 후 소수점 버리기 (평균 길이를 정수로)
        lines.append(f"| {name} | {len(chunks)} | {sum(sizes) // len(sizes)} | {min(sizes)} | {max(sizes)} |")
        print(f"{name:8} → 조각 {len(chunks)}개")  # {name:8} → 8칸 너비로 맞춰 출력(줄 정렬용)

    # ── 2. 방법별 조각 내용 전체 ──
    for name, chunks in results.items():
        lines += ["", f"## {name}", ""]
        for c in chunks:
            # 조각을 ``` 코드 블록으로 감싸서 '어디서 시작하고 어디서 끝나는지' 한눈에 보이게
            lines += [f"### {c.id} ({len(c.text)}자)", "```", c.text, "```", ""]

    # ── 3. 직접 채울 관찰 기록 칸 ──
    lines += [
        "## 관찰 기록 (직접 작성)",
        "- 문장/개념이 중간에 잘린 조각:",
        "- 검색에 가장 유리해 보이는 방법과 이유:",
    ]

    # "\n".join(lines) : 리스트의 각 줄을 줄바꿈으로 이어 붙여서 파일로 저장
    Path("chunks_preview.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n완료! chunks_preview.md 를 열어서 조각들을 비교해보세요.")
