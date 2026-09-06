# INTERFACE.md — 역할 간 파일/DB 계약

> 이 문서는 **구현 계약서**에 가깝습니다. PLAN/ACTION_PLAN이 제안안인 것과 달리,  
> 컬럼·경로·status를 바꿀 때는 반드시 팀 공유 후 이 파일을 갱신하세요.

---

## 1. 경로 계약

| 용도 | 기본 경로 | 비고 |
|------|-----------|------|
| 설정 | `config/config.json` | `config.example.json` 복사 |
| 시크릿 | `.env` | gitignore |
| DB | `data/pipeline.db` | gitignore |
| raw 스냅샷(선택) | `data/raw/` | 파일 저장 시 UTF-8 |
| clean 스냅샷(선택) | `data/clean/` | |
| 차트 | `outputs/charts/*.png` | |
| 리포트 | `outputs/reports/*` | |
| 로그 | `logs/pipeline.log` | |
| export | `outputs/*.csv` 등 | |

상대 경로는 **저장소 루트** 기준. `main.py` 실행 cwd도 루트를 권장.

---

## 2. SQLite 테이블 계약

연결: `src/storage/db.py` → `get_connection()`, `init_db()`.

### 2.1 `news_raw` (작성: Collect/Clean / 스키마: 공유)

```sql
CREATE TABLE IF NOT EXISTS news_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  method TEXT NOT NULL,          -- 'rss' | 'crawl'
  guid TEXT,
  url TEXT NOT NULL,
  title TEXT,
  published_at TEXT,
  category TEXT,
  author TEXT,
  raw_html TEXT,
  raw_text TEXT,
  fetched_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'fetched',  -- fetched|error|skipped
  error_message TEXT,
  UNIQUE(url)
);
CREATE INDEX IF NOT EXISTS idx_news_raw_source ON news_raw(source);
CREATE INDEX IF NOT EXISTS idx_news_raw_fetched_at ON news_raw(fetched_at);
```

**status**
- `fetched`: 수집 성공
- `skipped`: 중복 정책으로 건너뜀(로그용 카운트; DB row를 안 남길 수도 있음 — skip 시 row 미작성 허용)
- `error`: 개별 URL 실패

### 2.2 `news_clean` (작성: Collect/Clean)

```sql
CREATE TABLE IF NOT EXISTS news_clean (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  raw_id INTEGER NOT NULL,
  source TEXT NOT NULL,
  url TEXT NOT NULL UNIQUE,
  title TEXT,
  published_at TEXT,
  category TEXT,
  author TEXT,
  body_text TEXT,
  word_count INTEGER DEFAULT 0,
  language TEXT DEFAULT 'ko',
  cleaned_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'clean',  -- clean|empty|error
  quality_flags TEXT,                   -- JSON string optional
  FOREIGN KEY(raw_id) REFERENCES news_raw(id)
);
```

### 2.3 `news_summary` (작성: Summarize/Analyze)

```sql
CREATE TABLE IF NOT EXISTS news_summary (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clean_id INTEGER NOT NULL UNIQUE,
  summary_text TEXT,
  model TEXT,
  prompt_version TEXT DEFAULT 'v1',
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ok',  -- ok|error
  error_message TEXT,
  FOREIGN KEY(clean_id) REFERENCES news_clean(id)
);
```

### 2.4 `news_analysis` (작성: Summarize/Analyze)

```sql
CREATE TABLE IF NOT EXISTS news_analysis (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT NOT NULL DEFAULT 'batch',
  batch_key TEXT NOT NULL,
  insights_json TEXT NOT NULL,
  model TEXT,
  created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ok',
  error_message TEXT
);
```

`insights_json` 최소 스키마(키는 선택적, **2개 이상 non-empty**):

```json
{
  "trends": ["string"],
  "keywords": [{"term": "string", "score": 0.0}],
  "similarities_differences": {"similar": ["string"], "different": ["string"]},
  "implications": ["string"],
  "top_articles": [{"url": "string", "title": "string", "reason": "string"}]
}
```

---

## 3. Python 함수 계약 (실제 시그니처)

> 아래는 **현재 코드에 구현되어 있는 그대로**입니다. 여기 적힌 이름·인자를 그대로 쓰면
> `main.py` 연결이 이미 되어 있어 추가 배선이 필요 없습니다.
> 바꾸려면 §6 변경 프로세스를 따르세요.

