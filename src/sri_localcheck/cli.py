"""CLI for a local build root and one root-relative HTML document."""

import argparse
import json
from pathlib import Path

from . import __version__
from .core import InputError, check


def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify local HTML SRI against local asset bytes")
    parser.add_argument("root", type=Path, help="stable build directory")
    parser.add_argument("document", type=Path, help="HTML path relative to the build root")
    parser.add_argument(
        "--require-integrity", action="store_true", help="also flag missing metadata"
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        result = check(args.root, args.document, require_integrity=args.require_integrity)
    except InputError as exc:
        result = {"schema": "sri-localcheck/v1", "status": "error", "code": str(exc)}
        status = 2
    else:
        status = 1 if result["failed"] else 0
    if args.json:
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    elif status == 2:
        print(f"error: {result['code']}")
    else:
        print(f"{result['status']}: {result['checked']} declarations, {result['failed']} failed")
        for row in result["checks"]:
            print(f"  line {row['line']} {row['element']}: {row['code']}")
    return status
