# agent-study · 1주차: LLM API 기초 체력

QA 엔지니어에서 AI 에이전트 엔지니어로 가는 4주 학습 기록.
1주차 목표: Python으로 LLM API(Google Gemini 무료)를 호출하고, 시스템 프롬프트에 따라 출력이 어떻게 달라지는지 실험한다.

---

## 📁 폴더 구조

```
agent-study/
├── README.md              ← 이 파일
├── requirements.txt       ← 설치할 패키지 목록
├── .gitignore             ← GitHub에 올리지 않을 파일 목록
├── .env.example           ← API 키 양식 (실제 키는 .env 에)
└── week1/
    ├── llm.py              ← API 호출을 모아둔 파일 (모델 교체 시 여기만 수정)
    ├── step1_hello.py
    ├── step2_system_prompt.py
    └── step3_my_notes.py
```

> 받은 파일 중 `README.md`, `requirements.txt`, `.gitignore`, `.env.example`은 **agent-study 폴더 바로 아래**,
> `llm.py`와 `step*.py` 3개는 **week1 폴더 안**에 넣으세요.

---

## 🛠 STEP 0. 설치 (처음 한 번만, 약 30분)

### 0-1. Python 설치
1. https://www.python.org/downloads 에서 최신 버전 다운로드
2. **Windows: 설치 첫 화면에서 `Add python.exe to PATH` 반드시 체크** ✅
3. 설치 후 확인 (Windows는 PowerShell, Mac은 터미널):
   ```
   python --version
   ```
   `Python 3.10` 이상이 나오면 OK. (Mac은 `python3 --version`)

### 0-2. VS Code 설치
1. https://code.visualstudio.com 에서 설치
2. VS Code 실행 → 왼쪽 세로줄의 **확장(Extensions, 네모 4개 아이콘)** 클릭
3. `Python` 검색 → Microsoft가 만든 것 설치

### 0-3. Git 설치 + GitHub 가입
1. https://git-scm.com 에서 Git 설치 (옵션은 전부 기본값으로 Next)
2. https://github.com 가입
3. 터미널에서 내 정보 등록 (한 번만):
   ```
   git config --global user.name "내이름"
   git config --global user.email "github가입이메일"
   ```

### 0-4. Gemini API 키 발급 (무료, 카드 등록 불필요)
1. https://aistudio.google.com 접속 → Google 계정으로 로그인
2. 왼쪽 메뉴 **Get API key** → **Create API key** → 키 복사
3. 결제 계정을 연결하지 않으면 무료 등급으로만 동작해서 요금이 나가지 않아요.
   ⚠️ 무료 등급은 입력 내용이 Google 제품 개선에 쓰일 수 있어요. 개인정보·회사 자료는 넣지 마세요.
   ⚠️ 무료 등급은 분당/일일 요청 한도가 있어요. 초과하면 `429` 에러 → 잠시 후 다시 실행.

---

## 📂 STEP 1. 프로젝트 폴더 열기

1. 원하는 위치에 `agent-study` 폴더 만들기 (예: `문서/agent-study`)
2. 그 안에 `week1` 폴더 만들기
3. 받은 파일들을 위 **폴더 구조**대로 넣기
4. VS Code → **File → Open Folder** → `agent-study` 선택
   - "이 폴더의 작성자를 신뢰합니까?" → **Yes**
