# EVALUATION.md — 평가자용 요구사항 대조표

> 과제 요구사항 하나하나가 **어느 파일에 구현되어 있고, 어느 명령으로 확인되는지**를 정리한 문서입니다.
> 위에서부터 순서대로 실행하면 전체 기능을 검증할 수 있습니다.

## 0. 준비 (1분)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.json config/config.json
cp .env.example .env      # AI_API_KEY 입력 (요약·분석 검증에 필요)
```

## 1. 검증 명령 순서

| # | 명령 | 무엇이 확인되는가 |
|---|------|-------------------|
| 1 | `python main.py --help` | argparse 서브커맨드 6종 존재 |
| 2 | `python main.py initdb` | SQLite 4테이블 생성 + 적재 현황 출력 |
| 3 | `python main.py fetch --method rss --limit 20` | RSS 수집, 신규/중복/실패 건수 로그 |
| 4 | `python main.py fetch --method crawl --limit 10` | 크롤링 수집, 요청 지연 적용 |
| 5 | `python main.py clean --limit 30` | raw → clean 분리 저장, 정규화 |
| 6 | `python main.py summarize --unsummarized --limit 20` | AI 요약, 기요약 건 스킵 |
| 7 | `python main.py analyze --limit 50` | 인사이트 JSON 저장 |
| 8 | `python main.py report --top-n 10 --format md` | 차트 PNG 2종 + 리포트 콘솔/파일 |
| 9 | `python main.py export --formats csv,jsonl` | 2개 이상 포맷 파일 생성 |

검증 후 확인할 산출물: `outputs/charts/*.png`, `outputs/reports/*.md`, `outputs/*.csv`, `outputs/*.jsonl`, `logs/pipeline.log`, `data/pipeline.db`

DB 직접 확인:
```bash
sqlite3 data/pipeline.db ".tables"
sqlite3 data/pipeline.db "SELECT status, COUNT(*) FROM news_raw GROUP BY status;"
sqlite3 data/pipeline.db "SELECT COUNT(*) FROM news_clean; SELECT COUNT(*) FROM news_summary;"
```

---

## 2. 기능 요구사항 대조표

| # | 요구사항 | 구현 위치 | 확인 방법 |
|---|----------|-----------|-----------|
| 1 | **CLI 설계** — argparse 서브커맨드 `fetch/clean/summarize/analyze/report/export` + 옵션 | `main.py` (`build_parser`) | `python main.py --help`, `python main.py fetch --help` |
| 2-1 | **수집 방법 1** — RSS/API | `src/collectors/rss.py` (`RSSCollector`) | `fetch --method rss` |
| 2-2 | **수집 방법 2** — 크롤링 (BeautifulSoup) | `src/collectors/crawl.py` (`CrawlCollector`) | `fetch --method crawl` |
| 2-3 | **타임아웃·오류 처리** | `config.timeouts.*` + 각 collector 의 `requests` 호출 | 로그의 WARNING/ERROR, `news_raw.status='error'` |
| 2-4 | **raw 저장 (수집시각·소스·수집방법 포함)** | `news_raw` 테이블 `fetched_at`, `source`, `method` — `src/storage/db.py` | `sqlite3 data/pipeline.db "SELECT source,method,fetched_at FROM news_raw LIMIT 3;"` |
| 3-1 | **정제 규칙** — 필수필드 검증·텍스트 정규화·날짜 통일·결측 처리 | `src/cleaners/cleaner.py` (`clean_article`) | `clean` 실행 후 `news_clean.body_text`, `published_at` |
| 3-2 | **중복 처리 skip/upsert** | `src/storage/db.py` (`upsert_raw`) + `config.duplicate_policy` | 같은 `fetch` 를 두 번 실행 → 두 번째는 "중복 스킵" 로그 |
| 3-3 | **clean 별도 저장** | `news_clean` 테이블 (raw 를 덮어쓰지 않음) | `SELECT COUNT(*) FROM news_raw; SELECT COUNT(*) FROM news_clean;` |
| 4-1 | **AI 요약** | `src/ai/summarizer.py` (`summarize_article`) | `summarize` 후 `news_summary.summary_text` |
| 4-2 | **대상 선택 옵션** `--all / --id / --unsummarized` | `main.py` summarize 파서 | `python main.py summarize --help` |
| 4-3 | **실패 시 로깅 후 스킵 / 기요약 스킵** | `run_summarize` + `news_summary.status='error'` | 로그, `SELECT status FROM news_summary;` |
| 5-1 | **조건별 인사이트 분석** (`--since`, `--category`) | `src/ai/analyzer.py` (`run_analyze`) | `python main.py analyze --help` |
| 5-2 | **분석 항목 2개 이상** (트렌드/키워드/공통점·차이점/시사점) | `news_analysis.insights_json` — 스키마는 `docs/INTERFACE.md` §2.4 | `sqlite3 data/pipeline.db "SELECT insights_json FROM news_analysis;"` |
| 5-3 | **분석 결과 저장·조회** | `news_analysis` 테이블, `get_latest_analysis()` | 리포트의 "AI 인사이트" 섹션 |
| 6-1 | **matplotlib 차트 2종** (카테고리별 건수 / 일자별 추이) | `src/report/charts.py` (`make_charts`) + `db.category_counts`, `db.daily_counts` | `report` 실행 후 `outputs/charts/*.png` 2개 |
| 6-2 | **한글 폰트 + PNG 저장** | `src/report/charts.py` (`setup_korean_font`) | PNG 열어서 한글 확인 |
| 7-1 | **품질 지표 2개 이상** | `src/storage/db.py` (`pipeline_stats`) — DB 실측값, 하드코딩 없음 | 리포트 상단 지표 섹션 |
| 7-2 | **TOP N 집계** | `src/report/reporter.py` (`write_report`) | `report --top-n 10` |
| 7-3 | **콘솔 출력 + TXT/MD 파일** | 같은 함수 | 콘솔 출력 + `outputs/reports/report.*.md` |
| 8-1 | **CSV/JSONL/Excel 중 2개 이상** | `src/report/exporter.py` (`export_data`) | `export --formats csv,jsonl` → `outputs/` |
| 8-2 | **필터 옵션** `--status summarized` | `main.py` export 파서 | `python main.py export --help` |
| 9-1 | **설정 파일** (API키·소스URL·중복정책) | `config/config.example.json`, `src/utils/config.py` | 파일 내용 |
| 9-2 | **logging INFO/WARNING/ERROR** | `src/utils/logging_setup.py` (콘솔 + `logs/pipeline.log`) | `cat logs/pipeline.log` |
| 10 | **영구 저장소 SQLite** (메모리 전용 금지) | `src/storage/db.py` → `data/pipeline.db` | `sqlite3 data/pipeline.db ".schema"` |
| 11 | **모듈 4개 이상 분리** | `collectors` / `cleaners` / `ai` / `report` / `storage` / `utils` = **6개 패키지, 14개 모듈** | `find src -name '*.py'` |

## 3. 제약사항 준수

| 제약 | 준수 방법 |
|------|-----------|
| 웹 UI 없음, CLI만 | 진입점은 `main.py` 하나. 서버·프론트엔드 코드 없음 |
| API 키를 코드에 넣지 않음 | `.env` + `os.getenv`, `.gitignore` 에 `.env` 등록. `git log -p` 에 키 없음 |
| 크롤링 정책 준수·요청 제한 | `config.crawl.delay_sec`(요청 간 지연), `max_pages`, `max_articles_per_run`, `respect_robots_txt`, 명시적 User-Agent |
| Python 3.10+ | `from __future__ import annotations` + `X | None` 문법 사용 |

## 4. 보너스 과제

| 항목 | 상태 |
|------|------|
| 정기 실행 스케줄링 문서화 | ✅ `README.md` §6 (cron / 작업 스케줄러) |
| 데이터 조회 CLI (`list`, `show`) | 선택 구현 — `docs/roles/LEAD_REPORT.md` 참조 |
| 감성 분석 | 선택 구현 — `insights_json.sentiment` 로 확장 |

## 5. 팀 협업 근거

- 워크스트림별 담당 파일과 브랜치가 `README.md` §5 와 `docs/roles/` 3개 문서에 명시되어 있습니다.
- 팀 간 계약(테이블 스키마·함수 시그니처·경로)은 `docs/INTERFACE.md` 한 곳에서 관리합니다.
- 기여 내역은 `git log --oneline --graph` / `git shortlog -sn` 으로 확인할 수 있습니다.
