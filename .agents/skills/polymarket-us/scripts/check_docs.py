#!/usr/bin/env python3
from __future__ import annotations

import json

from pmus_core.docs_check import check_required_docs
from pmus_core.output import failure


def main() -> int:
    try:
        result = check_required_docs()
    except Exception as exc:
        print(json.dumps(failure("docs-check", exc.__class__.__name__, str(exc)), separators=(",", ":"), sort_keys=True))
        return 1
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