5. VS Code 메뉴 **Terminal → New Terminal** (단축키 `` Ctrl+` ``)
   → 아래쪽에 터미널이 열려요. 이후 명령어는 전부 여기서 입력!

---

## 🐍 STEP 2. 가상환경 + 패키지 설치

가상환경 = 이 프로젝트 전용 Python 공간. 다른 프로젝트와 패키지가 섞이지 않게 해요.

**Windows (PowerShell)**
```
python -m venv .venv
.venv\Scripts\Activate.ps1
```
> 빨간 에러("스크립트를 실행할 수 없으므로…")가 나면 아래를 한 번 실행 후 다시 시도:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` → `Y`

**Mac**
```
python3 -m venv .venv
source .venv/bin/activate
```

✅ 성공하면 터미널 줄 맨 앞에 `(.venv)`가 붙어요.

이어서 패키지 설치:
```
pip install -r requirements.txt
```

VS Code 오른쪽 아래에 "가상환경을 선택할까요?" 알림이 뜨면 **Yes**.
(안 뜨면 `Ctrl+Shift+P` → `Python: Select Interpreter` → `.venv` 선택)

---

## 🔑 STEP 3. API 키 넣기

1. VS Code 왼쪽 파일 목록에서 `.env.example` 우클릭 → **Copy** → 빈 곳에 **Paste**
2. 복사된 파일 이름을 **`.env`** 로 변경
3. `.env` 열어서 `여기에_키_붙여넣기` 부분을 실제 키로 교체 → 저장 (`Ctrl+S`)

```
GEMINI_API_KEY=AIzaSyxxxxxxxx
GEMINI_MODEL=gemini-3.5-flash
```

✅ `.env`는 `.gitignore`에 등록돼 있어서 GitHub에 올라가지 않아요.

---

## ▶️ STEP 4. 실습 실행

터미널에서 (앞에 `(.venv)` 붙어 있는지 확인!):

```
cd week1
python llm.py
```
→ 내 키로 쓸 수 있는 모델 목록이 나오면 연결 성공! (`GEMINI_MODEL`에 적은 모델이 목록에 있는지 확인)

```
python step1_hello.py
```

| 파일 | 배우는 것 | 실행 명령 |
|---|---|---|
| step1_hello.py | API 호출, 응답 구조, 토큰, temperature | `python step1_hello.py` |
| step2_system_prompt.py | 시스템 프롬프트 비교, 결과 파일 저장 | `python step2_system_prompt.py` |
| step3_my_notes.py | 내 노트로 요약+퀴즈 (2주차 RAG 예고편) | `python step3_my_notes.py 내노트.txt` |

### 미션
- **step1**: temperature 0 vs 1, 같은 질문 3번씩 → 답이 얼마나 달라지나?
- **step2**: `results.md` 열어서 "한 줄 평가" 칸 직접 채우기. 내 페르소나 하나 추가해서 재실행.
- **step3**: 공부 노트를 `.txt`로 저장해 넣어보기 → 퀴즈 근거가 실제 노트에 있는지 대조 (QA 관점!)
- **보너스**: `.env`의 `GEMINI_MODEL`을 Flash-Lite 같은 다른 모델로 바꿔서 품질·토큰 비교

---

## 🚀 STEP 5. GitHub에 올리기

### 5-1. GitHub에 저장소 만들기
1. github.com 로그인 → 오른쪽 위 **+ → New repository**
2. Repository name: `agent-study`
3. Public 선택 (포트폴리오용)
4. **README, .gitignore 추가 옵션은 체크하지 말기** (이미 있으니까요)
5. **Create repository** → 나오는 주소 복사 (`https://github.com/내아이디/agent-study.git`)

### 5-2. 첫 업로드 (터미널, `agent-study` 폴더 위치에서)
```
cd ..
git init
git add .
git status
```

⚠️ **`git status` 결과에 `.env`가 보이면 절대 다음 단계로 가지 마세요!**
(`.gitignore`가 같은 폴더에 있는지 확인)

```
git commit -m "week1: Gemini API 기초 실습"
git branch -M main
git remote add origin https://github.com/내아이디/agent-study.git
git push -u origin main
```

처음 push하면 브라우저로 GitHub 로그인 창이 떠요 → 승인.

### 5-3. 이후 기록할 때마다
```
git add .
git commit -m "week1: step2 시스템 프롬프트 비교 결과 추가"
git push
```

💡 VS Code 왼쪽 **소스 제어(Source Control)** 아이콘으로 클릭만으로도 할 수 있어요.

---

## 📝 학습 기록 (직접 채우기)

### 1주차 체크리스트
- [o] API 호출 성공
- [o] temperature 0 vs 1 차이를 설명할 수 있다
- [o] 시스템 프롬프트 3개 이상 비교한 results.md 작성
- [ ] 내 노트로 퀴즈 생성 + 환각 여부 검증
- [ ] GitHub에 push 완료

### 배운 점 / 실험 결과
- temperature 실험: 0일 경우 3번의 답변의 단어들이 통일성을 가지고 있다. 1일 경우 단어들의 통일성이 떨어지나 답변이 자연스러운 느낌이 든다.
- 가장 효과 있던 시스템 프롬프트: 10년차 엔지니어, 면접관, 초등학교 선생님, QA 학생 순으로 설명이 좋았던 것 같음.
- 환각 발견 사례:

---

## 🆘 자주 나는 에러

| 에러 | 해결 |
|---|---|
| `python`을 찾을 수 없음 | Python 재설치 시 `Add to PATH` 체크, 터미널 새로 열기 |
| `ModuleNotFoundError: google` / `dotenv` | `(.venv)` 켜져 있는지 확인 → `pip install -r requirements.txt` |
| `API key not valid` / `400` / `403` | `.env` 파일 이름·키 값 확인 (공백, 따옴표 없이) |
| `404 ... model not found` | `python llm.py`로 목록 확인 → `.env`의 `GEMINI_MODEL` 수정 |
| `429 RESOURCE_EXHAUSTED` | 무료 한도 초과 → 1분 기다리거나, 다음 날 다시. 또는 Flash-Lite 모델로 변경 |
| `can't open file 'step1_hello.py'` | `cd week1` 했는지 확인 |
| 실수로 `.env`를 push함 | **즉시 AI Studio에서 키 삭제 후 새로 발급** |