### storage (`src/storage/db.py`) — **구현 완료, 그대로 호출만 하면 됨**
- `get_connection(db_path: str) -> sqlite3.Connection`  # `with` 로 사용, row_factory=Row
- `init_db(db_path: str) -> None`
- `now_iso() -> str`  # 모든 타임스탬프 컬럼 형식: `YYYY-MM-DDTHH:MM:SSZ`
- `upsert_raw(conn, row: dict, policy: str = "skip") -> str`  # 'inserted'|'updated'|'skipped'
- `get_raw_for_clean(conn, source=None, limit=None, include_cleaned=False) -> list[dict]`
- `upsert_clean(conn, row: dict) -> int`  # clean id
- `get_unsummarized(conn, limit=None, clean_id=None) -> list[dict]`
- `get_clean_articles(conn, limit=None, since=None, category=None, with_summary=True) -> list[dict]`
- `upsert_summary(conn, row: dict) -> int`
- `insert_analysis(conn, row: dict) -> int`  # insights_json 에 dict 를 넘기면 자동 직렬화
- `get_latest_analysis(conn) -> dict | None`  # `result["insights"]` 에 파싱된 dict
- `count_rows(conn, table: str, where: str = "", params=()) -> int`
- `category_counts(conn) -> list[tuple[str, int]]`  # 차트 1번용
- `daily_counts(conn) -> list[tuple[str, int]]`  # 차트 2번용
- `pipeline_stats(conn) -> dict`  # 품질 지표 원천 수치

### collectors (`src/collectors/`) — **구현 완료**
- `BaseCollector(config: dict, source: str = "aitimes")`
  - `.timeout -> tuple[float, float]`  # (connect, read), config.timeouts 에서
  - `.build_session() -> requests.Session`  # User-Agent 적용
- `RSSCollector.fetch(limit: int = 20, **kwargs) -> list[dict]`
- `CrawlCollector.fetch(limit: int = 20, **kwargs) -> list[dict]`  # kwargs: `max_pages`

### cleaner (`src/cleaners/cleaner.py`) — **구현 완료**
- `clean_article(raw_row: dict) -> dict`  # 순수 함수, id 없는 clean row
- `clean_articles(db_path, source=None, limit=None, force=False, config=None) -> int`

### ai (`src/ai/`) — **미구현 (Summarize/Analyze 담당)**
- `summarize_article(title: str, body: str, *, model: str | None = None) -> str`
- `run_summarize(db_path, limit=20, clean_id=None, unsummarized=True, config=None) -> int`
- `analyze_batch(articles: list[dict], *, model: str | None = None) -> dict`
- `run_analyze(db_path, limit=50, since=None, category=None, config=None) -> bool`

### report (`src/report/`) — **미구현 (Lead/Report 담당)**
- `setup_korean_font() -> str | None`
- `make_charts(db_path: str, out_dir: str, config=None) -> list[str]`  # png 경로들
- `write_report(db_path: str, out_dir: str, top_n=10, fmt="md", config=None) -> str`
- `export_data(db_path: str, out_dir: str, formats: list[str], status=None, config=None) -> list[str]`

> ⚠️ report/ai 함수는 **첫 인자가 `conn` 이 아니라 `db_path`(str)** 입니다.
> 내부에서 `with db.get_connection(db_path) as conn:` 으로 여세요.

---

## 4. CLI ↔ 모듈 매핑

| 서브커맨드 | 모듈 | 담당 |
|------------|------|------|
| fetch | collectors + storage | Collect/Clean |
| clean | cleaners + storage | Collect/Clean |
| summarize | ai.summarizer + storage | Summarize/Analyze |
| analyze | ai.analyzer + storage | Summarize/Analyze |
| report | report.reporter + charts | Lead/Report |
| export | report.exporter | Lead/Report |

---

## 5. 설정 키 계약 (`config.json`)

필수에 가까운 키:
- `sources.aitimes.rss_urls` : string[]
- `sources.aitimes.list_url_templates` : string[]
- `duplicate_policy` : `"skip"` | `"upsert"` — **기본값 `"upsert"` (변경 금지)**
  - RSS 와 크롤링이 같은 기사 URL 을 수집합니다. `"skip"` 이면 나중에 도는 크롤링 결과가
    전부 버려져 `category` 가 전부 NULL 이 되고 본문이 리드 문단만 남습니다
    (→ 필수 차트 "카테고리별 뉴스 수" 와 `analyze --category` 가 깨집니다).
  - 그래서 **실행 순서도 계약입니다: `fetch --method rss` → `fetch --method crawl` → `clean`**
    (순서가 반대면 RSS 가 크롤링 본문·카테고리를 NULL 로 덮어씁니다.)
- `crawl.delay_sec` : number
- `crawl.max_pages` : number — **현재 `1` (의도된 값)**
  - aitimes.com 의 `articleList.html` 은 `?page=N` 파라미터를 무시하고 항상 1페이지(약 20건)를
    돌려줍니다(실측: page=1/2/3 결과 idxno 완전 동일). 2 이상으로 올리면 **같은 페이지를
    중복 요청**할 뿐이라 크롤링 윤리(과도한 요청 금지)에 어긋납니다.
  - 수집량은 RSS(`rss_urls`) 쪽을 늘려서 확보하세요.
- `paths.db` : string
- `report.top_n` : number
- `logging.level` : `"INFO"` 등

---

## 6. 변경 프로세스

1. INTERFACE 수정 PR/커밋  
2. `init_db` 마이그레이션(간단 과제에서는 DROP 재생성 허용 — **단, 팀원에게 재fetch 공지**)  
3. ACTION_PLAN 머지 포인트와 충돌 시 INTERFACE 우선  

---

*계약 위반이 생기면 merge 전에 Lead/Report·해당 담당자와 짧은 동기화.*
