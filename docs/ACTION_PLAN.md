# ACTION_PLAN.md — 단계별 진행 체크리스트

> 날짜가 아니라 **단계(Phase)** 기준입니다. 각자 속도에 맞춰 진행하되,
> **머지 포인트**(Phase 끝의 굵은 줄)만 팀이 함께 맞춥니다.
> 앞 Phase 가 안 끝나도 뒤 작업을 시작할 수 있게, 각 역할이 **독립적으로 개발 가능한 방법**을 함께 적어 뒀습니다.

## 한눈에 보기

| Phase | Collect/Clean | Summarize/Analyze | Lead/Report | 머지 포인트 |
|---|---|---|---|---|
| **0. 셋업** | clone·venv·`initdb` | clone·venv·`.env` 키 확인 | ✅ 뼈대 완료 | 전원 `python main.py --help` 성공 |
| **1. 수집** | `fetch --method rss` | AI 클라이언트 호출 성공 | 한글 폰트 탐지 | `news_raw` 에 실데이터 |
| **2. 정제·요약** | `clean` | `summarize` | 차트 2종 PNG | `news_clean` + `news_summary` 각 1건+ |
| **3. 크롤링·분석** | `fetch --method crawl`, 중복 정책 | `analyze` (JSON 2필드+) | `report` + `export` | `news_analysis` 1건 |
| **4. 통합** | 버그픽스 | 품질 다듬기 | E2E·머지 | **E2E 그린** |
| **5. 제출** | — | — | 최종 점검·제출 | 제출 체크리스트 완료 |

---

## Phase 0 — 셋업 (전원, 10분)

- [ ] `git clone` → `python3 -m venv .venv && source .venv/bin/activate`
- [ ] `pip install -r requirements.txt`
- [ ] `cp config/config.example.json config/config.json`
- [ ] `cp .env.example .env` (Summarize/Analyze 는 `AI_API_KEY` 필수, 나머지는 없어도 됨)
- [ ] `python main.py --help` → 서브커맨드 6종 확인
- [ ] `python main.py initdb` → `data/pipeline.db` 생성 확인
- [ ] 본인 역할 문서 1개 정독: `docs/roles/`
- [ ] `git checkout -b feature/<본인-워크스트림>-<작업>`

**머지 포인트:** 전원이 `--help` 와 `initdb` 성공. 여기서 막히면 즉시 팀 채널에 공유.

---

## Phase 1 — 수집 시작

### Collect/Clean
- [ ] `src/collectors/rss.py` → `RSSCollector.fetch()` 구현
- [ ] 타임아웃·개별 실패 스킵 처리
- [ ] `python main.py fetch --method rss --limit 20` 성공
- [ ] 재실행 시 중복 스킵 로그 확인

### Summarize/Analyze — *수집을 기다리지 말 것*
- [ ] `.env` 로드 및 API 호출 1회 성공 (짧은 텍스트로 테스트)
- [ ] `summarize_article()` 시그니처 확정
- [ ] 데이터가 없으면 `news_clean` 에 테스트 행을 직접 INSERT 해서 개발

```sql
INSERT INTO news_clean (raw_id, source, url, title, body_text, word_count, cleaned_at, status)
VALUES (0, 'aitimes', 'http://test/1', '테스트 기사', '본문 텍스트...', 3, '2026-01-01T00:00:00Z', 'clean');
```

### Lead/Report
- [ ] `setup_korean_font()` 구현 — 본인 OS 에서 한글 폰트 탐지
- [ ] `outputs/charts`, `outputs/reports` 경로 생성 확인

**머지 포인트:** `news_raw` 에 실제 기사 행 존재 → 이후 전원이 같은 DB 로 개발.

---

## Phase 2 — 정제 · 요약

### Collect/Clean
- [ ] `clean_article()` — HTML 제거, 공백 정규화, `word_count`, 날짜 ISO8601 통일
- [ ] `clean_articles()` — `db.get_raw_for_clean` / `db.upsert_clean` 연결
- [ ] 빈 본문 → `status='empty'`
- [ ] `python main.py clean --limit 30` 성공

