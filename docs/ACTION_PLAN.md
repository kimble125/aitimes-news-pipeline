# ACTION_PLAN.md — 일정·체크리스트 제안안

> **문서 성격: 제안안(draft proposal)**  
> 날짜별 할 일과 담당은 **참고용 제안**입니다. 각 팀원은 본인 모델·학습 속도·가용 시간에 맞춰 **자율적으로** 일정을 조정하세요.  
> 단, **머지 포인트(인터페이스 동결·E2E·제출)** 와 DoD는 팀 전체가 맞춰야 합니다.

- 오늘: 2026-09-04 (금) — 기획·repo 세팅
- 마감: 2026-09-09 (수)

---

## 한눈에 보는 제안 일정

| 날짜 | Collect/Clean | Summarize/Analyze | Lead/Report | 머지 포인트 |
|------|--------|--------|--------|-------------|
| **9/4 (금)** | 문서·INTERFACE 리뷰 | 문서·SHARED_PROMPT 리뷰 | **repo+docs+스켈레톤 완료** | main에 초기 구조 push |
| **9/5 (토)** | `fetch` RSS+raw 스키마 | AI 클라이언트 스텁 | storage+CLI 동기화 | `news_raw` 스키마 합의 |
| **9/6 (일)** | `clean` + 샘플 raw→clean | `summarize` 샘플 동작 | 차트 폰트/경로 준비 | clean 샘플 N건 존재 |
| **9/7 (월)** | crawl 보완·중복 정책 | `analyze` JSON 2+필드 | charts 2종 PNG | analysis 1회 성공 |
| **9/8 (화)** | fetch/clean 버그픽스 | 요약·분석 품질 다듬기 | report+export 통합 E2E | **E2E 그린** |
| **9/9 (수)** | 버퍼·이슈 대응 | 버퍼·이슈 대응 | 최종 merge·README·**제출** | 제출 체크리스트 |

---

## Day 0 — 2026-09-04 (금) 기획일

### Lead/Report (제안)
- [x] GitHub repo 디렉터리·문서·스켈레톤 작성 (`README`, `docs/*`, `main.py`, `src/*` stub)
- [ ] remote push 및 팀원 초대/권한 확인
- [ ] `config/config.example.json` → 팀원에게 `config.json` 복사 안내
- [ ] 슬랙/채팅에 **제안안**임을 명시하고 INTERFACE 리뷰 요청

### Collect/Clean / Summarize/Analyze (제안)
- [ ] PLAN·INTERFACE·SHARED_PROMPT 읽고 질문/변경 요청
- [ ] 로컬 clone, venv, `pip install -r requirements.txt`
- [ ] `.env` 준비(Summarize/Analyze: API 키; Collect/Clean: 없어도 fetch/clean 가능)

---

## Day 1 — 2026-09-05 (토)

### Collect/Clean — fetch + raw
**목표(제안):** `fetch --source aitimes --method rss --limit N` 가 `news_raw`에 기록.

체크리스트:
- [ ] `src/storage/db.py`의 `news_raw` 스키마가 INTERFACE와 일치하는지 확인(불일치 시 호연과 합의)
- [ ] `src/collectors/rss.py`: RSS 파싱 → dict 리스트
- [ ] `src/collectors/crawl.py` 스텁 또는 링크 수집만 선행
- [ ] `main.py fetch` 연결: `--method rss|crawl`, `--limit`, `--max-pages`
- [ ] 중복: 동일 `url`이면 skip(기본) 로그
- [ ] DoD: `limit=10`으로 실행 시 DB에 ≥1건(네트워크 가능 시) 또는 실패 원인 로그

브랜치 예: `feature/jj-fetch-rss`

### Summarize/Analyze — AI 클라이언트 스텁
**목표(제안):** env 기반 클라이언트 + `summarize`가 “키 없으면 명확히 실패/스킵”.

체크리스트:
- [ ] `.env` / `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL` 로드 확인
- [ ] `src/ai/summarizer.py`: API 호출 함수 시그니처 확정(입력: title+body, 출력: summary_text)
- [ ] `news_summary` 테이블 insert/upsert 경로 스케치
- [ ] 프롬프트 v1을 SHARED_PROMPT 역할 추가분과 맞추기
- [ ] DoD: `python main.py summarize --help` 및 dry 경로 로그

브랜치 예: `feature/psb-ai-stub`

### Lead/Report — storage + CLI 동기화
- [ ] `init_db()`로 4테이블 생성 스크립트 안정화
- [ ] stub → 실제 dispatch에 팀원 PR 반영
- [ ] 로그 포맷 통일 (`logging_setup`)
- [ ] Collect/Clean raw 스키마 PR merge

**머지 포인트:** `news_raw` 컬럼 동결(이후 변경은 INTERFACE 개정).

