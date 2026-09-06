#!/usr/bin/env python3
"""AI타임스 뉴스 파이프라인 — CLI 진입점.

사용 예:
    python main.py --help
    python main.py initdb
    python main.py fetch --source aitimes --method rss --limit 20
    python main.py clean --limit 20
    python main.py summarize --unsummarized --limit 20
    python main.py analyze --limit 50
    python main.py report --top-n 10 --format md
    python main.py export --formats csv,jsonl

각 서브커맨드는 담당 모듈 함수를 호출만 한다(디스패처).
아직 구현되지 않은 단계는 크래시 대신 "무엇을 어느 파일에 구현해야 하는지"를
안내하고 종료 코드 2 로 끝난다.
"""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, Callable

from src.utils.config import load_config
from src.utils.logging_setup import setup_logging

logger = logging.getLogger("main")

DEFAULT_CONFIG = "config/config.json"

# 서브커맨드 → (담당 워크스트림, 구현해야 할 파일)
OWNERSHIP: dict[str, tuple[str, str]] = {
    "fetch": ("Collect/Clean", "src/collectors/rss.py, src/collectors/crawl.py"),
    "clean": ("Collect/Clean", "src/cleaners/cleaner.py"),
    "summarize": ("Summarize/Analyze", "src/ai/summarizer.py"),
    "analyze": ("Summarize/Analyze", "src/ai/analyzer.py"),
    "report": ("Lead/Report", "src/report/reporter.py, src/report/charts.py"),
    "export": ("Lead/Report", "src/report/exporter.py"),
}


# ---------------------------------------------------------------- 서브커맨드