### Summarize/Analyze
- [ ] `run_summarize()` — 미요약 건만 처리, 건별 진행 로그
- [ ] 실패 시 `status='error'` + ERROR 로그 (예외 전파 금지)
- [ ] `python main.py summarize --unsummarized --limit 10` 성공

### Lead/Report
- [ ] `make_charts()` — 카테고리 막대 + 일자별 선그래프 PNG 2개
- [ ] 데이터 0건일 때 WARNING 후 빈 리스트 반환

**머지 포인트:** `news_clean` 과 `news_summary` 에 각각 1건 이상.

---

## Phase 3 — 크롤링 · 분석 · 리포트

### Collect/Clean
- [ ] `CrawlCollector.fetch()` — list 페이지 → detail 파싱
- [ ] `delay_sec` sleep, `max_pages` 준수, User-Agent 설정
- [ ] `duplicate_policy` skip/upsert 양쪽 동작 확인
- [ ] `python main.py fetch --method crawl --limit 10` 성공

### Summarize/Analyze
- [ ] `analyze_batch()` — 배치 입력 → JSON 파싱
- [ ] `insights_json` non-empty 키 **2개 이상**
- [ ] `python main.py analyze --limit 50` 성공

### Lead/Report
- [ ] `write_report()` — 품질지표 2+, TOP N, AI 인사이트, 콘솔+파일
- [ ] `export_data()` — CSV + JSONL (+ 가능하면 XLSX)

**머지 포인트:** `news_analysis` 에 `status='ok'` 1건, 차트 PNG 2개, 리포트 파일 1개.

---

## Phase 4 — 통합 E2E (전원)

`main` 브랜치에서 한 번에:

```bash
rm -f data/pipeline.db          # 깨끗한 상태에서 재현되는지 확인
python main.py initdb
python main.py fetch --source aitimes --method rss --limit 20
python main.py fetch --source aitimes --method crawl --limit 10
python main.py clean --limit 30
python main.py summarize --unsummarized --limit 20
python main.py analyze --limit 50
python main.py report --top-n 10 --format md
python main.py export --formats csv,jsonl
```

- [ ] 위 9줄이 **에러 없이** 끝난다
- [ ] `logs/pipeline.log` 에 ERROR 가 없다 (있으면 티켓화)
- [ ] README 의 실행 예시가 실제 옵션과 일치한다
- [ ] `docs/EVALUATION.md` 대조표의 "구현 위치" 가 실제와 맞다

**머지 포인트: E2E 그린.** 이 시점 이후 breaking 스키마 변경 금지.

---

## Phase 5 — 제출 (Lead/Report 주도)

- [ ] `git status` — `.env`, `*.db`, 산출물이 커밋되지 않았는지
- [ ] `git log -p | grep -i "api.key"` — 키 유출 없음
- [ ] `git shortlog -sn` — 팀원 3명 커밋이 모두 보이는지
- [ ] 클린 venv 에서 `pip install -r requirements.txt` 로 설치 재현
- [ ] `docs/EVALUATION.md` 검증 명령 9개 전부 통과
- [ ] 저장소 문서·코드에 실명·개인정보 0건 (`git grep` 확인)
- [ ] 제출 양식에 저장소 URL 기입

---

## 최소 성공 경로 (시간이 모자랄 때 이 순서로)

1. RSS `fetch` → `clean` → SQLite 적재
2. `summarize` 1건 + `analyze` 필드 2개
3. 차트 PNG 2개 + `report` MD + `export` CSV/JSONL
4. 크롤링은 "동작" 또는 "제한사항 문서화" 중 하나

Selenium · XLSX · upsert · 보너스(list/show, 감성분석)는 여유가 생기면 추가합니다.

---

## 커뮤니케이션 규칙

- 스키마·CLI 옵션 변경 → `docs/INTERFACE.md` 수정 + 팀 채널 한 줄 공지
- 막혔을 때 → **에러 로그 10줄 + 재현 명령**을 붙여서 공유 (스크린샷보다 텍스트)
- 머지는 Lead/Report 가 담당, 급한 수정은 `hotfix/` 브랜치
