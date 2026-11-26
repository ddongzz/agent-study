"""
step3: 내 공부 노트로 요약 + 퀴즈 만들기 (2주차 RAG 예고편)
- 실행: python step3_my_notes.py 내노트.txt
- 배우는 것: 파일 읽기, 문서를 프롬프트에 넣는 법(컨텍스트 주입), 환각 확인
- 한계: 문서 전체를 통째로 넣기 때문에 문서가 길어지면 토큰↑ → 2주차 RAG가 이걸 해결해요
- 주의: Gemini 무료 등급은 입력 데이터가 Google 제품 개선에 쓰일 수 있어요. 민감한 내용은 넣지 마세요.
"""
import sys
from pathlib import Path

from llm import ask

SYSTEM = """너는 학습 코치야.
반드시 <notes> 안의 내용만 근거로 답해. 노트에 없는 내용은 절대 지어내지 마.
노트로 답할 수 없는 부분은 '노트에 없음'이라고 적어."""

TASK = """위 노트를 바탕으로:
1. 핵심 내용 5줄 요약
2. 객관식 퀴즈 3문제 (보기 4개, 정답과 근거가 된 노트 문장 함께 표시)"""


def load_notes(path: str) -> str:
    file = Path(path)
    if not file.exists():
        sys.exit(f"파일을 찾을 수 없어요: {path}")
    text = file.read_text(encoding="utf-8")
    print(f"노트 로드: {len(text)}자")
    return text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("사용법: python step3_my_notes.py 내노트.txt")

    notes = load_notes(sys.argv[1])
    result = ask(f"<notes>\n{notes}\n</notes>\n\n{TASK}", system=SYSTEM, temperature=0)

    print("\n" + result.text)
    Path("quiz_result.md").write_text(result.text, encoding="utf-8")
    print(f"\n[토큰] 입력 {result.input_tokens} / 출력 {result.output_tokens}")
    print("quiz_result.md 저장 완료")
    print("\nQA 미션: 퀴즈의 '근거 문장'이 실제 노트에 있는지 하나씩 대조해보세요.")
