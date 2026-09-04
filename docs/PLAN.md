# PLAN.md — AI타임스 뉴스 파이프라인 설계 제안안

> **문서 성격: 제안안(draft proposal)**  
> 이 문서는 팀 합의를 위한 **초안**입니다. 사용 모델, 세부 구현, 작업 시간·일정은 각 팀원(Collect/Clean·Summarize/Analyze·Lead/Report)이 **자율적으로** 결정합니다.  
> 다만 **인터페이스·스키마·CLI 계약·Definition of Done(DoD)** 은 가능한 한 구체화해 두었으므로, 변경 시 `docs/INTERFACE.md`와 함께 팀 채널에 공유해 주세요.

- 작성일: 2026-09-04  
- 과제: A2-2 / Project B  
- 소스: https://www.aitimes.com/  
- 마감: 2026-09-09 (수)

---

## 1. Goals (목표)

1. AI타임스 기사를 **수집(fetch) → 정제(clean) → AI 요약(summarize) → 인사이트 분석(analyze) → 리포트/차트(report) → 내보내기(export)** 하는 재현 가능한 CLI 파이프라인을 만든다.
2. **RSS(또는 피드/API성 엔드포인트)와 HTML 크롤링을 모두** 지원한다.
3. raw와 clean을 분리하고, URL/GUID 기준 **중복 skip 또는 upsert**를 지원한다.
4. AI로 요약하고, 트렌드·키워드·유사/차이·시사점 중 **2가지 이상**의 인사이트를 산출한다.
5. matplotlib로 **카테고리 건수**, **일별 추이** 등 차트 2종 이상을 PNG로 저장한다(한글 폰트).
6. 품질 지표 2개 이상 + TOP N + AI 인사이트를 콘솔 및 TXT/MD 리포트로 출력한다.
7. CSV / JSONL / Excel 중 **최소 2형식**으로 export한다.
8. 설정은 `config.json` + `.env`, 로그는 INFO/WARNING/ERROR, 영속 저장은 **SQLite**를 기본으로 한다.
9. 단일 파일이 아닌 **모듈 4개 이상** 구조, Python 3.10+, 웹 UI 없음, API 키는 코드에 넣지 않는다.

## 2. Scope / Non-goals

### In scope
- CLI 서브커맨드 6종: `fetch`, `clean`, `summarize`, `analyze`, `report`, `export`
- aitimes.com 대상 RSS + list/detail 크롤링
- SQLite 테이블: `news_raw`, `news_clean`, `news_summary`, `news_analysis` (이름 변경 시 INTERFACE 동기화)
- 팀 역할 분담에 맞춘 모듈 소유권

### Non-goals (이번 과제에서 하지 않음)
- 웹 UI / 대시보드 서버
- 실시간 스트리밍·스케줄러 데몬( cron 등은 선택)
- 다중 언론사 통합 검색 엔진
- 프로덕션급 배포·인증·요금 관리
- Selenium 필수화(필요 시 옵션; 기본은 requests + BeautifulSoup)

---

## 3. Pipeline Architecture

```
[aitimes RSS] ----\
                   +--> fetch --> news_raw --+--> clean --> news_clean --+--> summarize --> news_summary
[aitimes crawl] --/                          |                           |
                                             |                           +--> analyze --> news_analysis
                                             |                                      |
                                             +--------------------------------------+--> report / charts / export
```

데이터 흐름 원칙:
1. **fetch**는 원문 메타+본문(가능한 범위)을 `news_raw`에만 기록.
2. **clean**은 raw를 읽어 정규화·HTML 제거·필드 표준화 후 `news_clean`에 기록. raw를 덮어쓰지 않음.
3. **summarize / analyze**는 clean(또는 summary)을 입력으로 사용. API 키는 `.env`.
4. **report / export**는 clean+summary+analysis를 조인/조회하여 산출물 생성.

---

## 4. Data Schema (제안)

### 4.1 `news_raw`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 자동증가 |
| source | TEXT | 예: `aitimes` |
| method | TEXT | `rss` \| `crawl` |
| guid | TEXT | RSS guid 또는 안정적 식별자(없으면 url 해시) |
| url | TEXT NOT NULL | 기사 URL (고유키 후보) |
| title | TEXT | 원제목 |
| published_at | TEXT | ISO8601 또는 원문 문자열 |
| category | TEXT | 섹션/카테고리(있으면) |
| author | TEXT | 기자/작성자(있으면) |
| raw_html | TEXT | 상세 페이지 HTML 스니펫/전체(용량 주의) |
| raw_text | TEXT | 피드 description 등 |
| fetched_at | TEXT | 수집 시각 UTC ISO8601 |
| status | TEXT | `fetched` \| `error` \| `skipped` |
| error_message | TEXT | 실패 시 |
| UNIQUE(url) 권장, UNIQUE(guid) 선택 |

