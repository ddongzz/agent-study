# 2주차: RAG (검색 증강 생성)

목표: 내 공부 노트에서 **질문과 관련된 부분만 찾아서** 답하는 지식 비서를 직접 만들고,
**청킹 방식에 따라 검색 품질이 어떻게 달라지는지** 평가한다.

```
노트 ──① 청킹──▶ 조각들 ──② 임베딩──▶ 벡터 저장
                                          │
질문 ──② 임베딩──▶ 질문 벡터 ──③ 유사도 검색──▶ Top-k 조각 ──④ 답변 생성(+출처)
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| llm.py | 1주차 llm.py + `embed()` (텍스트 → 벡터) |
| chunkers.py | 청킹 3가지: fixed / overlap / heading |
| vector_store.py | 직접 만든 미니 벡터 DB (코사인 유사도 검색 + 임베딩 캐시) |
| step1_chunking.py | 청킹 결과 눈으로 비교 → `chunks_preview.md` |
| step2_search.py | 질문 입력 → 비슷한 조각 Top-3 |
| step3_rag_answer.py | 검색한 조각으로 출처 달린 답변 생성 |
| step4_retrieval_eval.py | 청킹 3종 검색 품질 비교 → `retrieval_report.md` |
| eval_set.json | 평가용 질문 10개 + 정답 문구 |

노트는 기본으로 `../week1/notes/my_notes.txt`를 사용해요. 다른 노트는 `--notes 경로`로 지정.

## 준비

```
cd week2
python llm.py
```
→ **임베딩 모델 목록**에 `gemini-embedding-001`이 있는지 확인.
없으면 목록의 임베딩 모델 이름을 `.env`에 `EMBED_MODEL=모델이름`으로 추가.

## 실습 순서

| 단계 | 실행 | 미션 |
|---|---|---|
| 1 | `python step1_chunking.py` | `chunks_preview.md`에서 문장이 중간에 잘린 조각 찾기 (API 호출 없음) |
| 2 | `python step2_search.py` | 노트에 없는 단어로 질문해도 의미로 찾아오는지 확인 |
| 3 | `python step3_rag_answer.py "soft target이 뭐야?"` | 출처 번호가 맞는지, 노트에 없는 질문에 지어내지 않는지 확인 |
| 4 | `python step4_retrieval_eval.py` | 어떤 청킹이 가장 잘 찾는지 + ❌ 문항의 실패 원인 분석 |

## 배운 점 (직접 작성)
- 청킹:
- 임베딩/유사도:
- 검색 평가(Hit@k, MRR):
- 1주차(노트 전체 투입) 대비 토큰 변화:

## 2주차 확장 아이디어
- [ ] 손 노트 사진 → 텍스트 변환 후 노트에 추가 (Gemini 이미지 입력)
- [ ] 평가 문항 직접 10개 더 만들기
- [ ] Top-k 값(1, 3, 5)에 따른 Hit 비교
- [ ] step3 답변을 1주차 LLM Judge로 채점하기 (근거 일치 루브릭)
