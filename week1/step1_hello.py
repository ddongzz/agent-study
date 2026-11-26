"""
step1: LLM API 첫 호출
- 실행: python step1_hello.py
- 배우는 것: 프롬프트 보내기, 응답 받기, 토큰 사용량, temperature
"""
from llm import MODEL, ask


def show(result) -> None:
    print(result.text)
    # 토큰 = 비용(유료일 때)이자 한도(무료일 때). 습관적으로 확인하세요
    print(f"  [토큰] 입력 {result.input_tokens} / 출력 {result.output_tokens}")


if __name__ == "__main__":
    print(f"모델: {MODEL}\n")

    print("=== 기본 호출 ===")
    show(ask("모델 증류(Model Distillation)를 비유를 들어 3문장으로 설명해줘."))

    # 미션: 같은 질문을 temperature 0과 1로 3번씩 실행해서 비교
    question = "AI 에이전트를 한 문장으로 정의해줘."
    for temp in [0.0, 1.0]:
        print(f"\n=== temperature={temp} 로 3번 ===")
        for i in range(3):
            result = ask(question, temperature=temp)
            print(f"{i + 1}. {result.text.strip()}")
