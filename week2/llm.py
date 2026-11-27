"""
llm.py (2주차 버전): LLM 호출 + 임베딩을 한 곳에 모아둔 파일
- 1주차 llm.py에 embed() 함수(텍스트 → 숫자 벡터)를 추가했어요.
- step1~4는 모두 여기 있는 ask(), embed() 함수만 사용해요.
- 나중에 Claude, OpenAI 등으로 바꾸고 싶으면 이 파일만 고치면 돼요. (실무에서도 이렇게 분리해요)
- 직접 실행하면(python llm.py) 내 API 키로 쓸 수 있는 모델 목록을 보여줘요.
"""

# ── import: 다른 사람이 만든 기능(라이브러리)을 가져오는 부분 ──────────
import os                          # 운영체제 기능. 여기서는 환경변수(.env 값)를 읽을 때 사용
import time                        # 시간 관련 기능. 재시도 전에 잠깐 기다릴 때(time.sleep) 사용
from dataclasses import dataclass  # 여러 값을 하나로 묶는 '데이터 상자'를 쉽게 만드는 도구

from dotenv import load_dotenv     # .env 파일을 읽어서 환경변수로 등록해주는 라이브러리
from google import genai           # Google Gemini API 공식 라이브러리
from google.genai import errors, types  # errors: 에러 종류 / types: 요청 설정용 자료형

# ── 설정 불러오기 ────────────────────────────────────────────────
load_dotenv()  # .env 파일의 GEMINI_API_KEY, GEMINI_MODEL 을 불러와요

# os.getenv("이름", 기본값): 환경변수 값을 읽고, 없으면 기본값을 사용
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# 임베딩 모델: 텍스트를 '의미를 담은 숫자 목록(벡터)'으로 바꿔주는 전용 모델
# 에러가 나면 python llm.py 로 목록을 보고 .env 에 EMBED_MODEL=... 을 추가하세요
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")

# Gemini와 통신하는 '클라이언트' 객체. GEMINI_API_KEY 환경변수를 자동으로 읽어요.
# 이름 앞의 _ 는 "이 파일 안에서만 쓰는 변수"라는 관례적인 표시예요.
_client = genai.Client()

# 재시도할 에러 코드: 429(요청 한도 초과), 500/502/503/504(서버 일시 장애)
# set(중괄호 {})은 '포함 여부'를 빠르게 확인할 때 쓰는 자료형이에요.
RETRYABLE_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 4  # 최대 재시도 횟수


# ── 결과를 담는 상자 ─────────────────────────────────────────────
# @dataclass 를 붙이면 아래 3개 값을 담는 클래스를 자동으로 만들어줘요.
# 사용 예: result.text, result.input_tokens 처럼 이름으로 꺼내 쓸 수 있어요.
@dataclass
class LLMResult:
    text: str            # 모델의 답변 텍스트
    input_tokens: int    # 내가 보낸 프롬프트의 토큰 수
    output_tokens: int   # 모델이 생성한 답변의 토큰 수


# ── 핵심 함수: 질문을 보내고 답을 받기 ───────────────────────────
# 파라미터 옆의 ': str', ': float' 는 '이 값은 이런 타입이에요'라는 힌트(타입 힌트)예요.
# '= 1.0' 처럼 값이 있으면 생략 가능한 파라미터(기본값)예요.
# 'str | None' 은 '문자열이거나, 아무것도 없음(None)'이라는 뜻이에요.
def ask(
    prompt: str,                 # 사용자 질문(필수)
    system: str | None = None,   # 시스템 프롬프트(역할 지정). 생략하면 사용 안 함
    temperature: float = 1.0,    # 0에 가까울수록 일정한 답, 1 이상일수록 다양한 답
    model: str = MODEL,          # 사용할 모델. 생략하면 .env 에 적은 모델
    json_output: bool = False,   # True 면 JSON 형식으로만 답하게 강제
) -> LLMResult:                  # '-> LLMResult' : 이 함수는 LLMResult 를 돌려준다는 뜻
    """프롬프트 하나를 보내고 답변 + 토큰 사용량을 돌려줘요.
    json_output=True 면 모델이 JSON 형식으로만 답하게 강제해요 (채점 결과처럼 코드로 읽을 때 사용)."""

    # 요청 옵션 묶음. None 으로 둔 옵션은 '설정 안 함'으로 처리돼요.
    config = types.GenerateContentConfig(
        system_instruction=system,  # 시스템 프롬프트 (None이면 사용 안 함)
        temperature=temperature,
        # 'A if 조건 else B' : 조건이 참이면 A, 거짓이면 B (한 줄짜리 if문)
        response_mime_type="application/json" if json_output else None,
    )

    # 실제 API 호출 (일시적인 에러면 자동 재시도)
    response = _retry(lambda: _client.models.generate_content(model=model, contents=prompt, config=config))

    # 토큰 사용량 정보. 드물게 비어 있을 수 있어서 'if usage else 0' 으로 안전하게 처리
    usage = response.usage_metadata
    return LLMResult(
        text=response.text or "(빈 응답)",  # 'A or B' : A가 비어 있으면 B 사용
        input_tokens=(usage.prompt_token_count or 0) if usage else 0,
        output_tokens=(usage.candidates_token_count or 0) if usage else 0,
    )