---

## Day 2 — 2026-09-06 (일)

### Collect/Clean — clean
- [ ] `src/cleaners/cleaner.py`: HTML→text, 공백 정규화, `word_count`
- [ ] `python main.py clean --source aitimes --limit N`
- [ ] 빈 본문 → `status=empty`
- [ ] DoD: raw 샘플이 `news_clean`에 대응 행 생성

### Summarize/Analyze — summarize on sample
- [ ] `--unsummarized`로 미요약 clean만 처리
- [ ] 성공 시 `news_summary` 저장, 실패 시 `status=error`
- [ ] DoD: 실제 또는 모의(팀 합의)로 summary 1건+

### Lead/Report
- [ ] matplotlib 한글 폰트 탐지 유틸
- [ ] `outputs/charts`, `outputs/reports` 경로 생성 확인
- [ ] clean 샘플 기준으로 리포트용 SELECT 초안

**머지 포인트:** 샘플 N건 clean 존재 → 이후 AI/리포트가 동일 DB 사용.

---

## Day 3 — 2026-09-07 (월)

### Collect/Clean — crawl + 중복
- [ ] list 페이지 → detail 파싱
- [ ] `delay_sec` 적용, `--max-pages`
- [ ] `duplicate_policy` skip/upsert 동작 테스트
- [ ] DoD: `--method crawl --limit 5` 성공 또는 셀렉터 이슈 문서화

### Summarize/Analyze — analyze
- [ ] 배치 기사(clean+summary) 입력 → `insights_json`
- [ ] 최소 2필드: 예) `trends` + `keywords` (또는 similarities_differences / implications)
- [ ] `python main.py analyze --limit 50`
- [ ] DoD: `news_analysis` 1행 `status=ok`

### Lead/Report — charts
- [ ] 카테고리별 건수 막대 그래프 PNG
- [ ] 일별 수집/발행 추이 선 그래프 PNG
- [ ] DoD: `outputs/charts/`에 PNG 2개+

**머지 포인트:** analysis JSON 스키마 고정, 차트 입력 쿼리 합의.

---

## Day 4 — 2026-09-08 (화) — Integration

### 전원
- [ ] main에서 한 경로 E2E:
  ```bash
  python main.py fetch --source aitimes --method rss --limit 20
  python main.py clean --limit 20
  python main.py summarize --unsummarized --limit 20
  python main.py analyze --limit 20
  python main.py report --top-n 10 --format md
  python main.py export --formats csv,jsonl
  ```
- [ ] 로그에 ERROR가 있으면 티켓화 후 당일 수정
- [ ] README 실행 예시와 실제 옵션 일치

### Lead/Report
- [ ] `report`: 품질 지표 2+, TOP N, AI 인사이트 섹션
- [ ] `export`: CSV+JSONL (+가능하면 xlsx)
- [ ] 충돌 resolve, main 그린 유지

**머지 포인트: E2E 그린** — 이 시점 이후 breaking schema 변경 금지(긴급 제외).

---

## Day 5 — 2026-09-09 (수) — Buffer + Submit

### 버퍼 (오전 제안)
- [ ] 네트워크/폰트/API 실패 재시도
- [ ] 스크린샷·산출물 샘플을 `outputs/`에 남길지 팀 결정(용량·gitignore 주의)
- [ ] 커밋 메시지·작성자 확인

### 제출 체크리스트 (Lead/Report 주도)
- [ ] remote `main` 최신 + 팀원 기여 커밋 포함
- [ ] `.env` / API 키 미포함 (`git status`, `git log -p` 간단 확인)
- [ ] `requirements.txt`로 클린 venv 설치 가능
- [ ] README에 실행 방법·역할·마감 명시
- [ ] 과제 제출 양식(학교/플랫폼)에 repo URL·팀원 정보 기입
- [ ] 리포트 파일·차트·export 샘플이 재현 가능함을 확인

---

## 최소 성공 경로 (일정 밀릴 때)

우선순위(제안):
1. RSS fetch → clean → SQLite  
2. summarize 1건 + analyze 필드 2개  
3. 차트 2 PNG + report MD + export CSV+JSONL  
4. crawl은 “동작 또는 제한사항 문서화”

Selenium·xlsx·upsert는 시간 되면 추가.

---

## 커뮤니케이션 (제안)

- 스키마/CLI 변경: INTERFACE.md 수정 PR + 채팅 한 줄 공지
- 막히면: 에러 로그 10줄 + 재현 명령 공유
- 머지는 Lead/Report; 급한 hotfix는 `hotfix/` 브랜치

---

*본 일정은 제안안이며, 개인 일정에 맞게 앞당기거나 바꿔도 됩니다. 9/8 E2E와 9/9 제출만 팀 공통 앵커로 지켜 주세요.*
