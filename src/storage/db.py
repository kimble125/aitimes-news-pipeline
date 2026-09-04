"""SQLite 영속 저장 계층 — 공용 모듈.

담당: Lead/Report (스키마 유지) / 모든 워크스트림이 호출해서 사용.

`docs/INTERFACE.md` 의 테이블 계약을 그대로 구현한 것이므로,
컬럼을 바꾸려면 INTERFACE.md 를 먼저 고치고 팀에 공지한다.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS news_raw (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source TEXT NOT NULL,
      method TEXT NOT NULL,
      guid TEXT,
      url TEXT NOT NULL,
      title TEXT,
      published_at TEXT,
      category TEXT,
      author TEXT,
      raw_html TEXT,
      raw_text TEXT,
      fetched_at TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'fetched',
      error_message TEXT,
      UNIQUE(url)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_news_raw_source ON news_raw(source)",
    "CREATE INDEX IF NOT EXISTS idx_news_raw_fetched_at ON news_raw(fetched_at)",
    "CREATE INDEX IF NOT EXISTS idx_news_raw_status ON news_raw(status)",
    """
    CREATE TABLE IF NOT EXISTS news_clean (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      raw_id INTEGER NOT NULL,
      source TEXT NOT NULL,
      url TEXT NOT NULL UNIQUE,
      title TEXT,
      published_at TEXT,
      category TEXT,
      author TEXT,
      body_text TEXT,
      word_count INTEGER DEFAULT 0,
      language TEXT DEFAULT 'ko',
      cleaned_at TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'clean',
      quality_flags TEXT,
      FOREIGN KEY(raw_id) REFERENCES news_raw(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_news_clean_category ON news_clean(category)",
    "CREATE INDEX IF NOT EXISTS idx_news_clean_published_at ON news_clean(published_at)",
    """
    CREATE TABLE IF NOT EXISTS news_summary (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      clean_id INTEGER NOT NULL UNIQUE,
      summary_text TEXT,
      model TEXT,
      prompt_version TEXT DEFAULT 'v1',
      created_at TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'ok',
      error_message TEXT,
      FOREIGN KEY(clean_id) REFERENCES news_clean(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS news_analysis (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      scope TEXT NOT NULL DEFAULT 'batch',
      batch_key TEXT NOT NULL,
      insights_json TEXT NOT NULL,
      model TEXT,
      created_at TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'ok',
      error_message TEXT
    )
    """,
)

RAW_COLUMNS: tuple[str, ...] = (
    "source", "method", "guid", "url", "title", "published_at",
    "category", "author", "raw_html", "raw_text", "fetched_at",
    "status", "error_message",
)

CLEAN_COLUMNS: tuple[str, ...] = (
    "raw_id", "source", "url", "title", "published_at", "category",
    "author", "body_text", "word_count", "language", "cleaned_at",
    "status", "quality_flags",
)


def now_iso() -> str:
    """UTC ISO8601 문자열. 모든 타임스탬프 컬럼은 이 형식을 쓴다."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_connection(db_path: str) -> sqlite3.Connection:
    """DB 커넥션을 연다. 부모 디렉터리는 자동 생성한다."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    """4개 테이블과 인덱스를 생성한다(이미 있으면 그대로 둔다)."""
    with get_connection(db_path) as conn:
        for stmt in SCHEMA_STATEMENTS:
            conn.execute(stmt)
    logger.info("DB 초기화 완료: %s", db_path)


def _pick(row: dict[str, Any], columns: Iterable[str]) -> dict[str, Any]:
    return {c: row.get(c) for c in columns}


# --------------------------------------------------------------------------
# raw (작성: Collect/Clean)
# --------------------------------------------------------------------------

def upsert_raw(conn: sqlite3.Connection, row: dict[str, Any], policy: str = "skip") -> str:
    """news_raw 한 건 저장.

    policy='skip'  : 같은 url 이 있으면 아무것도 하지 않는다.
    policy='upsert': 같은 url 이 있으면 새 값으로 갱신한다.

    Returns: 'inserted' | 'updated' | 'skipped'
    """
    if not row.get("url"):
        raise ValueError("news_raw 행에 url 이 필요합니다")

    data = _pick(row, RAW_COLUMNS)
    data.setdefault("source", "aitimes")
    data.setdefault("method", "rss")
    data["fetched_at"] = data.get("fetched_at") or now_iso()
    data["status"] = data.get("status") or "fetched"

    existing = conn.execute(
        "SELECT id FROM news_raw WHERE url = ?", (data["url"],)
    ).fetchone()

    if existing is None:
        cols = ", ".join(RAW_COLUMNS)
        marks = ", ".join(["?"] * len(RAW_COLUMNS))
        conn.execute(
            f"INSERT INTO news_raw ({cols}) VALUES ({marks})",
            tuple(data[c] for c in RAW_COLUMNS),
        )
        return "inserted"

    if policy != "upsert":
        return "skipped"

    updatable = [c for c in RAW_COLUMNS if c != "url"]
    assignments = ", ".join(f"{c} = ?" for c in updatable)
    conn.execute(
        f"UPDATE news_raw SET {assignments} WHERE url = ?",
        tuple(data[c] for c in updatable) + (data["url"],),
    )
    return "updated"


def get_raw_for_clean(
    conn: sqlite3.Connection,
    source: str | None = None,
    limit: int | None = None,
    include_cleaned: bool = False,
) -> list[dict[str, Any]]:
    """정제 대상 raw 행을 반환한다(기본: 아직 clean 되지 않은 것만)."""
    sql = ["SELECT r.* FROM news_raw r"]
    params: list[Any] = []
    if not include_cleaned:
        sql.append("LEFT JOIN news_clean c ON c.raw_id = r.id")
    sql.append("WHERE r.status = 'fetched'")
    if not include_cleaned:
        sql.append("AND c.id IS NULL")
    if source:
        sql.append("AND r.source = ?")
        params.append(source)
    sql.append("ORDER BY r.id ASC")
    if limit:
        sql.append("LIMIT ?")
        params.append(limit)
    rows = conn.execute(" ".join(sql), params).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# clean (작성: Collect/Clean)
# --------------------------------------------------------------------------

def upsert_clean(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    """news_clean 한 건 저장(url 기준 upsert). clean id 를 반환한다."""
    if not row.get("url"):
        raise ValueError("news_clean 행에 url 이 필요합니다")

    data = _pick(row, CLEAN_COLUMNS)
    data["cleaned_at"] = data.get("cleaned_at") or now_iso()
    data["status"] = data.get("status") or "clean"
    data["language"] = data.get("language") or "ko"
    data["word_count"] = data.get("word_count") or 0
    if isinstance(data.get("quality_flags"), (dict, list)):
        data["quality_flags"] = json.dumps(data["quality_flags"], ensure_ascii=False)

    cols = ", ".join(CLEAN_COLUMNS)
    marks = ", ".join(["?"] * len(CLEAN_COLUMNS))
    updatable = [c for c in CLEAN_COLUMNS if c != "url"]
    assignments = ", ".join(f"{c} = excluded.{c}" for c in updatable)
    cur = conn.execute(
        f"INSERT INTO news_clean ({cols}) VALUES ({marks}) "
        f"ON CONFLICT(url) DO UPDATE SET {assignments}",
        tuple(data[c] for c in CLEAN_COLUMNS),
    )
    if cur.lastrowid:
        return int(cur.lastrowid)
    found = conn.execute(
        "SELECT id FROM news_clean WHERE url = ?", (data["url"],)
    ).fetchone()
    return int(found["id"])


# --------------------------------------------------------------------------
# summary / analysis (작성: Summarize/Analyze)
# --------------------------------------------------------------------------

def get_unsummarized(
    conn: sqlite3.Connection,
    limit: int | None = None,
    clean_id: int | None = None,
) -> list[dict[str, Any]]:
    """아직 요약되지 않은 clean 기사를 반환한다."""
    sql = [
        "SELECT c.* FROM news_clean c",
        "LEFT JOIN news_summary s ON s.clean_id = c.id AND s.status = 'ok'",
        "WHERE c.status = 'clean' AND s.id IS NULL",
    ]
    params: list[Any] = []
    if clean_id is not None:
        sql.append("AND c.id = ?")
        params.append(clean_id)
    sql.append("ORDER BY c.id ASC")
    if limit:
        sql.append("LIMIT ?")
        params.append(limit)
    return [dict(r) for r in conn.execute(" ".join(sql), params).fetchall()]


def get_clean_articles(
    conn: sqlite3.Connection,
    limit: int | None = None,
    since: str | None = None,
    category: str | None = None,
    with_summary: bool = True,
) -> list[dict[str, Any]]:
    """분석·리포트·export 공용 조회. clean(+summary) 조인 결과."""
    select = "SELECT c.*"
    join = ""
    if with_summary:
        select += ", s.summary_text, s.model AS summary_model, s.status AS summary_status"
        join = "LEFT JOIN news_summary s ON s.clean_id = c.id"
    sql = [select, "FROM news_clean c", join, "WHERE c.status = 'clean'"]
    params: list[Any] = []
    if since:
        sql.append("AND COALESCE(c.published_at, c.cleaned_at) >= ?")
        params.append(since)
    if category:
        sql.append("AND c.category = ?")
        params.append(category)
    sql.append("ORDER BY COALESCE(c.published_at, c.cleaned_at) DESC")
    if limit:
        sql.append("LIMIT ?")
        params.append(limit)
    return [dict(r) for r in conn.execute(" ".join(sql), params).fetchall()]


def upsert_summary(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    """news_summary 저장(clean_id 기준 upsert)."""
    clean_id = row.get("clean_id")
    if clean_id is None:
        raise ValueError("news_summary 행에 clean_id 가 필요합니다")
    cur = conn.execute(
        """
        INSERT INTO news_summary
          (clean_id, summary_text, model, prompt_version, created_at, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(clean_id) DO UPDATE SET
          summary_text = excluded.summary_text,
          model = excluded.model,
          prompt_version = excluded.prompt_version,
          created_at = excluded.created_at,
          status = excluded.status,
          error_message = excluded.error_message
        """,
        (
            clean_id,
            row.get("summary_text"),
            row.get("model"),
            row.get("prompt_version") or "v1",
            row.get("created_at") or now_iso(),
            row.get("status") or "ok",
            row.get("error_message"),
        ),
    )
    if cur.lastrowid:
        return int(cur.lastrowid)
    found = conn.execute(
        "SELECT id FROM news_summary WHERE clean_id = ?", (clean_id,)
    ).fetchone()
    return int(found["id"])


def insert_analysis(conn: sqlite3.Connection, row: dict[str, Any]) -> int:
    """news_analysis 한 행 추가. insights_json 은 dict 로 넘겨도 된다."""
    insights = row.get("insights_json")
    if isinstance(insights, (dict, list)):
        insights = json.dumps(insights, ensure_ascii=False)
    if not insights:
        raise ValueError("news_analysis 행에 insights_json 이 필요합니다")
    cur = conn.execute(
        """
        INSERT INTO news_analysis
          (scope, batch_key, insights_json, model, created_at, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.get("scope") or "batch",
            row.get("batch_key") or now_iso(),
            insights,
            row.get("model"),
            row.get("created_at") or now_iso(),
            row.get("status") or "ok",
            row.get("error_message"),
        ),
    )
    return int(cur.lastrowid or 0)


def get_latest_analysis(conn: sqlite3.Connection) -> dict[str, Any] | None:
    """리포트에 실을 최신 성공 분석 1건. 없으면 None."""
    row = conn.execute(
        "SELECT * FROM news_analysis WHERE status = 'ok' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    try:
        result["insights"] = json.loads(result["insights_json"])
    except (TypeError, ValueError):
        result["insights"] = {}
    return result


# --------------------------------------------------------------------------
# 집계 (사용: Lead/Report)
# --------------------------------------------------------------------------

def count_rows(conn: sqlite3.Connection, table: str, where: str = "", params: Iterable[Any] = ()) -> int:
    """단순 건수 조회. 품질 지표를 하드코딩하지 말고 이 함수로 계산할 것."""
    if table not in {"news_raw", "news_clean", "news_summary", "news_analysis"}:
        raise ValueError(f"허용되지 않은 테이블: {table}")
    sql = f"SELECT COUNT(*) AS n FROM {table}"
    if where:
        sql += f" WHERE {where}"
    return int(conn.execute(sql, tuple(params)).fetchone()["n"])


def category_counts(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """카테고리별 기사 수 — 차트 1번용."""
    rows = conn.execute(
        """
        SELECT COALESCE(NULLIF(TRIM(category), ''), '미분류') AS category, COUNT(*) AS n
        FROM news_clean WHERE status = 'clean'
        GROUP BY category ORDER BY n DESC
        """
    ).fetchall()
    return [(r["category"], int(r["n"])) for r in rows]


def daily_counts(conn: sqlite3.Connection) -> list[tuple[str, int]]:
    """일자별 기사 수 — 차트 2번용."""
    rows = conn.execute(
        """
        SELECT SUBSTR(COALESCE(published_at, cleaned_at), 1, 10) AS day, COUNT(*) AS n
        FROM news_clean WHERE status = 'clean'
        GROUP BY day ORDER BY day ASC
        """
    ).fetchall()
    return [(r["day"], int(r["n"])) for r in rows]


def pipeline_stats(conn: sqlite3.Connection) -> dict[str, Any]:
    """리포트 품질 지표의 원천 수치. 비율은 0 나눗셈을 막아 계산한다."""
    raw_total = count_rows(conn, "news_raw")
    raw_ok = count_rows(conn, "news_raw", "status = 'fetched'")
    clean_total = count_rows(conn, "news_clean")
    clean_ok = count_rows(conn, "news_clean", "status = 'clean'")
    summary_ok = count_rows(conn, "news_summary", "status = 'ok'")
    avg_row = conn.execute(
        "SELECT AVG(word_count) AS avg_wc FROM news_clean WHERE status = 'clean'"
    ).fetchone()

    def ratio(num: int, den: int) -> float:
        return round(num / den, 4) if den else 0.0

    return {
        "raw_total": raw_total,
        "raw_fetched": raw_ok,
        "clean_total": clean_total,
        "clean_ok": clean_ok,
        "summary_ok": summary_ok,
        "analysis_ok": count_rows(conn, "news_analysis", "status = 'ok'"),
        "fetch_success_rate": ratio(raw_ok, raw_total),
        "clean_rate": ratio(clean_total, raw_ok),
        "summary_coverage": ratio(summary_ok, clean_ok),
        "avg_word_count": round(float(avg_row["avg_wc"] or 0.0), 1),
    }