def cmd_initdb(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """SQLite 스키마(4테이블)를 생성한다."""
    from src.storage import db

    db_path = _db_path(config)
    db.init_db(db_path)
    with db.get_connection(db_path) as conn:
        stats = db.pipeline_stats(conn)
    logger.info("현재 적재 상태: %s", stats)
    return 0


def cmd_fetch(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """RSS 또는 크롤링으로 기사를 수집해 news_raw 에 저장한다."""
    from src.collectors.crawl import CrawlCollector
    from src.collectors.rss import RSSCollector
    from src.storage import db

    db_path = _db_path(config)
    db.init_db(db_path)

    collector_cls = RSSCollector if args.method == "rss" else CrawlCollector
    collector = collector_cls(config, source=args.source)
    logger.info("수집 시작: source=%s method=%s limit=%s", args.source, args.method, args.limit)

    rows = collector.fetch(limit=args.limit, max_pages=args.max_pages)

    if args.dry_run:
        logger.info("dry-run: %d건 수집(저장하지 않음)", len(rows))
        return 0

    policy = config.get("duplicate_policy", "skip")
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    with db.get_connection(db_path) as conn:
        for row in rows:
            row.setdefault("source", args.source)
            row.setdefault("method", args.method)
            counts[db.upsert_raw(conn, row, policy)] += 1

    logger.info(
        "수집 완료: 신규 %d건, 갱신 %d건, 중복 스킵 %d건 (policy=%s)",
        counts["inserted"], counts["updated"], counts["skipped"], policy,
    )
    return 0


def cmd_clean(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """news_raw → news_clean 정제."""
    from src.cleaners.cleaner import clean_articles

    processed = clean_articles(
        db_path=_db_path(config),
        source=args.source,
        limit=args.limit,
        force=args.force,
        config=config,
    )
    logger.info("정제 완료: %s건", processed)
    return 0


def cmd_summarize(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """AI 요약 → news_summary."""
    from src.ai.summarizer import run_summarize

    done = run_summarize(
        db_path=_db_path(config),
        limit=args.limit,
        clean_id=args.clean_id,
        unsummarized=not args.all,
        config=config,
    )
    logger.info("요약 완료: %s건", done)
    return 0


def cmd_analyze(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """AI 인사이트 분석 → news_analysis."""
    from src.ai.analyzer import run_analyze

    ok = run_analyze(
        db_path=_db_path(config),
        limit=args.limit,
        since=args.since,
        category=args.category,
        config=config,
    )
    logger.info("분석 %s", "완료" if ok else "실패")
    return 0 if ok else 1


def cmd_report(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """차트 PNG + 품질 지표/TOP N/인사이트 리포트 생성."""
    from src.report.charts import make_charts
    from src.report.reporter import write_report

    db_path = _db_path(config)
    paths = config.get("paths", {})
    charts = make_charts(db_path, paths.get("charts_dir", "outputs/charts"), config=config)
    logger.info("차트 %d개 생성: %s", len(charts), charts)

    report_path = write_report(
        db_path,
        paths.get("reports_dir", "outputs/reports"),
        top_n=args.top_n if args.top_n is not None else config.get("report", {}).get("top_n", 10),
        fmt=args.format or config.get("report", {}).get("default_format", "md"),
        config=config,
    )
    logger.info("리포트 저장: %s", report_path)
    return 0


def cmd_export(args: argparse.Namespace, config: dict[str, Any]) -> int:
    """news_clean(+summary) 을 CSV/JSONL/Excel 로 내보낸다."""
    from src.report.exporter import export_data

    formats = (
        [f.strip() for f in args.formats.split(",") if f.strip()]
        if args.formats
        else config.get("export", {}).get("default_formats", ["csv", "jsonl"])
    )
    files = export_data(
        _db_path(config),
        args.out or "outputs",
        formats=formats,
        status=args.status,
        config=config,
    )
    logger.info("내보내기 완료 %d개: %s", len(files), files)
    return 0


# -------------------------------------------------------------------- 유틸

def _db_path(config: dict[str, Any]) -> str:
    return config.get("paths", {}).get("db", "data/pipeline.db")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="AI타임스 뉴스 수집·정제·AI 요약·분석·리포트 파이프라인 (CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "전체 흐름 예시:\n"
            "  python main.py fetch --method rss --limit 20\n"
            "  python main.py clean --limit 20\n"
            "  python main.py summarize --unsummarized --limit 20\n"
            "  python main.py analyze --limit 50\n"
            "  python main.py report --top-n 10 --format md\n"
            "  python main.py export --formats csv,jsonl\n"
        ),
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"설정 파일 경로 (기본: {DEFAULT_CONFIG})")
    parser.add_argument("-v", "--verbose", action="store_true", help="DEBUG 로그 출력")

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_init = sub.add_parser("initdb", help="SQLite 스키마 생성 / 적재 현황 출력")
    p_init.set_defaults(func=cmd_initdb)

    p_fetch = sub.add_parser("fetch", help="뉴스 수집 (RSS 또는 크롤링) → news_raw")
    p_fetch.add_argument("--source", default="aitimes", help="config.sources 의 키 (기본: aitimes)")
    p_fetch.add_argument("--method", choices=["rss", "crawl"], default="rss", help="수집 방식")
    p_fetch.add_argument("--limit", type=int, default=20, help="최대 수집 건수")
    p_fetch.add_argument("--max-pages", type=int, default=None, help="크롤링 시 최대 페이지 수")
    p_fetch.add_argument("--dry-run", action="store_true", help="DB에 쓰지 않고 결과 건수만 출력")
    p_fetch.set_defaults(func=cmd_fetch)

    p_clean = sub.add_parser("clean", help="raw → clean 정제 (HTML 제거·정규화·중복 처리)")
    p_clean.add_argument("--source", default=None, help="특정 소스만 정제")
    p_clean.add_argument("--limit", type=int, default=None, help="최대 처리 건수")
    p_clean.add_argument("--force", action="store_true", help="이미 정제된 기사도 다시 처리")
    p_clean.set_defaults(func=cmd_clean)

    p_sum = sub.add_parser("summarize", help="AI 요약 → news_summary")
    group = p_sum.add_mutually_exclusive_group()
    group.add_argument("--unsummarized", action="store_true", default=True, help="미요약 기사만 (기본)")
    group.add_argument("--all", action="store_true", help="이미 요약된 기사도 다시 요약")
    p_sum.add_argument("--id", "--clean-id", dest="clean_id", type=int, default=None, help="특정 clean id 만 요약")
    p_sum.add_argument("--limit", type=int, default=20, help="최대 요약 건수")
    p_sum.set_defaults(func=cmd_summarize)

    p_an = sub.add_parser("analyze", help="AI 인사이트 분석 → news_analysis")
    p_an.add_argument("--limit", type=int, default=50, help="분석에 사용할 기사 수")
    p_an.add_argument("--since", default=None, help="시작일 (YYYY-MM-DD)")
    p_an.add_argument("--category", default=None, help="카테고리 필터")
    p_an.set_defaults(func=cmd_analyze)

    p_rep = sub.add_parser("report", help="차트 PNG + 품질지표/TOP N/인사이트 리포트")
    p_rep.add_argument("--top-n", type=int, default=None, help="TOP N 기사 수")
    p_rep.add_argument("--format", choices=["txt", "md", "both"], default=None, help="리포트 형식")
    p_rep.set_defaults(func=cmd_report)

    p_exp = sub.add_parser("export", help="CSV/JSONL/Excel 내보내기")
    p_exp.add_argument("--formats", default=None, help="쉼표 구분 (예: csv,jsonl,xlsx)")
    p_exp.add_argument("--status", default=None, choices=["summarized", "unsummarized", "clean"],
                       help="내보낼 대상 필터 (예: summarized)")
    p_exp.add_argument("--out", default=None, help="출력 디렉터리 (기본: outputs)")
    p_exp.set_defaults(func=cmd_export)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(
            f"[ERROR] 설정 파일이 없습니다: {args.config}\n"
            f"        cp config/config.example.json {args.config} 로 먼저 만들어 주세요.",
            file=sys.stderr,
        )
        return 2

    setup_logging(config, verbose=args.verbose)

    func: Callable[[argparse.Namespace, dict[str, Any]], int] = args.func
    try:
        return func(args, config)
    except NotImplementedError as exc:
        owner, files = OWNERSHIP.get(args.command, ("미지정", "-"))
        logger.error("`%s` 는 아직 구현되지 않았습니다: %s", args.command, exc)
        logger.error("담당 워크스트림: %s / 구현 대상: %s", owner, files)
        logger.error("할 일 상세: docs/roles/ 아래 해당 역할 문서를 확인하세요.")
        return 2
    except KeyboardInterrupt:
        logger.warning("사용자 중단")
        return 130
    except Exception:  # noqa: BLE001 - CLI 최상단에서 traceback 을 로그로 남긴다
        logger.exception("`%s` 실행 중 오류", args.command)
        return 1


if __name__ == "__main__":
    sys.exit(main())
