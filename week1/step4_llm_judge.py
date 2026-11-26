"""
step4: LLM Judge — step2 결과(results.md)를 LLM이 기준표(루브릭)로 채점하기
- 실행: python step4_llm_judge.py            (기본: 각 답변을 2번씩 채점)
        python step4_llm_judge.py --repeat 3
- 배우는 것:
  1) 루브릭 설계: "좋은 답변"을 평가 기준(Dimension)과 점수(Metric)로 쪼개기
  2) JSON 출력: 채점 결과를 코드가 읽을 수 있는 형태로 받기
  3) Judge 일관성 검사: 같은 답변을 여러 번 채점했을 때 점수가 흔들리는지 확인
     → "어제 PASS, 오늘 FAIL"이 Judge 자체에서도 생길 수 있어요!
- 결과: judge_report.md
"""

import argparse                # 실행 옵션(--repeat 3 같은 것)을 읽어주는 도구
import json                    # JSON 문자열 ↔ 파이썬 딕셔너리 변환
import re                      # 정규표현식: 문자열에서 특정 패턴을 찾는 도구
from datetime import datetime  # 실행 시각 기록용
from pathlib import Path       # 파일 읽기/쓰기

from llm import MODEL, ask

# ── 1. 평가 기준(루브릭) ─────────────────────────────────────────
# 책에서 배운 기준으로 자유롭게 바꿔보세요. 기준이 바뀌면 점수도 바뀌어요.
# 키(왼쪽 영어 이름)는 JSON 결과와 표 머리글에 쓰이고, 값(오른쪽)은 Judge에게 주는 설명이에요.
RUBRIC = {
    "persona": "페르소나 준수: 시스템 프롬프트가 요구한 역할·말투·출력 형식을 지켰는가",
    "accuracy": "사실 정확성: RAG/파인튜닝에 대한 설명에 틀린 내용이 없는가",
    "calibration": "표현의 신중함: 근거 없이 단정하거나 과장한 표현(예: '항상', '표준', '완벽하게')이 없는가",
    "relevance": "질문 적합성: 사용자의 질문에 맞는 내용을 적절한 분량으로 답했는가",
}

# PASS/FAIL 판정 기준 (QA의 '합격 기준'과 같아요)
PASS_AVG = 4.0   # 평균 4점 이상
PASS_MIN = 3     # 그리고 모든 항목 3점 이상이어야 PASS

# Judge 역할을 하는 LLM에게 주는 시스템 프롬프트
JUDGE_SYSTEM = """너는 AI 답변 품질을 평가하는 엄격하고 공정한 QA 평가자야.
- 주어진 루브릭의 각 항목을 1~5점 정수로 채점해. (5=매우 우수, 3=보통/일부 문제, 1=심각한 문제)
- 점수마다 답변 속 구체적인 근거(문장이나 표현)를 짧게 들어.
- 답변이 길다고 점수를 더 주지 마.
- 반드시 지정된 JSON 형식으로만 답해."""

# Judge에게 보낼 프롬프트 틀(템플릿)
# {question} 같은 자리는 나중에 .format() 으로 실제 값이 채워져요.
# {{ }} 처럼 중괄호를 두 번 쓰면 '진짜 중괄호 문자'로 출력돼요 (JSON 모양을 보여주려고)
JUDGE_TEMPLATE = """## 사용자 질문
{question}

## 평가 대상 AI의 시스템 프롬프트
{system_prompt}

## 평가 대상 답변
<answer>
{answer}
</answer>

## 루브릭
{rubric}

## 출력 형식 (JSON)
{{
  "scores": {{{score_keys}}},
  "reasons": {{{reason_keys}}},
  "issues": ["발견한 문제점을 짧게 나열 (없으면 빈 배열)"]
}}"""


