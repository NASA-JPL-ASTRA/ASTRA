#!/usr/bin/env python3
"""
JPL ASTRA - Export Notes from Database
=====================================
Export valid transcription notes from SQLite, ordered by timestamp.
Skips filtered (noise/hallucination) entries - only exports tasks with non-empty transcript.

Usage:
  python export_notes.py [--db PATH] [--output FILE] [--format md|txt] [--by-segment]
  python export_notes.py --date 2024-02-18 -o notes_20240218.md   # 导出某一天的笔记
  python export_notes.py --from 2024-02-18 --to 2024-02-20 -o notes_range.md  # 导出日期范围

Time filter:
  - --date YYYY-MM-DD: export only notes from that day
  - --from YYYY-MM-DD: start date (inclusive)
  - --to YYYY-MM-DD: end date (inclusive)
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path


def load_notes(
    db_path: str,
    by_segment: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """
    Load completed tasks with non-empty transcript from SQLite.
    date_from/date_to: YYYY-MM-DD, filter by created_at date.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = "SELECT id, created_at, updated_at, result FROM tasks WHERE status = 'completed' AND result IS NOT NULL"
    params: list = []
    if date_from:
        sql += " AND date(created_at) >= date(?)"
        params.append(date_from)
    if date_to:
        sql += " AND date(created_at) <= date(?)"
        params.append(date_to)
    sql += " ORDER BY created_at ASC"

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    notes = []
    for row in rows:
        try:
            result = json.loads(row["result"]) if isinstance(row["result"], str) else row["result"]
        except (TypeError, json.JSONDecodeError):
            continue

        text = (result.get("text") or "").strip()
        if not text:
            continue  # Skip filtered/noise entries
        if result.get("filtered"):
            continue  # Skip explicitly filtered

        ts = row["created_at"] or row["updated_at"]
        if not ts:
            continue

        if by_segment:
            segments = result.get("segments") or []
            for seg in segments:
                seg_text = (seg.get("text") or "").strip()
                if not seg_text:
                    continue
                start = seg.get("start") or 0
                # Approximate absolute time: created_at + segment start
                try:
                    base = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    seg_ts = (base + timedelta(seconds=start)).isoformat()
                except Exception:
                    seg_ts = ts
                notes.append({"timestamp": seg_ts, "text": seg_text, "task_id": row["id"]})
        else:
            notes.append({"timestamp": ts, "text": text, "task_id": row["id"]})

    return notes


def export_markdown(notes: list[dict], out_path: Path) -> None:
    """Export notes as Markdown with timestamps."""
    lines = ["# ASTRA Transcription Notes\n", f"*Exported: {datetime.now().isoformat()}*\n"]
    for n in notes:
        lines.append(f"## {n['timestamp']}\n\n")
        lines.append(f"{n['text']}\n\n")
    out_path.write_text("".join(lines), encoding="utf-8")


def export_txt(notes: list[dict], out_path: Path) -> None:
    """Export notes as plain text with timestamps."""
    lines = [f"[{n['timestamp']}] {n['text']}\n" for n in notes]
    out_path.write_text("".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export transcription notes from SQLite")
    parser.add_argument(
        "--db", default="WhisperServiceAPI.db",
        help="SQLite database path (default: WhisperServiceAPI.db)"
    )
    parser.add_argument(
        "--output", "-o", default="notes_export.md",
        help="Output file path (default: notes_export.md)"
    )
    parser.add_argument(
        "--format", "-f", choices=["md", "txt"], default="md",
        help="Output format: md (Markdown) or txt (default: md)"
    )
    parser.add_argument(
        "--by-segment", action="store_true",
        help="One timestamp per segment (一句一个); default is one per task (每次完整语音任务)"
    )
    parser.add_argument(
        "--date", metavar="YYYY-MM-DD",
        help="Export only notes from this date (e.g. 2024-02-18)"
    )
    parser.add_argument(
        "--from", dest="date_from", metavar="YYYY-MM-DD",
        help="Start date (inclusive)"
    )
    parser.add_argument(
        "--to", dest="date_to", metavar="YYYY-MM-DD",
        help="End date (inclusive)"
    )
    args = parser.parse_args()

    date_from = args.date_from
    date_to = args.date_to
    if args.date:
        date_from = date_to = args.date

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    notes = load_notes(
        str(db_path),
        by_segment=args.by_segment,
        date_from=date_from,
        date_to=date_to,
    )
    if not notes:
        range_hint = f" (date filter: {date_from or '?'} to {date_to or '?'})" if (date_from or date_to) else ""
        print(f"No valid notes found{range_hint}.")
        return

    out_path = Path(args.output)
    if args.format == "md":
        export_markdown(notes, out_path)
    else:
        export_txt(notes, out_path)

    if date_from and date_to and date_from == date_to:
        range_info = f" ({date_from})"
    elif date_from and date_to:
        range_info = f" ({date_from} to {date_to})"
    elif date_from:
        range_info = f" (from {date_from})"
    elif date_to:
        range_info = f" (to {date_to})"
    else:
        range_info = ""
    print(f"Exported {len(notes)} note(s){range_info} to {out_path}")


if __name__ == "__main__":
    main()
