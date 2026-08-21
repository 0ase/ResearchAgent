"""Export the FastAPI OpenAPI document without starting the server."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web" / "openapi.json"


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from backend.main import create_app

    schema = create_app().openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Exported OpenAPI schema to {OUTPUT}")


if __name__ == "__main__":
    main()
