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

## 3. Python 함수 계약 (제안 시그니처)

팀원이 이 이름을 맞추면 `main.py` 연결이 쉬움.

### storage (`src/storage/db.py`)
- `init_db(db_path: str) -> None`
- `upsert_raw(conn, row: dict, policy: str) -> str`  # returns 'inserted'|'updated'|'skipped'
- `get_raw_for_clean(conn, source: str | None, limit: int | None) -> list[dict]`
- `upsert_clean(conn, row: dict) -> int`  # clean id
- `get_unsummarized(conn, limit: int | None) -> list[dict]`
- `upsert_summary(conn, row: dict) -> int`
- `insert_analysis(conn, row: dict) -> int`
- `fetch_report_frame(conn) ->` pandas-compatible rows / list[dict]

### collectors
- `BaseCollector.fetch(limit: int, **kwargs) -> list[dict]`  # raw row dicts
- `RSSCollector`, `CrawlCollector`

### cleaner
- `clean_article(raw_row: dict) -> dict`  # clean row dict without id

### ai
- `summarize_article(title: str, body: str, *, model: str) -> str`
- `analyze_batch(articles: list[dict], *, model: str) -> dict`

### report
- `make_charts(conn, out_dir: str) -> list[str]`  # png paths
- `write_report(conn, out_dir: str, top_n: int, fmt: str) -> str`
- `export_data(conn, out_dir: str, formats: list[str]) -> list[str]`

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
- `duplicate_policy` : `"skip"` | `"upsert"`
- `crawl.delay_sec` : number
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
