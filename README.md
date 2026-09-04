# AI타임스 뉴스 파이프라인 (A2-2 / Project B)

AI타임스(https://www.aitimes.com/) 기사를 수집·정제·AI 요약·분석·시각화·리포트·내보내기까지 수행하는 CLI 파이프라인입니다.

> **문서 안내:** `docs/PLAN.md`, `docs/ACTION_PLAN.md`, `docs/SHARED_PROMPT.md`, `docs/INTERFACE.md`는 **제안안(draft proposal)** 입니다.  
> 모델 선택, 세부 일정, 작업 시간 배분은 각 담당이 **자율적으로** 결정합니다. 인터페이스·DoD만 맞추면 됩니다.

## 역할 (작업 단위 — 실명 사용 금지)

| 워크스트림 | 주요 범위 |
|------|-----------|
| **Lead/Report** | GitHub repo·merge·push, storage/CLI, 시각화·리포트·export, 최종 제출 |
| **Collect/Clean** | `fetch`(RSS + 크롤링), `clean`, raw/clean 스키마·중복 처리 |
| **Summarize/Analyze** | `summarize`(AI), `analyze`(인사이트 2종 이상), 구조화 JSON |

공유 원칙: 각자 브랜치 커밋 → Lead/Report가 main에 merge/push.

## 빠른 시작

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp config/config.example.json config/config.json
python main.py --help
```

## 브랜치 예 (실명/이니셜 금지)

```
feature/collect-fetch-rss
feature/ai-summarize
feature/report-charts
```

## 마감

- **제출 마감:** 2026-09-09 (수)
- 상세 제안: `docs/ACTION_PLAN.md` / handoff: `docs/HANDOFF.md`
