# HANDOFF — Codyssey A2-2 / Project B (다음 AI용)

> 작성 시각: 2026-09-04 (KST)  
> 목적: 후속 AI가 **즉시** 이어받을 수 있게 상태·해야 할 일·제약만 전달한다.

---

## 0) 최우선 (보안/프라이버시) — 반드시 먼저

1. **실명 모두 지우기**  
   - public 레포 `https://github.com/kimble125/aitimes-news-pipeline` 및 로컬 `/workspace/aitimes-news-pipeline`에서  
     팀원 **실명·개인식별 정보**를 문서/코드 주석/커밋 메시지/이슈에서 **전부 제거**한다.
2. **이름이 아닌 작업 단위로 역할 배분**  
   - 역할 표기는 아래처럼 **워크스트림 라벨**만 사용한다 (실명 금지).
     - `Collect/Clean` — `fetch`, `clean` (RSS + 크롤링, raw/clean)
     - `Summarize/Analyze` — `summarize`, `analyze` (AI API)
     - `Lead/Report` — repo/merge/제출, `report`, 차트, `export`, storage/CLI 통합
3. public 레포에 실명·이메일·학교 개인정보를 다시 넣지 말 것. 필요하면 **사용자에게 먼저 확인**.
4. (이미 로컬에서는 실명→역할 라벨 치환 완료. **원격에 아직 옛 실명 문서가 남아 있을 수 있으니 remote docs를 덮어써 스크럽할 것.**)

---

## 1) 과제 한 줄

AI타임스(`https://www.aitimes.com/`) 뉴스 → 수집·정제·AI 요약·인사이트·시각화·리포트·export 하는 **Python CLI** (Project B).

마감: **2026-09-09 (수)**  
오늘(기획일): 2026-09-04

---

## 2) 필수 요구 (과제 스펙)

- CLI argparse 서브커맨드: `fetch | clean | summarize | analyze | report | export`
- 수집: **RSS/API + 크롤링** 둘 다
- raw/clean 분리, 중복 skip/upsert
- AI 요약 + 인사이트(트렌드/키워드/유사·차이/시사점 중 2+)
- matplotlib 차트 2+(카테고리 건수, 일별 추이), 한글 폰트, PNG
- 리포트: 품질지표 2+, TOP N, AI 인사이트 / 콘솔+TXT|MD
- export: CSV/JSONL/Excel 중 최소 2
- `config.json` + logging; API 키는 코드에 넣지 말 것
- 영속 저장 SQLite(권장) 또는 JSONL; 모듈 4개+; Python 3.10+; 웹 UI 없음

---

## 3) 현재 상태 (사실)

| 항목 | 상태 |
|------|------|
| GitHub repo | **있음** https://github.com/kimble125/aitimes-news-pipeline (public) |
| GitHub owner | `kimble125` (계정 식별자; 문서에 실명 쓰지 말 것) |
| README / docs | remote에 있음 — **실명 포함본일 수 있음 → 스크럽 push 필요** |
| `main.py` | **remote에 없을 수 있음** (로컬에는 있음) |
| `src/storage/db.py` | **remote에 없을 수 있음** (로컬에는 있음) |
| 본 구현 | **미구현** (stub) |

로컬 경로: `/workspace/aitimes-news-pipeline`

---

## 4) 바로 할 일 (우선순위)

### P0
1. 원격 docs/README/주석 **실명 스크럽** 후 push.
2. `main.py`, `src/storage/**` push.
3. 사용자에게 스크럽 완료 확인.

### P1
4. docs는 **제안안(draft)** 유지. 역할은 작업 단위 라벨만.
5. 공동 프롬프트: `docs/SHARED_PROMPT.md`

### P2
6. Collect/Clean → Summarize/Analyze → Lead/Report 순으로 구현·E2E·제출

---

## 5) 사용자 제약

- 한국어 소통. 막히면 질문 후 진행.
- **public에 실명 올리지 말 것. 반드시 사용자에게 먼저 확인.**
- 속도 중요: 불필요하게 지연하지 말 것.

## 6) 복붙용 한 줄

```text
https://github.com/kimble125/aitimes-news-pipeline 이어받기.
P0: public에서 팀원 실명 전부 삭제하고 역할은 Collect/Clean·Summarize/Analyze·Lead/Report 작업 단위로만 표기 후 push.
이어서 main.py·src/storage remote에 올리고 A2-2 CLI 구현 진행.
실명·개인정보는 사용자 확인 없이 public에 넣지 말 것. 한국어로 보고.
```
