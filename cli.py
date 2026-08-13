"""Dvir Token Manager - CLI entrypoint."""
from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

from token_dashboard.db import init_db, default_db_path, overview_totals
from token_dashboard.scanner import scan_dir
from token_dashboard.tips import all_tips


# Ensure UTF-8 output on Windows consoles for Hebrew text
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


PRODUCT = "מנהל הטוקנים"


def _db_path(args) -> str:
    return args.db or os.environ.get("TOKEN_DASHBOARD_DB") or str(default_db_path())


def _projects(args) -> str:
    return (
        args.projects_dir
        or os.environ.get("CLAUDE_PROJECTS_DIR")
        or str(Path.home() / ".claude" / "projects")
    )


def _today_range():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).isoformat()
    end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    return start, end


def cmd_scan(args):
    db = _db_path(args)
    init_db(db)
    n = scan_dir(_projects(args), db)
    print(f"{PRODUCT}: נסרקו {n['files']} קבצים, {n['messages']} הודעות, {n['tools']} קריאות לכלים")


def cmd_today(args):
    db = _db_path(args)
    init_db(db)
    s, e = _today_range()
    t = overview_totals(db, since=s, until=e)
    print(f"{PRODUCT} — היום")
    print(f"  שיחות: {t['sessions']}    פניות: {t['turns']}")
    print(f"  קלט:    {t['input_tokens']:>12,}    פלט: {t['output_tokens']:>12,}")
    print(f"  קריאת זיכרון: {t['cache_read_tokens']:>12,}    כתיבת זיכרון: {t['cache_create_5m_tokens']+t['cache_create_1h_tokens']:>12,}")


def cmd_stats(args):
    db = _db_path(args)
    init_db(db)
    t = overview_totals(db)
    print(f"{PRODUCT} — מאז ומתמיד")
    print(f"  שיחות: {t['sessions']}    פניות: {t['turns']}")
    print(f"  קלט:    {t['input_tokens']:>12,}    פלט: {t['output_tokens']:>12,}")


def cmd_tips(args):
    db = _db_path(args)
    init_db(db)
    tips = all_tips(db)
    if not tips:
        print(f"{PRODUCT}: אין הצעות פעילות")
        return
    for tip in tips:
        print(f"[{tip['category']}] {tip['title']}")
        print(f"  {tip['body']}\n")


def cmd_dashboard(args):
    db = _db_path(args)
    init_db(db)
    if not args.no_scan:
        scan_dir(_projects(args), db)
    from token_dashboard.server import run

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    url = f"http://{host}:{port}/"
    if not args.no_open:
        webbrowser.open(url)
    print(f"{PRODUCT} מאזין בכתובת {url}")
    run(host, port, db, _projects(args))


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", help="נתיב SQLite (ברירת מחדל ~/.claude/token-dashboard.db)")
    common.add_argument("--projects-dir", help="תיקיית JSONL (ברירת מחדל ~/.claude/projects)")

    p = argparse.ArgumentParser(
        prog="dvir-token-manager",
        description=f"{PRODUCT} — לוח בקרה מקומי לשימוש בטוקנים של Claude Code",
        parents=[common],
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan",  parents=[common], help="סריקת קבצי JSONL חדשים").set_defaults(func=cmd_scan)
    sub.add_parser("today", parents=[common], help="סיכום של היום").set_defaults(func=cmd_today)
    sub.add_parser("stats", parents=[common], help="סיכום מאז ומתמיד").set_defaults(func=cmd_stats)
    sub.add_parser("tips",  parents=[common], help="הצגת טיפים לחיסכון").set_defaults(func=cmd_tips)
    d = sub.add_parser("dashboard", parents=[common], help="הפעלת לוח הבקרה ב-127.0.0.1:8080")
    d.add_argument("--no-scan", action="store_true", help="דילוג על סריקה לפני הפעלה")
    d.add_argument("--no-open", action="store_true", help="לא לפתוח דפדפן אוטומטית")
    d.set_defaults(func=cmd_dashboard)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
