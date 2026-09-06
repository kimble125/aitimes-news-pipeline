# MERGE_GUIDE.md — 브랜치·머지 규칙 (전원)

> 공개 저장소입니다. **브랜치명·커밋 메시지·주석에 실명을 쓰지 않습니다.**
> 역할 라벨만 사용: `Collect/Clean`, `Summarize/Analyze`, `Lead/Report`

---

## 0. 한 장 요약

| | 팀원 (Collect/Clean, Summarize/Analyze) | 머지 담당 (Lead/Report) |
|---|---|---|
| 작업 위치 | 내 `feature/*` 브랜치 | `main` |
| 건드리는 파일 | **내 담당 파일만** | 전체 + 통합 |
| 하루 흐름 | 아침 rebase → 작업 → 저녁 push → PR | PR 받으면 검수 → 머지 → 공지 |
| 충돌 나면 | **직접 풀지 말고 담당자 호출** | 규칙(4번)대로 판정 |
| 절대 금지 | `main` 직접 push, `--force`, 남의 파일 수정 | 검수 없이 머지 |

브랜치는 3개 고정입니다. 매번 새로 만들지 말고 계속 쓰세요.

```
feature/collect-fetch-rss     ← Collect/Clean
feature/ai-summarize          ← Summarize/Analyze
feature/report-charts         ← Lead/Report
```

---

## 1. 팀원용 — 매일 이 5줄

**아침 (작업 시작 전, 30초)**

```bash
git checkout main && git pull            # 남이 머지한 것 받아오기
git checkout feature/내-브랜치
git rebase main                          # 내 작업을 최신 main 위로 올림
```

**저녁 (작업 끝나고)**

```bash
git add <내가 고친 파일만>                 # git add . 금지
git commit -m "feat(collect): RSS 수집 구현"
git push origin feature/내-브랜치
```

그리고 GitHub에서 **Pull Request** 를 열고, 팀 채널에 링크를 올립니다.

**커밋 메시지 형식** — `<타입>(<범위>): <한 일>`
`feat` 기능 / `fix` 버그 / `docs` 문서 / `chore` 설정
범위는 `collect` `clean` `ai` `report` `db` 중 하나.

> ⚠️ 커밋은 **본인 계정으로 본인이** 하세요. 남이 대신 커밋하면 팀 기여 확인에서 빠집니다.

---

## 2. 팀원용 — 이것만 지키면 사고 안 납니다

1. **`main` 에서 직접 코드 수정 금지.** 실수했으면 4번 아래 "잘못된 곳에 커밋했을 때".
2. **`git push --force` 금지.** 남의 작업이 사라집니다. 필요하면 담당자에게 말하세요.
3. **내 담당 파일만.** 남의 파일을 고쳐야 할 것 같으면 **먼저 채널에 물어보세요.**
   - `main.py`, `src/storage/db.py`, `docs/INTERFACE.md` 는 **공용**입니다. 손대지 마세요.
   - 이 3개를 바꿔야 하면 → 채널에 "이유 + 바꿀 내용" 을 쓰고 담당자가 반영합니다.
4. **올리면 안 되는 것:** `.env`, `data/pipeline.db`, `config/config.json`, `outputs/*`, `.DS_Store`
   → `.gitignore` 에 이미 들어 있지만, push 전에 `git status` 로 한 번 보세요.
5. **API 키를 커밋·PR·채팅에 붙여넣지 마세요.** `.env` 에만 둡니다.

**PR 올릴 때 본문에 3줄만 쓰면 됩니다**

```
무엇: RSSCollector.fetch 구현
확인: python main.py fetch --method rss --limit 5 → 5건 저장됨
남은 것: 카테고리 필드는 아직 비어 있음
```

---

## 3. 머지 담당자용 — PR 하나에 5분

