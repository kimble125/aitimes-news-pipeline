# SHARED_PROMPT.md — 팀 공통 AI 프롬프트 제안안

> **문서 성격: 제안안(draft proposal)**  
> 아래 블록을 ChatGPT / Claude / Cursor 등에 **그대로 붙여넣고** 작업을 시작하세요.  
> 모델 선택·추가 지시·작업 순서는 팀원 자율입니다. 코드베이스 경로와 INTERFACE 계약만 맞춰 주세요.

---

## A. 공통 프롬프트 블록 (전원 붙여넣기)

```text
당신은 대학 팀 과제(A2-2 / Project B)용 Python CLI 파이프라인 구현을 돕는 엔지니어다.

프로젝트명: aitimes-news-pipeline
목표 소스: https://www.aitimes.com/
언어: Python 3.10+
진입점: main.py (argparse 서브커맨드)
영속 저장: SQLite (data/pipeline.db)
설정: config/config.json + .env (AI_API_KEY, AI_BASE_URL, AI_MODEL) — 시크릿을 코드/커밋에 넣지 말 것
웹 UI 금지

필수 서브커맨드:
- fetch   : RSS 및 크롤링(BeautifulSoup; Selenium은 선택)으로 기사 수집 → news_raw
- clean   : raw → news_clean (HTML 제거, 정규화, raw/clean 분리)
- summarize : AI 요약 → news_summary
- analyze : AI 인사이트(트렌드/키워드/유사차이/시사점 중 2+) → news_analysis (구조화 JSON)
- report  : 품질지표 2+, TOP N, AI 인사이트 / 콘솔+TXT|MD, matplotlib 차트 2+(카테고리 건수, 일별 추이, 한글폰트 PNG)
- export  : CSV/JSONL/Excel 중 최소 2형식

중복: url(및 guid) 기준 skip 또는 upsert (config.duplicate_policy)
로깅: INFO/WARNING/ERROR
모듈 구조 유지: src/collectors, cleaners, ai, report, storage, utils
문서 docs/INTERFACE.md 의 컬럼·경로·status 계약을 깨지 말 것.
가짜 메트릭을 하드코딩하지 말 것. DB에서 계산할 것.
응답은 구체적 패치/코드 위주로, 기존 stub의 NotImplementedError를 실제 구현으로 교체하는 방향을 우선한다.
UTF-8. 팀 대면 문서/로그 메시지는 한국어 가능.
```

---

## B. 역할별 추가분 (해당 역할만 이어서 붙여넣기)

### B-1. Collect/Clean (fetch + clean)

```text
[역할: Collect/Clean — 수집·정제]
우선 구현:
1) src/collectors/base.py, rss.py, crawl.py
2) src/cleaners/cleaner.py
3) main.py 의 fetch, clean 핸들러 연결

CLI 계약:
- python main.py fetch --source aitimes --method rss|crawl --limit N [--max-pages N]
- python main.py clean [--source aitimes] [--limit N] [--force]

수집 전략:
- RSS URL은 config.sources.aitimes.rss_urls 사용. 실패 시 로깅 후 crawl 폴백 가능하도록.
- crawl: list 페이지에서 링크 수집 → detail에서 title/body/date/category.
- config.crawl.delay_sec 만큼 요청 사이 대기. User-Agent 설정.
- news_raw 필드: source, method, guid, url, title, published_at, category, author, raw_html, raw_text, fetched_at, status, error_message
- 중복 url → skip(기본) 또는 upsert.

정제:
- raw_html/raw_text → body_text (태그 제거, 공백 정규화)
- word_count 계산, 빈 본문은 status=empty
- news_clean 에 raw_id FK 유지

DoD:
- method=rss 로 limit=10 실행 시 신규/스킵/실패 건수 로그
- clean 후 news_clean 행 생성
- 단위 실행이 크래시 없이 끝나며, 네트워크 오류는 status=error 로 남김

지금은 report/export/AI 본문을 수정하지 말고, storage API가 있으면 재사용하라.
```

