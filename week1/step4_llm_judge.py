"""
step4: LLM Judge — step2 결과(results.md)를 LLM이 기준표(루브릭)로 채점하기
- 실행: python step4_llm_judge.py            (기본: 각 답변을 2번씩 채점)
        python step4_llm_judge.py --repeat 3
- 배우는 것:
  1) 루브릭 설계: "좋은 답변"을 평가 기준(Dimension)과 점수(Metric)로 쪼개기
  2) JSON 출력: 채점 결과를 코드가 읽을 수 있는 형태로 받기
  3) Judge 일관성 검사: 같은 답변을 여러 번 채점했을 때 점수가 흔들리는지 확인
     → "어제 PASS, 오늘 FAIL"이 Judge 자체에서도 생길 수 있어요!
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

from llm import MODEL, ask

# ── 1. 평가 기준(루브릭) ─────────────────────────────────────────
# 책에서 배운 기준으로 자유롭게 바꿔보세요. 기준이 바뀌면 점수도 바뀌어요.
RUBRIC = {
    "persona": "페르소나 준수: 시스템 프롬프트가 요구한 역할·말투·출력 형식을 지켰는가",
    "accuracy": "사실 정확성: RAG/파인튜닝에 대한 설명에 틀린 내용이 없는가",
    "calibration": "표현의 신중함: 근거 없이 단정하거나 과장한 표현(예: '항상', '표준', '완벽하게')이 없는가",
    "relevance": "질문 적합성: 사용자의 질문에 맞는 내용을 적절한 분량으로 답했는가",
}

PASS_AVG = 4.0   # 평균 4점 이상
PASS_MIN = 3     # 그리고 모든 항목 3점 이상이어야 PASS

JUDGE_SYSTEM = """너는 AI 답변 품질을 평가하는 엄격하고 공정한 QA 평가자야.
- 주어진 루브릭의 각 항목을 1~5점 정수로 채점해. (5=매우 우수, 3=보통/일부 문제, 1=심각한 문제)
- 점수마다 답변 속 구체적인 근거(문장이나 표현)를 짧게 들어.
- 답변이 길다고 점수를 더 주지 마.
- 반드시 지정된 JSON 형식으로만 답해."""

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
    """step2가 만든 results.md에서 질문과 페르소나별 (시스템 프롬프트, 답변)을 꺼내요."""
    text = path.read_text(encoding="utf-8")
    q = re.search(r"^- 질문: (.+)$", text, re.M)
    question = q.group(1).strip() if q else "(질문 정보 없음)"

    cases = []
    for section in re.split(r"\n## ", text)[1:]:
        name, _, body = section.partition("\n")
        sp = re.search(r"\*\*시스템 프롬프트:\*\* (.*)", body)
        system_prompt = sp.group(1).strip() if sp else "(없음)"
        answer = body[sp.end():].strip() if sp else body.strip()
        cases.append({"name": name.strip(), "system_prompt": system_prompt, "answer": answer})
    return question, cases


# ── 3. 채점 ─────────────────────────────────────────────────────
def judge_once(question: str, case: dict) -> dict:
    prompt = JUDGE_TEMPLATE.format(
        question=question,
        system_prompt=case["system_prompt"],
        answer=case["answer"],
        rubric="\n".join(f"- {k}: {v}" for k, v in RUBRIC.items()),
        score_keys=", ".join(f'"{k}": 1~5' for k in RUBRIC),
        reason_keys=", ".join(f'"{k}": "근거"' for k in RUBRIC),
    )
    result = ask(prompt, system=JUDGE_SYSTEM, temperature=0, json_output=True)
    try:
        data = json.loads(result.text)
        scores = {k: int(data["scores"][k]) for k in RUBRIC}
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Judge가 형식을 안 지킨 것도 하나의 '결함'이에요. 기록하고 넘어가요.
        return {"error": result.text[:300]}
    data["scores"] = scores
    return data


def verdict(scores: dict) -> tuple[float, str]:
    avg = sum(scores.values()) / len(scores)
    ok = avg >= PASS_AVG and min(scores.values()) >= PASS_MIN
    return avg, "✅ PASS" if ok else "❌ FAIL"


# ── 4. 실행 + 리포트 ────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="results.md")
    parser.add_argument("--repeat", type=int, default=2, help="같은 답변을 몇 번 채점할지 (일관성 검사)")
    args = parser.parse_args()

    question, cases = parse_results(Path(args.file))
    print(f"채점 대상 {len(cases)}개 × {args.repeat}회 / Judge 모델: {MODEL}\n")

    keys = list(RUBRIC)
    lines = [
        "# LLM Judge 채점 리포트",
        f"- 실행 시각: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Judge 모델: {MODEL} (temperature 0)",
        f"- 질문: {question}",
        f"- 판정 기준: 평균 {PASS_AVG} 이상 + 모든 항목 {PASS_MIN}점 이상 → PASS",
        f"- 반복 채점: {args.repeat}회",
        "",
        "## 루브릭",
        *[f"- **{k}**: {v}" for k, v in RUBRIC.items()],
        "",
        "## 요약 (1회차 기준)",
        "",
        "| 페르소나 | " + " | ".join(keys) + " | 평균 | 판정 | 반복 시 점수 변동 |",
        "|---|" + "---|" * (len(keys) + 3),
    ]
    details = []
    unstable = 0

    for case in cases:
        runs = []
        for i in range(args.repeat):
            print(f"채점 중: {case['name']} ({i + 1}/{args.repeat})")
            runs.append(judge_once(question, case))

        valid = [r for r in runs if "error" not in r]
        if not valid:
            lines.append(f"| {case['name']} | " + " | ".join("-" for _ in keys) + " | - | ⚠️ 파싱 실패 | - |")
            details.append(f"\n## {case['name']}\n\n⚠️ Judge 응답을 JSON으로 읽지 못했어요:\n\n```\n{runs[0]['error']}\n```\n")
            continue

        first = valid[0]
        avg, result = verdict(first["scores"])

        # 일관성: 반복 채점에서 점수가 달라진 항목 찾기
        changed = [k for k in keys if len({r["scores"][k] for r in valid}) > 1]
        verdicts = {verdict(r["scores"])[1] for r in valid}
        if changed:
            unstable += 1
        drift = "없음" if not changed else ", ".join(
            f"{k}({'/'.join(str(r['scores'][k]) for r in valid)})" for k in changed
        )
        if len(verdicts) > 1:
            drift += " ⚠️판정 뒤집힘"

        lines.append(
            f"| {case['name']} | " + " | ".join(str(first["scores"][k]) for k in keys)
            + f" | {avg:.2f} | {result} | {drift} |"
        )

        reasons = first.get("reasons", {})
        issues = first.get("issues", [])
        details.append(
            f"\n## {case['name']}\n\n"
            + "\n".join(f"- **{k}** {first['scores'][k]}점: {reasons.get(k, '')}" for k in keys)
            + "\n\n**발견된 문제**\n"
            + ("\n".join(f"- {x}" for x in issues) if issues else "- 없음")
            + "\n"
        )

    lines += [
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