```bash
# 1) PR 브랜치를 로컬로 가져와서 확인
git fetch origin
git checkout feature/collect-fetch-rss
git pull

# 2) 실제로 돌아가는지 (말이 아니라 실행으로 확인)
python main.py --help
python main.py <해당 서브커맨드> --limit 5

# 3) 사고 3종 검사
git diff main --stat                     # 담당 파일 밖을 건드렸는가?
git diff main -- main.py src/storage/db.py docs/INTERFACE.md   # 공용 파일 변경?
git diff main | grep -iE "api.key|sk-|Bearer |실명"             # 키·실명 유출?

# 4) 통과하면 머지
git checkout main
git merge --no-ff feature/collect-fetch-rss
git push origin main
```

`--no-ff` 를 쓰는 이유: 누가 어떤 작업을 했는지 기록이 남습니다(팀 기여 근거).

**머지 후 팀 채널에 한 줄:** `main 에 <무엇> 머지됨 → 각자 rebase 해주세요`

**되돌리기** (머지했는데 깨졌을 때)

```bash
git revert -m 1 <머지커밋해시>    # 이력을 남기며 취소. reset --hard 쓰지 말 것
```

---

## 4. 충돌 났을 때 — 판정 규칙

**팀원은 충돌을 직접 풀지 마세요.** `git rebase --abort` 로 되돌리고 담당자를 부르세요.

| 충돌 지점 | 판정 |
|---|---|
| DB 컬럼 / 함수 시그니처 / 경로 | **`docs/INTERFACE.md` 가 항상 이깁니다** |
| `main.py`, `src/storage/db.py` | **머지 담당자 것이 기준** — 팀원 변경은 되돌리고 별도 논의 |
| 내 담당 파일끼리 | 해당 담당자 본인이 판단 |
| `docs/` | 양쪽 내용을 합칩니다 |

**스키마를 바꿔야 할 때** (순서 지키기)

1. 채널에 제안 → 2. `docs/INTERFACE.md` 수정 → 3. `db.py` 반영 →
4. **"DB 삭제 후 재수집 필요" 공지** → 5. 전원 `rm -f data/pipeline.db && python main.py initdb`

> Phase 4(E2E 통과) 이후에는 **스키마 변경 금지.**

---

## 5. 사고 복구 3가지

**잘못된 곳(main)에 커밋했을 때**

```bash
git branch feature/내-브랜치        # 지금 상태를 브랜치로 저장
git reset --hard origin/main        # main 을 원격 상태로 되돌림
git checkout feature/내-브랜치
```

**커밋 안 한 변경을 잠깐 치워둘 때**

```bash
git stash          # 치우기
git stash pop      # 되돌리기
```

**올리면 안 되는 파일을 이미 커밋했을 때** — 혼자 지우지 말고 담당자에게 말하세요.
(키가 포함됐다면 **즉시 그 키를 폐기·재발급**하는 게 먼저입니다. 커밋만 지워도 이력에 남습니다.)

---

## 6. 제출 직전 체크 (담당자)

```bash
git status                                   # 깨끗한가
git log --oneline --graph | head -20         # 3명 커밋이 다 보이는가
git shortlog -sn                             # 기여자 3명
git log -p | grep -iE "api.key|sk-"          # 키 유출 0건
python main.py --help                        # 서브커맨드 6종
```

마지막으로 `docs/EVALUATION.md` 의 검증 명령 9개를 위에서부터 순서대로 실행 →
`outputs/charts/*.png` 2개, `outputs/reports/*.md`, `outputs/*.csv`, `*.jsonl` 생성 확인.

---

## 7. 막혔을 때

- 계약(컬럼·함수·경로): `docs/INTERFACE.md`
- 내가 뭘 해야 하는지: `docs/roles/<내 역할>.md`
- 지금 어느 단계인지: `docs/ACTION_PLAN.md`
- 그래도 막히면 채널에 **에러 로그 10줄 + 실행한 명령어** (스크린샷 X)