### 4.2 `news_clean`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| raw_id | INTEGER FK | news_raw.id |
| source | TEXT | |
| url | TEXT NOT NULL UNIQUE | |
| title | TEXT | 정규화 제목 |
| published_at | TEXT | 파싱된 ISO8601(가능 시) |
| category | TEXT | 표준화 카테고리 |
| author | TEXT | |
| body_text | TEXT | HTML 제거·공백 정규화 본문 |
| word_count | INTEGER | 대략 토큰/단어 수 |
| language | TEXT | 기본 `ko` |
| cleaned_at | TEXT | |
| status | TEXT | `clean` \| `empty` \| `error` |
| quality_flags | TEXT | JSON 문자열(짧은 본문 등) |

### 4.3 `news_summary`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| clean_id | INTEGER FK UNIQUE | 기사당 1요약(재실행 시 upsert) |
| summary_text | TEXT | 한국어 요약 |
| model | TEXT | 사용 모델명 |
| prompt_version | TEXT | 예: `v1` |
| created_at | TEXT | |
| status | TEXT | `ok` \| `error` |
| error_message | TEXT | |

### 4.4 `news_analysis`
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | |
| scope | TEXT | `batch` \| `single` 등 |
| batch_key | TEXT | 실행 단위 키(날짜+해시) |
| insights_json | TEXT | 구조화 인사이트 JSON |
| model | TEXT | |
| created_at | TEXT | |
| status | TEXT | `ok` \| `error` |

`insights_json` 예시 키(제안, 최소 2개 채우면 DoD 충족):
```json
{
  "trends": ["..."],
  "keywords": [{"term": "생성형 AI", "score": 0.9}],
  "similarities_differences": {"similar": ["..."], "different": ["..."]},
  "implications": ["..."],
  "top_articles": [{"url": "...", "title": "...", "reason": "..."}]
}
```

상세 계약은 `docs/INTERFACE.md` 참고.

---

## 5. Module Ownership Map (제안)

| 모듈 경로 | 소유(제안) | 책임 |
|-----------|------------|------|
| `src/collectors/*` | Collect/Clean | RSS/crawl 수집, rate limit |
| `src/cleaners/cleaner.py` | Collect/Clean | raw→clean 변환, 중복 정책 적용 보조 |
| `src/ai/summarizer.py`, `analyzer.py` | Summarize/Analyze | AI 클라이언트, 요약·분석 JSON |
| `src/report/charts.py`, `reporter.py`, `exporter.py` | Lead/Report | 차트·리포트·export |
| `src/storage/db.py` | Lead/Report(주도) / 전원 사용 | 스키마·upsert/skip 헬퍼 |
| `src/utils/config.py`, `logging_setup.py` | Lead/Report(초기) / 공유 | 설정·로깅 |
| `main.py` | Lead/Report(스켈레톤) / 전원 확장 | argparse 디스패치 |

---

## 6. CLI Contracts (제안 옵션)

공통:
- `--config PATH` (기본: `config/config.json`)
- `-v / --verbose` → DEBUG에 가깝게(선택), 기본 로그 INFO

### `fetch`
```
python main.py fetch --source aitimes --method {rss|crawl} [--limit N] [--max-pages N] [--dry-run]
```
- DoD: N건 이하로 `news_raw`에 insert; 중복 URL은 skip 또는 upsert(`config.duplicate_policy`); 로그에 신규/스킵/실패 건수.

### `clean`
```
python main.py clean [--source aitimes] [--limit N] [--force]
```
- DoD: status=`fetched`인 raw를 처리해 `news_clean` 작성; 빈 본문은 `empty`로 표시.

### `summarize`
```
python main.py summarize [--unsummarized] [--limit N] [--clean-id ID]
```
- DoD: clean 중 미요약 건을 요약해 `news_summary`에 저장; 키 없으면 명확한 ERROR 로그 후 non-zero 또는 graceful skip(팀 합의).

### `analyze`
```
python main.py analyze [--limit N] [--since YYYY-MM-DD]
```
- DoD: 인사이트 필드 2개 이상 채운 JSON을 `news_analysis`에 저장.

### `report`
```
python main.py report [--top-n N] [--format {txt|md|both}] [--out DIR]
```
- DoD: 품질 지표 2+ , TOP N, AI 인사이트 포함; 콘솔 출력 + 파일; 차트 PNG 2+ 생성(또는 charts 서브호출).

### `export`
```
python main.py export [--formats csv,jsonl,xlsx] [--out DIR]
```
- DoD: 지정 형식 중 최소 2개 파일 생성.

---

## 7. Tech Choices (제안)