# ── 2. results.md 읽기 ──────────────────────────────────────────
def parse_results(path: Path) -> tuple[str, list[dict]]:
    """step2가 만든 results.md에서 질문과 페르소나별 (시스템 프롬프트, 답변)을 꺼내요.
    돌려주는 값: (질문 문자열, [{"name":..., "system_prompt":..., "answer":...}, ...])"""
    text = path.read_text(encoding="utf-8")

    # 정규표현식으로 '- 질문: ...' 줄 찾기
    #  ^ : 줄의 시작 / (.+) : 아무 글자 1개 이상 → 이 부분을 꺼내옴 / $ : 줄의 끝
    #  re.M : 여러 줄 모드 (^ 와 $ 를 각 줄 기준으로)
    q = re.search(r"^- 질문: (.+)$", text, re.M)
    question = q.group(1).strip() if q else "(질문 정보 없음)"  # group(1) : 괄호로 잡은 부분

    cases = []
    # "\n## " (제목 2단계)를 기준으로 문서를 잘라요 → 페르소나별 덩어리가 됨
    # [1:] : 첫 덩어리(요약 표 부분)는 건너뛰기
    for section in re.split(r"\n## ", text)[1:]:
        # .partition("\n") : 첫 줄바꿈 기준으로 (앞, 구분자, 뒤) 3개로 나눔 → 첫 줄 = 페르소나 이름
        name, _, body = section.partition("\n")  # _ 는 '안 쓰는 값'이라는 관례적인 이름
        sp = re.search(r"\*\*시스템 프롬프트:\*\* (.*)", body)  # \*\* 는 마크다운 굵게(**) 기호
        system_prompt = sp.group(1).strip() if sp else "(없음)"
        # sp.end() : 시스템 프롬프트 줄이 끝나는 위치 → 그 뒤 전부가 답변
        answer = body[sp.end():].strip() if sp else body.strip()
        cases.append({"name": name.strip(), "system_prompt": system_prompt, "answer": answer})
    return question, cases


# ── 3. 채점 ─────────────────────────────────────────────────────
def judge_once(question: str, case: dict) -> dict:
    """답변 하나를 Judge에게 1번 채점받아요. 실패하면 {"error": ...} 를 돌려줘요."""
    # 템플릿의 빈칸 채우기
    prompt = JUDGE_TEMPLATE.format(
        question=question,
        system_prompt=case["system_prompt"],
        answer=case["answer"],
        # 루브릭을 "- persona: 설명" 형식의 여러 줄로 만들기
        rubric="\n".join(f"- {k}: {v}" for k, v in RUBRIC.items()),
        # JSON 예시의 키 목록 만들기 → "persona": 1~5, "accuracy": 1~5, ...
        score_keys=", ".join(f'"{k}": 1~5' for k in RUBRIC),
        reason_keys=", ".join(f'"{k}": "근거"' for k in RUBRIC),
    )
    # 채점은 일관성이 중요하니 temperature 0 + JSON 형식 강제
    try:
        result = ask(prompt, system=JUDGE_SYSTEM, temperature=0, json_output=True)
    except Exception as e:
        # 재시도까지 다 실패한 API 에러(503 등)도 여기서 잡아서 '실패 1건'으로 기록해요.
        # 이렇게 안 하면 8번 중 마지막 1번만 실패해도 앞의 7번 결과까지 전부 날아가요!
        print(f"  ⚠️ 채점 실패: {str(e)[:80]}")
        return {"error": f"API 오류: {e}"}

    try:
        data = json.loads(result.text)  # JSON 문자열 → 파이썬 딕셔너리
        # 점수를 정수로 변환하면서, 루브릭 항목이 빠짐없이 있는지도 확인
        scores = {k: int(data["scores"][k]) for k in RUBRIC}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # JSON이 깨졌거나(JSONDecodeError), 항목이 빠졌거나(KeyError), 숫자가 아니면(ValueError)
        # Judge가 형식을 안 지킨 것도 하나의 '결함'이에요. 기록하고 넘어가요.
        return {"error": result.text[:300]}  # [:300] : 앞 300자만 저장
    data["scores"] = scores
    return data


def verdict(scores: dict) -> tuple[float, str]:
    """점수 딕셔너리로 (평균, 판정 문자열)을 계산해요."""
    avg = sum(scores.values()) / len(scores)  # .values() : 딕셔너리의 값(점수)들만
    ok = avg >= PASS_AVG and min(scores.values()) >= PASS_MIN  # 두 조건 모두 참이어야 PASS
    return avg, "✅ PASS" if ok else "❌ FAIL"


