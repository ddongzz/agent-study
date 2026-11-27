"""
chunkers.py: 문서를 조각(chunk)으로 자르는 3가지 방법
- RAG는 문서 전체가 아니라 '질문과 관련된 조각'만 찾아서 모델에 넣어요.
- 그래서 '어떻게 자르느냐'가 검색 품질을 크게 좌우해요.

  1) fixed    : 정해진 글자 수로 뚝뚝 자르기 (가장 단순, 문장 중간에서 잘릴 수 있음)
  2) overlap  : 정해진 글자 수로 자르되 앞 조각과 일부를 겹치기 (경계에서 문맥이 덜 끊김)
  3) heading  : 노트의 제목(1. 2. 3. ...) 단위로 자르기 (의미 단위가 유지됨)

- 이 파일은 직접 실행하지 않고, step1~4에서 'from chunkers import ...'로 가져다 써요.
"""

import re                                   # 정규표현식: '숫자. 으로 시작하는 줄' 같은 패턴 찾기
from dataclasses import dataclass, field    # 데이터 상자(클래스)를 쉽게 만드는 도구
from pathlib import Path                    # 파일 경로 다루기

# ── 기본 노트 위치 ───────────────────────────────────────────────
# 1주차에 만든 노트를 그대로 재사용해요.
# Path(__file__)      = 지금 이 파일(chunkers.py)의 위치
# .parent             = 그 파일이 들어 있는 폴더 → week2
# .parent.parent      = 한 단계 위 폴더 → agent-study
# / "week1" / ...     = 경로 이어 붙이기 → agent-study/week1/notes/my_notes.txt
# 이렇게 하면 터미널을 어느 폴더에서 열든 항상 같은 노트를 찾아요.
DEFAULT_NOTES = Path(__file__).parent.parent / "week1" / "notes" / "my_notes.txt"


# ── 조각 하나를 담는 상자 ─────────────────────────────────────────
@dataclass
class Chunk:
    id: str                 # 조각 이름 (예: "heading-2") → 검색 결과에서 어떤 조각인지 구분용
    text: str               # 조각 내용
    strategy: str           # 어떤 방법으로 잘랐는지 ("fixed" / "overlap" / "heading")
    # 추가 정보 (예: 어떤 제목 아래 조각인지)
    # field(default_factory=dict) : 조각마다 '새 빈 딕셔너리'를 만들어줘요.
    # (그냥 = {} 로 쓰면 모든 조각이 같은 딕셔너리 하나를 공유하는 버그가 생겨서 이렇게 써요)
    meta: dict = field(default_factory=dict)


def load_notes(path: Path = DEFAULT_NOTES) -> str:
    """노트 파일을 읽어서 문자열로 돌려줘요. 없으면 안내 메시지를 보여주고 종료."""
    if not Path(path).exists():
        raise SystemExit(f"노트 파일을 찾을 수 없어요: {path}")  # raise SystemExit : 프로그램 종료
    return Path(path).read_text(encoding="utf-8")


# ── 1) 고정 길이 ────────────────────────────────────────────────
def fixed_chunks(text: str, size: int = 300) -> list[Chunk]:
    """size 글자마다 자르기.
    range(0, 전체길이, size) → 0, 300, 600, 900, ... (조각이 시작하는 위치)
    text[i:i + size]          → i번째 글자부터 size 글자 잘라내기"""
    # 리스트 컴프리헨션: [만들값 for 변수 in 반복대상] → 반복하면서 바로 리스트 만들기
    pieces = [text[i:i + size] for i in range(0, len(text), size)]

    # enumerate(pieces) : (번호, 조각) 을 함께 꺼내줘요 → 0, 1, 2 ...
    # .strip() : 앞뒤 공백·줄바꿈 제거 / if p.strip() : 공백뿐인 조각은 버리기
    return [Chunk(f"fixed-{n}", p.strip(), "fixed") for n, p in enumerate(pieces) if p.strip()]


