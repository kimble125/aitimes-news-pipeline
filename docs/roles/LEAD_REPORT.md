# 역할: Lead/Report — 시각화 · 리포트 · 내보내기 · 통합

담당 서브커맨드: **`report`, `export`** + 저장소 통합

## 내가 건드릴 파일

| 파일 | 할 일 |
|------|-------|
| `src/report/charts.py` | `setup_korean_font()`, `make_charts()` 구현 |
| `src/report/reporter.py` | `write_report()` 구현 |
| `src/report/exporter.py` | `export_data()` 구현 |
| `src/storage/db.py` | ✅ 완료 — 스키마 관리 책임만 유지 |
| `main.py` | ✅ 완료 — 팀원 PR 반영 시에만 수정 |

## 시작하기

```bash
git checkout -b feature/report-charts
python main.py initdb
python main.py report          # 지금은 "미구현" 에러 — 여기서 시작
```

## 작업 1 — 차트 2종 (`src/report/charts.py`)

집계 쿼리는 이미 만들어져 있습니다:

```python
from src.storage import db
with db.get_connection(db_path) as conn:
    cats  = db.category_counts(conn)   # [("경제", 12), ("정책", 8), ...]
    daily = db.daily_counts(conn)      # [("2026-09-01", 5), ("2026-09-02", 9), ...]
```

- 차트 1: 카테고리별 기사 수 **막대그래프**
- 차트 2: 일자별 수집 추이 **선그래프**
- `setup_korean_font()`: `matplotlib.font_manager` 로 `AppleGothic`(macOS) / `NanumGothic` / `Noto Sans CJK KR` 순으로 탐지 → `plt.rcParams["font.family"]` 설정, `axes.unicode_minus = False`. 못 찾으면 WARNING 로그.
- `outputs/charts/*.png` 로 저장하고 **경로 리스트를 반환**
- 데이터가 0건이면 빈 차트를 그리지 말고 WARNING 후 `[]` 반환

**DoD:** `outputs/charts/` 에 PNG 2개 이상, 한글 라벨이 깨지지 않음

## 작업 2 — 리포트 (`src/report/reporter.py`)

```python
stats    = db.pipeline_stats(conn)        # 품질 지표 원천 — 하드코딩 금지
articles = db.get_clean_articles(conn, limit=top_n)
analysis = db.get_latest_analysis(conn)   # {"insights": {...}} 또는 None
```

리포트에 반드시 포함:
1. **품질 지표 2개 이상** — `stats["fetch_success_rate"]`, `stats["summary_coverage"]`, `stats["clean_rate"]`, `stats["avg_word_count"]` 중 선택
2. **TOP N 기사 목록** — 제목 + URL + 카테고리 (+ 요약 있으면 요약)
3. **AI 인사이트 섹션** — `analysis["insights"]` 의 trends / keywords 등
4. 생성된 차트 이미지 링크 (MD 인 경우 `![](../charts/xxx.png)`)

출력: **콘솔에 print + `outputs/reports/report.YYYYMMDD.md`(또는 .txt) 저장**, 파일 경로 반환.
`fmt="both"` 면 두 형식 모두 저장.

**DoD:** 콘솔 출력 + 파일 생성, 지표 수치가 DB 실측값과 일치

## 작업 3 — 내보내기 (`src/report/exporter.py`)

```python
rows = db.get_clean_articles(conn, with_summary=True)   # clean + summary 조인
```
- `csv` : `pandas.DataFrame(rows).to_csv(..., index=False, encoding="utf-8-sig")` ← 엑셀 한글 깨짐 방지
- `jsonl` : 한 줄에 dict 하나, `ensure_ascii=False`
- `xlsx` : `to_excel(..., engine="openpyxl")`
- `--status summarized` 필터: `summary_status == "ok"` 인 행만
- `outputs/` 아래 저장하고 파일 경로 리스트 반환

**DoD:** 최소 2개 포맷 파일 생성, 한글이 깨지지 않음

## 작업 4 — 통합 (Lead 업무)

- 팀원 브랜치 리뷰·머지, 충돌 시 **`docs/INTERFACE.md` 가 우선**
- 스키마 변경 요청이 오면 INTERFACE 수정 → `db.py` 반영 → 팀에 "재수집 필요" 공지
- 제출 전 점검:
  ```bash
  git status                       # .env, *.db 가 안 올라갔는지
  git log -p | grep -i "api.key"   # 키 유출 확인
  python main.py --help            # 6개 서브커맨드
  ```
  그리고 `docs/EVALUATION.md` 의 검증 명령 9개를 순서대로 실행

## 선택 작업 (보너스 점수)

- `list` / `show` 서브커맨드 — `main.py` 에 파서 추가 + `db.get_clean_articles()` 재사용 (필터·페이지네이션)
- 감성 분석 — Summarize/Analyze 와 협의해 `insights_json.sentiment` 확장 + 차트 1종 추가

## 막혔을 때

- 계약: `docs/INTERFACE.md`
- 품질 지표 정의: `docs/PLAN.md` §9
- AI 도구 프롬프트: `docs/SHARED_PROMPT.md` §A + §B-3
