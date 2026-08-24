"""Validate that project notebooks are well-formed JSON with executable cells.

These notebooks run on Databricks (Spark + Unity Catalog). GitHub Actions
cannot execute them, so this check only catches corruption / empty notebooks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_GLOBS = ("ingestion/*.ipynb", "model-eval/*.ipynb", "insights/*.ipynb")


def main() -> int:
    paths = []
    for pattern in NOTEBOOK_GLOBS:
        paths.extend(sorted(ROOT.glob(pattern)))

    if not paths:
        print("FAIL: no notebooks found")
        return 1

    failed = 0
    for path in paths:
        rel = path.relative_to(ROOT)
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"FAIL  {rel} — invalid JSON ({exc})")
            failed += 1
            continue

        cells = notebook.get("cells")
        if not isinstance(cells, list) or not cells:
            print(f"FAIL  {rel} — no cells")
            failed += 1
            continue

        code_cells = [
            cell
            for cell in cells
            if cell.get("cell_type") == "code" and "".join(cell.get("source") or []).strip()
        ]
        if not code_cells:
            print(f"FAIL  {rel} — no non-empty code cells")
            failed += 1
            continue

        print(f"PASS  {rel} — {len(cells)} cells ({len(code_cells)} code)")

    print(f"\n{len(paths) - failed}/{len(paths)} notebooks valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
