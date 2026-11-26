"""
step3: 내 공부 노트로 요약 + 퀴즈 만들기 (2주차 RAG 예고편)
- 실행: python step3_my_notes.py notes/my_notes.txt
- 배우는 것: 파일 읽기, 문서를 프롬프트에 넣는 법(컨텍스트 주입), 환각 확인
- 한계: 문서 전체를 통째로 넣기 때문에 문서가 길어지면 토큰↑ → 2주차 RAG가 이걸 해결해요
- 주의: Gemini 무료 등급은 입력 데이터가 Google 제품 개선에 쓰일 수 있어요. 민감한 내용은 넣지 마세요.
"""

import sys                # 실행할 때 넘긴 인자(파일 경로)를 읽거나, 프로그램을 종료할 때 사용
from pathlib import Path  # 파일 경로를 다루는 도구. 파일 존재 확인, 읽기/쓰기가 간단해져요

from llm import ask

# ── 시스템 프롬프트: 환각(지어내기)을 막기 위한 규칙 ──────────────
# 삼중 따옴표(""" """)는 여러 줄 문자열을 만들 때 써요
SYSTEM = """너는 학습 코치야.
반드시 <notes> 안의 내용만 근거로 답해. 노트에 없는 내용은 절대 지어내지 마.
노트로 답할 수 없는 부분은 '노트에 없음'이라고 적어."""

# ── 모델에게 시킬 작업 ──────────────────────────────────────────
# '근거가 된 노트 문장'을 같이 쓰게 하면, 사람이 사실 여부를 검증하기 쉬워져요 (QA 포인트!)
TASK = """위 노트를 바탕으로:
1. 핵심 내용 5줄 요약
2. 객관식 퀴즈 3문제 (보기 4개, 정답과 근거가 된 노트 문장 함께 표시)"""


def load_notes(path: str) -> str:
    """노트 파일을 읽어서 문자열로 돌려줘요. 파일이 없으면 안내 후 종료."""
    file = Path(path)
    if not file.exists():  # 파일이 존재하지 않으면
        sys.exit(f"파일을 찾을 수 없어요: {path}")  # 메시지를 출력하고 프로그램 종료
    text = file.read_text(encoding="utf-8")  # 파일 전체 내용을 한 번에 읽기
    print(f"노트 로드: {len(text)}자")  # len() : 글자 수(길이)
    return text


if __name__ == "__main__":
    # sys.argv : 실행 명령어를 공백으로 나눈 리스트
    # 예) python step3_my_notes.py notes/my_notes.txt
    #     → sys.argv = ["step3_my_notes.py", "notes/my_notes.txt"]
    # 길이가 2보다 작으면 = 파일 경로를 안 적었다는 뜻
    if len(sys.argv) < 2:
        sys.exit("사용법: python step3_my_notes.py notes/my_notes.txt")

    notes = load_notes(sys.argv[1])  # [1] : 리스트의 두 번째 값 = 파일 경로

    # ── 컨텍스트 주입: 노트를 <notes> 태그로 감싸서 질문과 함께 보내기 ──
    # 태그로 구분해주면 모델이 '어디까지가 자료이고 어디부터가 지시인지' 헷갈리지 않아요
    # 2주차 RAG에서는 노트 전체 대신 '질문과 관련된 부분만 검색'해서 넣게 돼요
    result = ask(f"<notes>\n{notes}\n</notes>\n\n{TASK}", system=SYSTEM, temperature=0)

    print("\n" + result.text)
    Path("quiz_result.md").write_text(result.text, encoding="utf-8")  # 결과를 파일로 저장
    print(f"\n[토큰] 입력 {result.input_tokens} / 출력 {result.output_tokens}")
    print("quiz_result.md 저장 완료")
    print("\nQA 미션: 퀴즈의 '근거 문장'이 실제 노트에 있는지 하나씩 대조해보세요.")
