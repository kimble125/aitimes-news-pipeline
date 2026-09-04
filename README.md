# AI타임스 뉴스 파이프라인 (A2-2 / Project B)

AI타임스(https://www.aitimes.com/) 기사를 수집·정제·AI 요약·분석·시각화·리포트·내보내기까지 수행하는 CLI 파이프라인입니다.

> **문서 안내:** `docs/PLAN.md`, `docs/ACTION_PLAN.md`, `docs/SHARED_PROMPT.md`, `docs/INTERFACE.md`는 **제안안(draft proposal)** 입니다.  
> 모델 선택, 세부 일정, 작업 시간 배분은 각 팀원이 **자율적으로** 결정합니다. 인터페이스·DoD만 맞추면 됩니다.

## 팀 역할

| 역할 | 담당 | 주요 범위 |
|------|------|-----------|
| 팀장 / 제출·통합 | **Lead/Report** | GitHub repo·merge·push, storage/CLI 스켈레톤, 시각화·리포트·export, README·최종 제출 |
| 수집·정제 | **Collect/Clean** | `fetch`(RSS + 크롤링), `clean`, raw/clean 스키마·중복 처리 |
| 요약·분석 | **Summarize/Analyze** | `summarize`(AI), `analyze`(인사이트 2종 이상), 구조화 JSON 출력 |

공유 원칙: 각자 브랜치에 커밋 → Lead/Report이 main에 merge/push.

## 요구사항 충족 요약

- CLI argparse 서브커맨드: `fetch`, `clean`, `summarize`, `analyze`, `report`, `export`
- RSS/API **및** 크롤링(BeautifulSoup) 병행
- raw/clean 분리, 중복 skip/upsert
- AI 요약 + 인사이트 분석(트렌드·키워드·유사/차이·시사점 중 2+)
- matplotlib 차트 2종+(카테고리 건수, 일별 추이), 한글 폰트, PNG
- 리포트: 품질 지표 2+, TOP N, AI 인사이트 — 콘솔 + TXT/MD
- Export: CSV / JSONL / Excel 중 최소 2종
- `config.json`, 로깅 INFO/WARNING/ERROR
- 영속 저장: SQLite 권장
- 모듈 4개 이상, Python 3.10+, 웹 UI 없음, API 키는 코드에 없음

## 빠른 시작

```bash
# 1) 가상환경
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2) 의존성
pip install -r requirements.txt

# 3) 설정
cp .env.example .env
cp config/config.example.json config/config.json
# .env 에 AI_API_KEY 등 입력 (커밋 금지)

# 4) 도움말
python main.py --help
python main.py fetch --help
```

## CLI 사용 예시 (제안)

```bash
# 수집 (RSS 또는 crawl)
python main.py fetch --source aitimes --method rss --limit 30
python main.py fetch --source aitimes --method crawl --limit 20 --max-pages 3

# 정제
python main.py clean --source aitimes

# AI 요약 / 분석
python main.py summarize --unsummarized --limit 20
python main.py analyze --limit 50

# 리포트 / 차트 / 내보내기
python main.py report --top-n 10 --format md
python main.py export --formats csv,jsonl,xlsx
```

현재 스켈레톤은 서브커맨드가 연결만 되어 있고, 본 구현은 담당자가 채웁니다. 미구현 시 `NotImplementedError` 또는 빈 결과 + 로그를 남깁니다.

## 디렉터리 구조

```
aitimes-news-pipeline/
├── main.py                 # CLI 진입점
├── config/
│   └── config.example.json
├── data/
│   ├── raw/                # 원문 스냅샷(선택)
│   ├── clean/
│   └── pipeline.db         # SQLite (gitignore)
├── docs/
│   ├── PLAN.md             # 제안안: 설계
│   ├── ACTION_PLAN.md      # 제안안: 일정
│   ├── SHARED_PROMPT.md    # 제안안: 공통 프롬프트
│   └── INTERFACE.md        # 역할 간 계약
├── logs/
├── outputs/
│   ├── charts/
│   └── reports/
├── src/
│   ├── collectors/         # RSS / crawl (Collect/Clean)
│   ├── cleaners/           # clean (Collect/Clean)
│   ├── ai/                 # summarize / analyze (Summarize/Analyze)
│   ├── report/             # charts / reporter / exporter (Lead/Report)
│   ├── storage/            # SQLite (Lead/Report 주도, 공유)
│   └── utils/              # config, logging
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 기여 방법 (브랜치)

제안 브랜치 네이밍:

```
feature/<이름이니셜>-<작업>
예: feature/jj-fetch-rss
    feature/psb-summarize
    feature/khy-charts-report
```

1. `main`에서 브랜치 생성
2. 본인 모듈 + 필요 시 `docs/INTERFACE.md` 계약 준수
3. PR 또는 호연에게 merge 요청
4. secrets(`.env`, API 키) 커밋 금지

## 마감

- **제출 마감:** 2026-09-09 (수)
- **오늘(2026-09-04):** 기획·repo 세팅일 (호연)

자세한 일정 제안은 `docs/ACTION_PLAN.md`를 참고하세요.
