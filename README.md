# AI타임스 뉴스 파이프라인 (A2-2 / Project B)

[AI타임스](https://www.aitimes.com/) 기사를 **수집 → 정제 → AI 요약 → 인사이트 분석 → 시각화·리포트 → 내보내기** 하는 Python CLI 파이프라인입니다. 웹 UI 없이 CLI만으로 전 과정이 동작합니다.

```
[RSS]  ──┐
         ├─ fetch ─→ news_raw ─ clean ─→ news_clean ─┬─ summarize ─→ news_summary ─┐
[크롤링] ─┘                                          └─ analyze ───→ news_analysis ─┤
                                                                                    ├─→ report (차트 PNG + MD/TXT)
                                                                                    └─→ export (CSV/JSONL/XLSX)
```

---

## 1. 빠른 시작 (3분)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config/config.example.json config/config.json
cp .env.example .env          # AI_API_KEY 를 채우면 summarize/analyze 사용 가능

python main.py --help         # 서브커맨드 6종 확인
python main.py initdb         # SQLite 스키마(4테이블) 생성
```

## 2. 전체 실행 (E2E)

> ⚠️ **`rss` → `crawl` 순서를 지키세요.** 두 방식이 같은 기사 URL 을 수집하기 때문에,
> `duplicate_policy: "upsert"` 와 이 순서가 맞물려야 크롤링이 가져온 **카테고리와 본문 전문**이
> RSS 행 위에 채워집니다. 순서가 반대면 RSS(리드 문단·카테고리 없음)가 덮어써서
> 카테고리 차트가 비고 요약 품질이 떨어집니다.

```bash
python main.py fetch --source aitimes --method rss --limit 20   # ① RSS 수집 (넓게)
python main.py fetch --source aitimes --method crawl --limit 20 # ② 크롤링으로 본문·카테고리 보강
python main.py clean --limit 30
python main.py summarize --unsummarized --limit 20
python main.py analyze --limit 50
python main.py report --top-n 10 --format md
python main.py export --formats csv,jsonl
```

산출물 위치: 차트 `outputs/charts/*.png` · 리포트 `outputs/reports/*` · export `outputs/*.csv|jsonl|xlsx` · 로그 `logs/pipeline.log` · DB `data/pipeline.db`

---

## 3. 평가자용 안내

요구사항이 **어느 파일·어느 명령으로 충족되는지**를 한 표로 정리한 문서가 있습니다.

👉 **[docs/EVALUATION.md](docs/EVALUATION.md) — 요구사항 대조표 + 검증 명령**

---

## 4. 저장소 구조

```
main.py                       # argparse 진입점 (6개 서브커맨드 디스패치)
config/config.example.json    # 소스 URL·중복정책·경로·로깅 설정
.env.example                  # AI_API_KEY / AI_BASE_URL / AI_MODEL (커밋 금지)
src/
  collectors/  base.py rss.py crawl.py    # 수집 (RSS + 크롤링)
  cleaners/    cleaner.py                 # 정제 (raw → clean)
  ai/          summarizer.py analyzer.py  # AI 요약 / 인사이트
  report/      charts.py reporter.py exporter.py  # 차트·리포트·export
  storage/     db.py                      # SQLite 4테이블 (공용)
  utils/       config.py logging_setup.py # 설정·로깅
docs/
  EVALUATION.md   # 평가자용 요구사항 대조표
  PLAN.md         # 설계안 (아키텍처·스키마·품질지표 정의)
  INTERFACE.md    # 팀 간 계약 (테이블·함수 시그니처·경로) — 단일 진실원
  ACTION_PLAN.md  # 단계별 진행 체크리스트
  SHARED_PROMPT.md# 팀 공통 AI 프롬프트
  roles/          # 역할별 "내가 할 일" 문서 3종
data/ outputs/ logs/          # 생성물 (gitignore)
```

---

## 5. 역할 분담 (워크스트림 단위)

| 워크스트림 | 담당 서브커맨드 | 담당 파일 | 내가 할 일 문서 |
|---|---|---|---|
| **Collect/Clean** | `fetch`, `clean` | `src/collectors/*`, `src/cleaners/*` | [docs/roles/COLLECT_CLEAN.md](docs/roles/COLLECT_CLEAN.md) |
| **Summarize/Analyze** | `summarize`, `analyze` | `src/ai/*` | [docs/roles/SUMMARIZE_ANALYZE.md](docs/roles/SUMMARIZE_ANALYZE.md) |
| **Lead/Report** | `report`, `export` | `src/report/*`, `src/storage/*`, `main.py` | [docs/roles/LEAD_REPORT.md](docs/roles/LEAD_REPORT.md) |

> **내가 뭘 해야 하는지 모르겠다면?** 담당 명령을 그냥 실행해 보세요.
> 미구현 단계는 *어느 파일을 고쳐야 하는지*를 에러 메시지로 알려줍니다.
> ```
> $ python main.py fetch --limit 3
> [ERROR] `fetch` 는 아직 구현되지 않았습니다
> [ERROR] 담당 워크스트림: Collect/Clean / 구현 대상: src/collectors/rss.py, src/collectors/crawl.py
> ```

**협업 규칙**
- 브랜치: `feature/collect-fetch-rss`, `feature/ai-summarize`, `feature/report-charts` (실명·이니셜 금지)
- 각자 브랜치에 커밋 → Lead/Report 가 `main` 에 머지
- 스키마/CLI 옵션을 바꾸면 **`docs/INTERFACE.md` 를 함께 수정**하고 팀에 공지

---

## 6. 정기 실행 스케줄링 (보너스)

매일 오전 8시 수집·정제:

```bash
crontab -e
0 8 * * * cd /path/to/aitimes-news-pipeline && .venv/bin/python main.py fetch --method rss --limit 30 >> logs/cron.log 2>&1
5 8 * * * cd /path/to/aitimes-news-pipeline && .venv/bin/python main.py clean >> logs/cron.log 2>&1
```

Windows 는 작업 스케줄러에서 동일 명령을 등록합니다.

---

## 7. 보안·윤리

- API 키는 `.env` 로만 관리하며 코드·커밋에 넣지 않습니다 (`.gitignore` 처리).
- 크롤링은 `config.crawl.delay_sec` 만큼 요청 간 지연을 두고, `max_pages` / `max_articles_per_run` 로 요청량을 제한합니다.
- 저장소 문서·코드에는 개인 실명을 쓰지 않고 워크스트림 라벨만 사용합니다.
