# 역할: Summarize/Analyze — AI 요약 · 인사이트 분석

담당 서브커맨드: **`summarize`, `analyze`**

## 내가 건드릴 파일 (이 2개만)

| 파일 | 할 일 |
|------|-------|
| `src/ai/summarizer.py` | `summarize_article()`, `run_summarize()` 구현 |
| `src/ai/analyzer.py` | `analyze_batch()`, `run_analyze()` 구현 |

**건드리지 말 것:** `src/collectors/*`, `src/cleaners/*`, `src/report/*`, `main.py`, `src/storage/db.py`

## 시작하기

```bash
git checkout -b feature/ai-summarize
cp .env.example .env      # AI_API_KEY, AI_BASE_URL, AI_MODEL 채우기 (절대 커밋 금지)
python main.py summarize --limit 3   # 지금은 "미구현" 에러 — 여기서 시작
```

> **먼저 확인:** 요약할 기사가 있어야 합니다. Collect/Clean 이 아직이면
> `python main.py initdb` 후 `news_clean` 에 테스트 행 몇 개를 직접 INSERT 해서 개발해도 됩니다.

## 작업 1 — `summarize`

```python
summarize_article(title: str, body: str, *, model: str | None = None) -> str
```
- 환경변수: `AI_API_KEY`, `AI_BASE_URL`, `AI_MODEL` (`os.getenv`, `.env` 는 이미 로드됨)
- OpenAI-compatible `chat/completions` 호출
- 프롬프트: **한국어 3~8문장, 사실 위주, 추측 금지**
- 본문이 너무 길면 앞부분만 자르기 (토큰 가드)

`run_summarize()` 루프 — 헬퍼는 이미 준비되어 있습니다:

```python
from src.storage import db

def run_summarize(db_path, limit=20, clean_id=None, unsummarized=True, config=None):
    if not os.getenv("AI_API_KEY"):
        logger.error("AI_API_KEY 가 없습니다 — .env 를 확인하세요")
        return 0
    done = 0
    with db.get_connection(db_path) as conn:
        targets = db.get_unsummarized(conn, limit=limit, clean_id=clean_id)
        for i, art in enumerate(targets, 1):
            try:
                text = summarize_article(art["title"], art["body_text"])
                db.upsert_summary(conn, {"clean_id": art["id"], "summary_text": text,
                                         "model": os.getenv("AI_MODEL"), "status": "ok"})
                logger.info("[%d/%d] ID=%s 요약 완료 (%d자 → %d자)",
                            i, len(targets), art["id"], len(art["body_text"] or ""), len(text))
                done += 1
            except Exception as exc:            # 한 건 실패가 전체를 멈추면 안 됨
                logger.error("ID=%s 요약 실패: %s", art["id"], exc)
                db.upsert_summary(conn, {"clean_id": art["id"], "status": "error",
                                         "error_message": str(exc)})
    return done
```

**완료 기준(DoD)**
- [ ] `python main.py summarize --unsummarized --limit 10` 이 건별 진행 로그를 남긴다
- [ ] 같은 명령을 다시 실행하면 이미 요약된 건은 **스킵**된다
- [ ] API 실패 시 traceback 이 아니라 ERROR 로그 + `news_summary.status='error'` 로 남는다
- [ ] `python main.py summarize --help` 에 `--all / --id / --unsummarized` 가 보인다

## 작업 2 — `analyze`

```python
analyze_batch(articles: list[dict], *, model: str | None = None) -> dict
```

여러 기사(요약 우선, 없으면 본문 일부)를 **한 번의 호출**로 보내 구조화 JSON 을 받습니다.
**최소 2개 키를 채워야 과제 요구사항을 충족합니다.**

```json
{
  "trends": ["AI 반도체 공급망 재편 가속"],
  "keywords": [{"term": "생성형 AI", "score": 0.92}],
  "similarities_differences": {"similar": ["..."], "different": ["..."]},
  "implications": ["..."],
  "top_articles": [{"url": "...", "title": "...", "reason": "..."}]
}
```

- 프롬프트에 **"JSON only, 코드펜스 없이"** 를 명시하고, `json.loads` 실패 시 재시도 또는 `status='error'`
- 저장은 `db.insert_analysis(conn, {"batch_key": ..., "insights_json": result, "model": ...})`
  — `insights_json` 에 dict 를 그대로 넘겨도 자동 직렬화됩니다.
- 대상 기사 조회: `db.get_clean_articles(conn, limit=limit, since=since, category=category)`

**완료 기준(DoD)**
- [ ] `python main.py analyze --limit 50` 이 성공하고 `news_analysis` 에 `status='ok'` 행 1개
- [ ] `insights_json` 에 **non-empty 키가 2개 이상**
- [ ] `--since 2026-09-01` 같은 필터가 동작한다

## 막혔을 때

- JSON 스키마·컬럼: `docs/INTERFACE.md` §2.3, §2.4
- 사용할 DB 헬퍼: `db.get_unsummarized`, `db.upsert_summary`, `db.get_clean_articles`, `db.insert_analysis`
- AI 도구에 붙여넣을 프롬프트: `docs/SHARED_PROMPT.md` §A + §B-2
- **주의:** API 키를 채팅·커밋·이슈에 붙여넣지 마세요.
