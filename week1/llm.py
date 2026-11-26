"""
llm.py: LLM 호출을 한 곳에 모아둔 파일
- step1~3은 모두 여기 있는 ask() 함수만 사용해요.
- 나중에 Claude, OpenAI 등으로 바꾸고 싶으면 이 파일만 고치면 돼요. (실무에서도 이렇게 분리해요)
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # .env 파일의 GEMINI_API_KEY, GEMINI_MODEL 을 불러와요

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# GEMINI_API_KEY 환경변수를 자동으로 읽어요
_client = genai.Client()


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int


def ask(
    prompt: str,
    system: str | None = None,
    temperature: float = 1.0,
    model: str = MODEL,
) -> LLMResult:
    """프롬프트 하나를 보내고 답변 + 토큰 사용량을 돌려줘요."""
    config = types.GenerateContentConfig(
        system_instruction=system,  # 시스템 프롬프트 (None이면 사용 안 함)
        temperature=temperature,
    )
    response = _client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )

    usage = response.usage_metadata
    return LLMResult(
        text=response.text or "(빈 응답)",
        input_tokens=(usage.prompt_token_count or 0) if usage else 0,
        output_tokens=(usage.candidates_token_count or 0) if usage else 0,
    )


if __name__ == "__main__":
    # python llm.py 로 실행하면 내 키로 쓸 수 있는 모델 목록을 보여줘요
    print(f"현재 설정된 모델: {MODEL}\n")
    print("사용 가능한 텍스트 생성 모델:")
    for m in _client.models.list():
        if "generateContent" in (m.supported_actions or []):
            print(" -", m.name.replace("models/", ""))