### B-2. Summarize/Analyze (summarize + analyze)

```text
[역할: Summarize/Analyze — AI 요약·분석]
우선 구현:
1) src/ai/summarizer.py
2) src/ai/analyzer.py
3) main.py 의 summarize, analyze 핸들러

환경변수: AI_API_KEY, AI_BASE_URL, AI_MODEL (python-dotenv)
OpenAI-compatible Chat Completions 사용. 키 없으면 ERROR 로그 후 명확히 중단 또는 skip(팀 합의된 동작).

CLI 계약:
- python main.py summarize --unsummarized [--limit N] [--clean-id ID]
- python main.py analyze [--limit N] [--since YYYY-MM-DD]

summarize:
- 입력: news_clean.title + body_text (너무 길면 잘라서 토큰 가드)
- 출력: 한국어 요약 3~8문장 권장 → news_summary (clean_id UNIQUE upsert)
- model, prompt_version 저장

analyze:
- 여러 기사(요약 우선, 없으면 본문 일부)를 배치로 보내 구조화 JSON 생성
- insights_json 에 최소 2개 키 채우기: trends, keywords, similarities_differences, implications 중 선택
- news_analysis 에 batch_key 와 함께 저장

프롬프트 예시 요구:
- 요약: 사실 위주, 추측 금지, 한국어
- 분석: JSON only (코드펜스 없이) 스키마 준수

DoD:
- summarize 1건 이상 status=ok (키 있는 환경)
- analyze JSON에 필드 2개 이상
- API 예외 시 traceback만 던지지 말고 status=error + 로그

collectors/cleaners/report 대량 수정 금지. DB 헬퍼 재사용.
```

### B-3. Lead/Report (report + export + 통합)

```text
[역할: Lead/Report — 시각화·리포트·export·repo 통합]
우선 구현:
1) src/storage/db.py 스키마/헬퍼 안정화
2) src/report/charts.py, reporter.py, exporter.py
3) main.py report/export 및 팀 PR 머지
4) README 실행성 유지

CLI 계약:
- python main.py report [--top-n N] [--format txt|md|both]
- python main.py export [--formats csv,jsonl,xlsx]

charts (matplotlib):
- 카테고리별 기사 수 막대그래프
- 일별 건수 추이 선그래프
- 한글 폰트 설정(시스템 폰트 탐지), PNG를 outputs/charts/ 저장
- 데이터 없으면 빈 차트 대신 WARNING 로그

report:
- 품질 지표 최소 2개 (예: 수집 성공률, 요약 커버리지) — DB에서 계산, 하드코딩 금지
- TOP N 기사 목록
- 최신 news_analysis.insights_json 요약 섹션
- 콘솔 출력 + outputs/reports/report.YYYYMMDD.md (또는 txt)

export:
- news_clean (+ summary 조인 가능)을 CSV, JSONL 필수에 가깝게, xlsx 권장
- outputs/ 아래 저장

통합:
- 팀원 브랜치 merge, 충돌 시 INTERFACE 우선
- .gitignore 로 .env, *.db, 산출물 제외 확인
- 9/8 E2E, 9/9 제출

DoD:
- PNG 2+, report 파일, export 파일 2형식+
- secrets 없음
```

---

## C. 사용 팁 (제안)

1. 공통 블록 + 본인 역할 블록만 붙인다.  
2. “현재 파일 내용을 읽고 stub을 구현해줘”처럼 **파일 경로를  Explicit** 하게 요청한다.  
3. 스키마 변경이 필요하면 코드와 함께 `docs/INTERFACE.md` 패치를 요청한다.  
4. API 키를 채팅에 붙여넣지 않는다.

---

*제안안 — 팀원이 더 짧은/긴 개인 프롬프트로 바꿔 써도 됩니다.*