| 영역 | 선택 | 이유 |
|------|------|------|
| 언어 | Python 3.10+ | 과제 요건 |
| HTTP | `requests` | 단순·충분 |
| HTML | `beautifulsoup4` + `lxml` | 리스트/상세 파싱 |
| Selenium | 선택(비기본) | JS 필수 구간만 |
| DB | SQLite (`sqlite3`) | 파일 하나, 설치 부담 없음 |
| AI | OpenAI-compatible HTTP (`openai` SDK 또는 requests) | `AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL` env |
| 표/엑셀 | `pandas` + `openpyxl` | CSV/XLSX |
| 차트 | `matplotlib` | PNG, 한글 폰트 설정 필요 |
| 설정 | `config.json` + `python-dotenv` | 비밀정보 분리 |

한글 폰트(제안): Linux CI/박스에서는 `NanumGothic` / `Noto Sans CJK KR` 등 존재 시 사용, 없으면 경고 로그 + 기본 폰트 폴백.

---

## 8. aitimes.com Collection Strategy (제안)

### 8.1 RSS
- 설정 예시 URL: `https://www.aitimes.com/rss/allArticle.xml`, `clickTop.xml` 등  
- **실제로 404/차단이면** crawl로 폴백하고 PLAN/로그에 기록.
- 파싱: `title`, `link`, `guid`, `pubDate`, `description`, category(있으면).

### 8.2 Crawl
1. 리스트 페이지: `articleList.html?page={page}` 형태(설정 `list_url_templates`)에서 기사 링크 수집.
2. 상세 페이지: 제목·본문·날짜·카테고리 셀렉터는 구현 시 HTML 구조에 맞게 확정(셀렉터는 코드 상수 또는 config).
3. **rate limit:** `crawl.delay_sec` (예: 1.5초) sleep; `max_pages`, `max_articles_per_run` 준수.
4. User-Agent를 명시하고, 가능하면 robots.txt를 확인(`respect_robots_txt`).
5. 실패 시 해당 URL `status=error` + `error_message`, 전체 중단은 가급적 피함.

### 8.3 중복
- 키: `url` 필수, `guid` 있으면 보조.
- `duplicate_policy`: `skip`(기본) | `upsert`(제목/본문/fetched_at 갱신).

---

## 9. Quality Metrics Definitions (제안 — 가짜 수치 금지)

리포트에 **실제 DB에서 계산한** 지표만 넣는다. 예시 정의:

1. **수집 성공률**  
   `success_rate = count(news_raw.status='fetched') / count(news_raw)`  
2. **정제 완료율**  
   `clean_rate = count(distinct news_clean.raw_id) / count(news_raw.status='fetched')`  
3. **요약 커버리지**  
   `summary_coverage = count(news_summary.status='ok') / count(news_clean.status='clean')`  
4. **평균 본문 길이**  
   `avg_word_count = avg(news_clean.word_count) where status='clean'`  
5. **일별 수집 건수 표준편차/최근 N일 추이** (차트와 함께 서술)

과제 DoD: 위 중 **2개 이상**을 리포트에 수치와 함께 명시.

TOP N: 예) 최신 N건, 또는 키워드 점수 상위 N건(분석 JSON의 `top_articles`와 정합).

---

## 10. Risks & Mitigation

| 위험 | 영향 | 완화 |
|------|------|------|
| RSS URL 변경/차단 | fetch 실패 | crawl 폴백, URL을 config로 분리 |
| HTML 구조 변경 | 파서 깨짐 | 셀렉터 한곳 집중, 샘플 HTML fixture 보관 |
| 과도한 요청 | IP 차단· eth 문제 | delay, limit, max_pages |
| AI API 키/쿼터 | summarize/analyze 불가 | `.env` 분리, dry-run·샘플 요약 경로(팀 합의), 에러 로깅 |
| 한글 폰트 미설치 | 차트 깨짐 | 폰트 탐지 로그, 설치 안내 README |
| 스키마 불일치로 merge 충돌 | 통합 지연 | INTERFACE.md 단일 진실원, Lead/Report이 DB 마이그레이션 조율 |
| 일정 압박(9/9) | 미완성 제출 | 9/8 E2E, 9/9 버퍼; 최소 경로(RSS→clean→요약1건→차트2→export2) 우선 |

---

## 11. Definition of Done (팀 공통 제안)

- [ ] 6개 서브커맨드가 `python main.py <cmd> --help`로 동작
- [ ] RSS와 crawl 각각 최소 1회 성공 로그/데이터(또는 한쪽 불가 시 문서화+다른쪽 강화)
- [ ] SQLite에 raw/clean 분리 적재, 중복 정책 동작
- [ ] AI 요약 1건 이상 + 인사이트 2종 이상
- [ ] 차트 PNG 2종+, 리포트 MD/TXT, export 2형식+
- [ ] API 키 코드/커밋 없음, README로 실행 가능
- [ ] 팀원별 커밋 이력 확인 가능

---

*이 제안안은 2026-09-04 기준입니다. 구현 중 변경은 PR/채팅으로 공유하고 INTERFACE를 갱신합니다.*
