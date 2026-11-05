"""Command line interface; run --help for available operations."""

import argparse
import json
import sqlite3

from .core import audit, write_reports


def _audit(args):
    result = audit(args.directory, args.rules)
    write_reports(result, args.json, args.html)
    return result


def main():
    parser = argparse.ArgumentParser(description="configuration-auditor")
    commands = parser.add_subparsers(dest="command", required=True)
    sub = commands.add_parser("audit")
    sub.add_argument("directory")
    sub.add_argument("--rules", default="audit-rules.json")
    sub.add_argument("--json", default="report.json")
    sub.add_argument("--html", default="report.html")
    args = parser.parse_args()
    try:
        if args.command == "audit":
            result = _audit(args)
        print(
            json.dumps(result, ensure_ascii=False, indent=2)
            if not isinstance(result, str)
            else result
        )
        if isinstance(result, dict) and result.get("passed") is False:
            return 1
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(2, f"Ошибка: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