# ── 임베딩: 텍스트 → 벡터 ─────────────────────────────────────────
def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT", model: str = EMBED_MODEL) -> list[list[float]]:
    """여러 텍스트를 한 번에 벡터로 바꿔요. 돌려주는 값: 텍스트마다 숫자 리스트 하나씩.
    task 는 용도 힌트예요:
      - "RETRIEVAL_DOCUMENT" : 검색 '대상'(노트 조각)을 저장할 때
      - "RETRIEVAL_QUERY"    : 사용자 '질문'을 검색할 때
    같은 모델이라도 용도를 알려주면 검색 품질이 좋아져요."""
    vectors = []
    # 한 번에 너무 많이 보내면 거절될 수 있어서 50개씩 나눠 보내요
    for start in range(0, len(texts), 50):
        batch = texts[start:start + 50]  # [a:b] : a번째부터 b-1번째까지 잘라내기(슬라이싱)
        response = _retry(lambda: _client.models.embed_content(
            model=model,
            contents=batch,
            config=types.EmbedContentConfig(task_type=task),
        ))
        vectors.extend(e.values for e in response.embeddings)  # .extend : 리스트에 여러 개 추가
    return vectors


# ── 재시도 로직 ──────────────────────────────────────────────────
def _retry(call):
    """일시적인 에러(503 과부하, 429 한도 초과)면 기다렸다가 다시 시도해요.
    대기 시간을 5초 → 10초 → 20초 → 40초로 늘려가는 방식(지수 백오프)이에요.
    call 에는 'lambda: 실제호출(...)' 형태로 '실행할 코드 묶음'을 넘겨받아요.
    (lambda = 이름 없는 짧은 함수. 지금 바로 실행하지 않고 나중에 call() 로 실행)"""

    # range(5) → 0, 1, 2, 3, 4 : 첫 시도 1번 + 재시도 4번
    for attempt in range(MAX_RETRIES + 1):
        # try: 일단 실행해보고, 에러가 나면 except 로 넘어가요
        try:
            return call()
        except errors.APIError as e:  # Gemini API 에러가 나면 e 라는 이름으로 받아요
            # 재시도해도 소용없는 에러(키 오류 400/403, 모델 없음 404 등)거나
            # 마지막 시도였다면 → raise 로 에러를 그대로 다시 던져서 프로그램을 멈춰요
            if e.code not in RETRYABLE_CODES or attempt == MAX_RETRIES:
                raise
            wait = 5 * (2 ** attempt)  # 2 ** n 은 2의 n제곱 → 5, 10, 20, 40초
            print(f"  ⏳ {e.code} 에러 → {wait}초 후 재시도 ({attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)  # wait 초 동안 멈췄다가 다음 반복으로


# ── 이 파일을 직접 실행했을 때만 동작하는 부분 ──────────────────────
# 'python llm.py' 로 실행하면 __name__ 이 "__main__" 이 돼서 아래가 실행돼요.
# 다른 파일에서 'from llm import ask' 로 가져올 때는 실행되지 않아요.
if __name__ == "__main__":
    print(f"현재 설정된 생성 모델: {MODEL}")
    print(f"현재 설정된 임베딩 모델: {EMBED_MODEL}\n")
    gen, emb = [], []
    for m in _client.models.list():  # 내 키로 접근 가능한 모든 모델을 하나씩 꺼내요
        actions = m.supported_actions or []
        name = m.name.replace("models/", "")  # 앞의 'models/' 글자는 떼고
        if "generateContent" in actions:
            gen.append(name)   # 텍스트 생성 모델
        if "embedContent" in actions:
            emb.append(name)   # 임베딩 모델
    print("사용 가능한 임베딩 모델:")
    print("\n".join(f" - {n}" for n in emb) or " (없음)")
    print("\n사용 가능한 텍스트 생성 모델:")
    print("\n".join(f" - {n}" for n in gen))