# ── 4. 실행 + 리포트 ────────────────────────────────────────────
if __name__ == "__main__":
    # 실행 옵션 정의: python step4_llm_judge.py --repeat 3 --file 다른파일.md
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="results.md")
    parser.add_argument("--repeat", type=int, default=2, help="같은 답변을 몇 번 채점할지 (일관성 검사)")
    args = parser.parse_args()  # 이후 args.file, args.repeat 로 사용

    question, cases = parse_results(Path(args.file))
    print(f"채점 대상 {len(cases)}개 × {args.repeat}회 / Judge 모델: {MODEL}\n")

    keys = list(RUBRIC)  # 딕셔너리를 list() 하면 키 목록만 → ["persona", "accuracy", ...]

    # 리포트 윗부분 (실험 정보 + 루브릭 + 요약 표 머리글)
    lines = [
        "# LLM Judge 채점 리포트",
        f"- 실행 시각: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Judge 모델: {MODEL} (temperature 0)",
        f"- 질문: {question}",
        f"- 판정 기준: 평균 {PASS_AVG} 이상 + 모든 항목 {PASS_MIN}점 이상 → PASS",
        f"- 반복 채점: {args.repeat}회",
        "",
        "## 루브릭",
        *[f"- **{k}**: {v}" for k, v in RUBRIC.items()],  # * : 리스트를 풀어서 하나씩 넣기
        "",
        "## 요약 (1회차 기준)",
        "",
        "| 페르소나 | " + " | ".join(keys) + " | 평균 | 판정 | 반복 시 점수 변동 |",
        "|---|" + "---|" * (len(keys) + 3),  # 문자열 * 숫자 : 그 횟수만큼 반복
    ]
    details = []   # 페르소나별 상세 근거
    unstable = 0   # 점수가 흔들린 페르소나 개수

    for case in cases:
        # ── 같은 답변을 repeat 번 채점 ──
        runs = []
        for i in range(args.repeat):
            print(f"채점 중: {case['name']} ({i + 1}/{args.repeat})")
            runs.append(judge_once(question, case))

        # 리스트 컴프리헨션: runs 중 "error" 가 없는 것만 골라 새 리스트로
        valid = [r for r in runs if "error" not in r]
        if not valid:  # 전부 실패했으면 표에 '파싱 실패'로 기록하고 다음 페르소나로
            lines.append(f"| {case['name']} | " + " | ".join("-" for _ in keys) + " | - | ⚠️ 채점 실패 | - |")
            details.append(f"\n## {case['name']}\n\n⚠️ 채점에 실패했어요 (API 오류 또는 JSON 형식 오류):\n\n```\n{runs[0]['error'][:300]}\n```\n")
            continue  # 아래 코드는 건너뛰고 다음 반복으로

        first = valid[0]  # 표에는 1회차 결과를 대표로 표시
        avg, result = verdict(first["scores"])

        # ── 일관성 검사 ──
        # {집합} 은 중복을 없애요. 반복 채점 점수들이 전부 같으면 집합 크기가 1
        # → 크기가 1보다 크면 '점수가 달라진 항목'
        changed = [k for k in keys if len({r["scores"][k] for r in valid}) > 1]
        verdicts = {verdict(r["scores"])[1] for r in valid}  # 회차별 PASS/FAIL 모음
        if changed:
            unstable += 1
        # 예: "accuracy(4/3)" → 1회차 4점, 2회차 3점
        drift = "없음" if not changed else ", ".join(
            f"{k}({'/'.join(str(r['scores'][k]) for r in valid)})" for k in changed
        )
        if len(verdicts) > 1:  # PASS 와 FAIL 이 둘 다 나왔으면
            drift += " ⚠️판정 뒤집힘"
        if len(valid) < len(runs):  # 반복 중 일부가 실패했으면 표시 (비교 횟수가 줄었다는 뜻)
            drift += f" ({len(runs) - len(valid)}회 채점 실패)"

        # 요약 표에 한 줄 추가
        lines.append(
            f"| {case['name']} | " + " | ".join(str(first["scores"][k]) for k in keys)
            + f" | {avg:.2f} | {result} | {drift} |"  # :.2f → 소수점 둘째 자리까지
        )

        # 상세 근거 섹션 만들기
        # .get(키, 기본값) : 키가 없어도 에러 없이 기본값을 돌려줌 (Judge가 빠뜨렸을 때 대비)
        reasons = first.get("reasons", {})
        issues = first.get("issues", [])
        details.append(
            f"\n## {case['name']}\n\n"
            + "\n".join(f"- **{k}** {first['scores'][k]}점: {reasons.get(k, '')}" for k in keys)
            + "\n\n**발견된 문제**\n"
            + ("\n".join(f"- {x}" for x in issues) if issues else "- 없음")
            + "\n"
        )

    # 리포트 마무리: 일관성 요약 + 사람이 채울 칸
    lines += [  # += : 리스트 뒤에 여러 줄 한꺼번에 추가
        "",
        f"**Judge 일관성:** {len(cases)}개 중 {unstable}개에서 반복 채점 점수가 달라짐",
        "",
        "## 사람 검수 (직접 작성)",
        "- Judge 점수에 동의하지 않는 항목과 이유:",
        "- 루브릭에서 고치고 싶은 점:",
    ]

    Path("judge_report.md").write_text("\n".join(lines) + "\n" + "\n".join(details), encoding="utf-8")
    print("\n완료! judge_report.md 를 열어보세요.")
    print("QA 미션: Judge의 점수와 근거에 내가 동의하는지 '사람 검수' 칸을 채워보세요.")