# ── 2) 겹치기 ──────────────────────────────────────────────────
def overlap_chunks(text: str, size: int = 300, overlap: int = 80) -> list[Chunk]:
    """size 글자씩 자르되, 다음 조각은 (size - overlap) 만큼만 앞으로 이동해서 overlap 글자가 겹치게.
    예) size=300, overlap=80 → 0~300, 220~520, 440~740, ...
    겹치는 이유: 중요한 문장이 경계에서 잘려도 옆 조각에는 온전히 들어 있을 확률이 높아져요."""
    step = size - overlap  # 한 번에 앞으로 이동하는 거리 (300 - 80 = 220)
    pieces = []
    for start in range(0, len(text), step):
        pieces.append(text[start:start + size])
        if start + size >= len(text):  # 이번 조각이 문서 끝까지 담았으면 멈춤 (중복 조각 방지)
            break
    return [Chunk(f"overlap-{n}", p.strip(), "overlap") for n, p in enumerate(pieces) if p.strip()]


# ── 3) 제목 기준 ────────────────────────────────────────────────
def heading_chunks(text: str, max_size: int = 600) -> list[Chunk]:
    """줄이 '숫자. '로 시작하면(예: '2. 모델 증류') 새 섹션의 시작으로 보고 잘라요.
    - 첫 제목 앞의 글(문서 제목 등)은 첫 섹션에 붙여요.
    - 섹션이 max_size 보다 길면 겹치기 방식으로 한 번 더 잘라요. (각 조각 앞에 제목을 붙여 문맥 유지)"""

    # 정규표현식 풀이: (?m)^(?=\d+\.\s)
    #   (?m)    : 여러 줄 모드 → ^ 가 '각 줄의 시작'을 뜻하게 됨
    #   ^       : 줄의 시작
    #   (?=...) : '여기서 자르되, 괄호 안 글자는 지우지 말고 다음 조각에 남겨라' (앞을 내다보기)
    #   \d+     : 숫자 1개 이상 (1, 2, 10 ...)
    #   \.\s    : 점(.)과 공백
    # → "1. ", "2. " 로 시작하는 줄 바로 앞에서 잘라요
    sections = re.split(r"(?m)^(?=\d+\.\s)", text)
    sections = [s.strip() for s in sections if s.strip()]  # 빈 덩어리 제거

    # 첫 덩어리가 제목(숫자. )으로 시작하지 않으면 = 문서 머리말(예: "[공부 노트] ...")
    # → 혼자 두면 의미 없는 짧은 조각이 되니 다음 섹션 앞에 합쳐요
    if len(sections) > 1 and not re.match(r"\d+\.\s", sections[0]):
        sections[1] = sections[0] + "\n" + sections[1]
        sections = sections[1:]  # [1:] : 첫 번째(머리말)를 뺀 나머지

    chunks = []
    for n, sec in enumerate(sections):
        title = sec.splitlines()[0]  # .splitlines() : 줄 단위로 나누기 → [0] 첫 줄 = 제목
        if len(sec) <= max_size:
            # 적당한 길이면 섹션 통째로 한 조각
            chunks.append(Chunk(f"heading-{n}", sec, "heading", {"title": title}))
        else:
            # 너무 긴 섹션은 겹치기 방식으로 잘게 나누고,
            # 두 번째 조각부터는 앞에 [제목]을 붙여서 '무슨 내용의 일부인지' 알 수 있게 해요
            for m, sub in enumerate(overlap_chunks(sec, size=max_size, overlap=100)):
                body = sub.text if m == 0 else f"[{title}]\n{sub.text}"
                chunks.append(Chunk(f"heading-{n}.{m}", body, "heading", {"title": title}))
    return chunks


# ── 이름으로 청킹 함수를 고를 수 있게 모아둔 딕셔너리 ──────────────────
# 함수도 값처럼 딕셔너리에 넣을 수 있어요.
# 사용 예: STRATEGIES["heading"](text) → heading_chunks(text) 를 실행한 것과 같음
STRATEGIES = {
    "fixed": fixed_chunks,
    "overlap": overlap_chunks,
    "heading": heading_chunks,
}
