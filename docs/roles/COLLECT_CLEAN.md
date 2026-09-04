# 역할: Collect/Clean — 수집 · 정제

담당 서브커맨드: **`fetch`, `clean`**

## 내가 건드릴 파일 (이 4개만)

| 파일 | 할 일 |
|------|-------|
| `src/collectors/base.py` | 공통 HTTP 세션·타임아웃·User-Agent (필요 시) |
| `src/collectors/rss.py` | `RSSCollector.fetch()` 구현 |
| `src/collectors/crawl.py` | `CrawlCollector.fetch()` 구현 |
| `src/cleaners/cleaner.py` | `clean_article()`, `clean_articles()` 구현 |

**건드리지 말 것:** `src/ai/*`, `src/report/*`, `main.py`, `src/storage/db.py`
(DB 스키마 변경이 필요하면 `docs/INTERFACE.md` 를 고치고 Lead/Report 에게 알리세요.)

## 시작하기

```bash
git checkout -b feature/collect-fetch-rss
python main.py initdb
python main.py fetch --method rss --limit 3   # 지금은 "미구현" 에러가 뜹니다 — 여기서 시작
```

## 작업 1 — `fetch` (RSS)

`src/collectors/rss.py` 의 `RSSCollector.fetch()` 가 **dict 리스트**를 반환하면 끝입니다.
저장은 `main.py` 가 `db.upsert_raw()` 로 알아서 합니다.

반환할 dict 키 (`news_raw` 컬럼과 동일):
```python
{
  "source": "aitimes", "method": "rss",
  "guid": "...", "url": "https://www.aitimes.com/news/articleView.html?idxno=...",
  "title": "...", "published_at": "2026-09-04T09:00:00Z",  # ISO8601 권장
  "category": "...", "author": "...",
  "raw_html": None, "raw_text": "<피드 description>",
  "fetched_at": "2026-09-04T09:10:00Z",   # UTC ISO8601
  "status": "fetched", "error_message": None,
}
```

구현 힌트:
- RSS URL 은 `self.source_cfg["rss_urls"]` 에 이미 들어 있습니다.
- 파싱은 `xml.etree.ElementTree` 또는 `BeautifulSoup(xml_text, "xml")` 둘 다 가능.
- 타임아웃: `config["timeouts"]["http_connect_sec"]`, `http_read_sec` 를 `requests.get(..., timeout=(c, r))` 에 전달.
- 실패한 URL 은 예외를 던지지 말고 **WARNING 로그 + 건너뛰기**. 전체 수집이 중단되면 안 됩니다.
- `limit` 건까지만 반환.

**완료 기준(DoD)**
- [ ] `python main.py fetch --method rss --limit 20` 이 "신규 N건 / 중복 스킵 M건" 로그로 끝난다
- [ ] 같은 명령을 두 번 실행하면 두 번째는 전부 "중복 스킵" 이다
- [ ] `sqlite3 data/pipeline.db "SELECT url,title,method FROM news_raw LIMIT 5;"` 에 데이터가 보인다

## 작업 2 — `fetch` (크롤링)

`src/collectors/crawl.py` 의 `CrawlCollector.fetch()`.

1. `self.source_cfg["list_url_templates"]` 의 `{page}` 를 1..max_pages 로 채워 기사 링크 수집
2. 각 상세 페이지에서 제목·본문·날짜·카테고리 파싱 (`raw_html` 에 본문 HTML 저장)
3. **요청 사이에 `config["crawl"]["delay_sec"]` 만큼 `time.sleep()`** ← 크롤링 윤리 요구사항, 반드시 넣을 것
4. `config["crawl"]["max_pages"]`, `max_articles_per_run` 상한 준수
5. User-Agent 헤더는 `self.source_cfg["user_agent"]` 사용

**완료 기준(DoD)**
- [ ] `python main.py fetch --method crawl --limit 10 --max-pages 2` 성공
- [ ] `news_raw.method='crawl'` 행이 생긴다
- [ ] 로그에서 요청 간 지연이 실제로 걸린 것이 보인다 (타임스탬프 간격)

## 작업 3 — `clean`

`src/cleaners/cleaner.py`.

- `clean_article(raw_row) -> dict` : 한 건 변환 (순수 함수, 테스트하기 쉬움)
  - `raw_html` → `BeautifulSoup(...).get_text(" ")` 로 태그 제거
  - 연속 공백·개행 정규화 (`re.sub(r"\s+", " ", text).strip()`)
  - 날짜를 ISO8601 로 통일
  - `word_count = len(body_text.split())`
  - 본문이 비었으면 `status="empty"`, 필수 필드(url/title) 없으면 `status="error"`
- `clean_articles(...)` : DB 루프. **이미 만들어진 헬퍼를 그대로 쓰세요.**

```python
from src.storage import db

def clean_articles(db_path, source=None, limit=None, force=False, config=None):
    processed = 0
    with db.get_connection(db_path) as conn:
        rows = db.get_raw_for_clean(conn, source=source, limit=limit, include_cleaned=force)
        for raw in rows:
            cleaned = clean_article(raw)
            cleaned["raw_id"] = raw["id"]
            db.upsert_clean(conn, cleaned)
            processed += 1
    return processed
```

**완료 기준(DoD)**
- [ ] `python main.py clean --limit 30` 이 "정제 완료: N건" 으로 끝난다
- [ ] `news_raw` 는 그대로 남고 `news_clean` 에 새 행이 생긴다 (raw/clean 분리)
- [ ] 본문 빈 기사는 `status='empty'` 로 남는다

## 막혔을 때

- 스키마·함수 시그니처: `docs/INTERFACE.md`
- 사용할 DB 헬퍼 목록: `src/storage/db.py` 상단 함수들
- AI 도구에 붙여넣을 프롬프트: `docs/SHARED_PROMPT.md` §A + §B-1
