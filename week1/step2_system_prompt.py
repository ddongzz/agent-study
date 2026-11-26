"""
step2: 시스템 프롬프트 비교 실험
- 실행: python step2_system_prompt.py
- 배우는 것: 시스템 프롬프트, 반복문으로 실험 자동화, 결과를 파일로 저장
- QA 관점: 같은 입력 + 다른 조건 → 출력 비교 = 테스트 케이스 설계와 같아요
"""
from datetime import datetime

from llm import MODEL, ask

# 같은 질문에 대해 비교할 시스템 프롬프트들 (자유롭게 추가해보세요!)
SYSTEM_PROMPTS = {
    "기본(없음)": None,
    "초등학생 선생님": "너는 초등학생에게 설명하는 선생님이야. 어려운 용어는 쓰지 말고 쉬운 비유를 사용해.",
    "시니어 엔지니어": "너는 10년차 ML 엔지니어야. 정확한 용어를 쓰고, 실무에서의 트레이드오프를 꼭 언급해.",
    "면접관": "너는 AI 엔지니어 면접관이야. 답변 대신 이 주제에 대한 날카로운 면접 질문 3개를 만들어.",
}

QUESTION = "RAG와 파인튜닝의 차이가 뭐야?"


if __name__ == "__main__":
    lines = [
        "# 시스템 프롬프트 비교 결과",
        f"- 실행 시각: {datetime.now():%Y-%m-%d %H:%M}",
        f"- 모델: {MODEL}",
        f"- 질문: {QUESTION}",
        "",
        "| 페르소나 | 출력 토큰 | 한 줄 평가(직접 작성) |",
        "|---|---|---|",
    ]
    details = []

    for name, prompt in SYSTEM_PROMPTS.items():
        print(f"실행 중: {name} ...")
        # 비교 실험은 temperature 0으로 고정해야 공정해요
        result = ask(QUESTION, system=prompt, temperature=0)
        lines.append(f"| {name} | {result.output_tokens} |  |")
        details.append(f"\n## {name}\n\n**시스템 프롬프트:** {prompt or '(없음)'}\n\n{result.text}\n")

    with open("results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n" + "\n".join(details))

    print("\n완료! results.md 파일을 열어서 비교해보세요.")
    print("미션: 표의 '한 줄 평가' 칸을 직접 채워보기 (이게 평가의 시작이에요)")
