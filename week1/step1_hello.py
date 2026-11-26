"""
step1: LLM API 첫 호출
- 실행: python step1_hello.py
- 배우는 것: 프롬프트 보내기, 응답 받기, 토큰 사용량, temperature
"""

# 같은 폴더의 llm.py 에서 MODEL(모델 이름)과 ask(질문 함수)를 가져와요
from llm import MODEL, ask


def show(result) -> None:
    """ask() 결과를 화면에 보기 좋게 출력하는 함수. '-> None' 은 돌려주는 값이 없다는 뜻"""
    print(result.text)
    # 토큰 = 비용(유료일 때)이자 한도(무료일 때). 습관적으로 확인하세요
    # f"...{변수}..." : 문자열 안에 변수 값을 끼워 넣는 문법(f-string)
    print(f"  [토큰] 입력 {result.input_tokens} / 출력 {result.output_tokens}")


# 이 파일을 직접 실행했을 때만 아래 코드가 동작해요 (llm.py 맨 아래 주석 참고)
if __name__ == "__main__":
    print(f"모델: {MODEL}\n")  # \n 은 줄바꿈

    # ── 1. 가장 기본적인 호출 ─────────────────────────────────
    print("=== 기본 호출 ===")
    show(ask("모델 증류(Model Distillation)를 비유를 들어 3문장으로 설명해줘."))

    # ── 2. temperature 비교 실험 ─────────────────────────────
    # 같은 질문을 temperature 0과 1로 3번씩 실행해서 답이 얼마나 달라지는지 비교
    #  - 0 : 가장 확률 높은 단어만 선택 → 거의 같은 답
    #  - 1 : 확률대로 뽑기 → 매번 조금씩 다른 답
    question = "AI 에이전트를 한 문장으로 정의해줘."
    for temp in [0.0, 1.0]:          # 리스트 안의 값을 하나씩 꺼내 temp 에 담아 반복
        print(f"\n=== temperature={temp} 로 3번 ===")
        for i in range(3):           # i = 0, 1, 2 → 3번 반복
            result = ask(question, temperature=temp)
            # .strip() : 답변 앞뒤의 불필요한 공백·줄바꿈 제거
            print(f"{i + 1}. {result.text.strip()}")
