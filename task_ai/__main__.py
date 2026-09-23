"""Run: python -m task_ai examples/ai_input.json --offline."""
import argparse
import json
import os
from pathlib import Path
import sys

from . import InputValidationError, analyze_task


def main():
    parser = argparse.ArgumentParser(description="AI Sana task clarification demo")
    parser.add_argument("input", type=Path, help="UTF-8 JSON: description and fields")
    parser.add_argument("--offline", action="store_true", help="Never call the API")
    parser.add_argument("--env-file", type=Path, help="Optional server .env file")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        if args.env_file:
            # Simple .env: no execution, expansion or interpolation.
            allowed = {"OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TIMEOUT_SECONDS"}
            for line in args.env_file.read_text(encoding="utf-8-sig").splitlines():
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                key, sep, value = line.partition("=")
                if not sep or key.strip() not in allowed:
                    raise ValueError("Unsupported entry in env file")
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                os.environ.setdefault(key.strip(), value)
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict) or set(payload) - {"description", "fields"}:
            raise InputValidationError("Expected an object with description and fields")
        result = analyze_task(payload.get("description", ""), payload.get("fields"), offline=args.offline)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError):
        print("Invalid input or unreadable file. Check the documented JSON/env format.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

