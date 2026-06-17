"""Исправляет битые телефоны в data_backup.json перед loaddata."""
import json
import re
import sys
from pathlib import Path

PHONE_RE = re.compile(r"^\+\d-\d{3}-\d{3}-\d{2}-\d{2}$")
FALLBACK = "+7-000-000-00-00"


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data_backup.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0
    for obj in data:
        if obj.get("model") != "accounts.user":
            continue
        phone = (obj.get("fields") or {}).get("phone") or ""
        if not PHONE_RE.match(phone):
            obj["fields"]["phone"] = FALLBACK
            fixed += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Sanitized {fixed} user phone(s) in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
