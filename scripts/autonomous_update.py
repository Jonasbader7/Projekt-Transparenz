"""Daily local orchestration; existing source intervals and validation remain effective."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from transparenz.config.settings import local_data_dir
from transparenz.ingestion.external import atomic_json
from transparenz.services.swiss_foundation import foundation_lock

ROOT = Path(__file__).resolve().parents[1]
DATA = local_data_dir(ROOT)  # Datenordner (TRANSPARENZ_DATA_DIR, sonst data/)
FOLDER = DATA / "processed/automation"


def main() -> int:
    FOLDER.mkdir(parents=True, exist_ok=True)
    with foundation_lock(FOLDER):
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        results = []
        for name, command in (
            ("global_candidates", ["scripts/download_global_candidates.py"]),
            ("market", ["-m", "transparenz", "market-update"]),
            ("swiss", ["-m", "transparenz", "swiss-update"]),
        ):
            log = FOLDER / f"{stamp}_{name}.log"
            started = datetime.now(UTC).isoformat()
            atomic_json(
                FOLDER / "latest.json",
                {"status": "running", "started_at": started, "job": name, "results": results},
            )
            try:
                with log.open("w", encoding="utf-8") as handle:
                    process = subprocess.run(
                        [sys.executable, *command],
                        cwd=ROOT,
                        stdout=handle,
                        stderr=subprocess.STDOUT,
                        timeout=3 * 3600,
                        check=False,
                    )
                code, error = process.returncode, None
            except Exception as exc:
                code, error = 1, str(exc)
            results.append(
                {
                    "job": name,
                    "returncode": code,
                    "error": error,
                    "started_at": started,
                    "finished_at": datetime.now(UTC).isoformat(),
                    "log": str(log.relative_to(DATA)),
                }
            )
        failed = any(r["returncode"] for r in results)
        atomic_json(
            FOLDER / "latest.json",
            {
                "status": "failed" if failed else "success",
                "finished_at": datetime.now(UTC).isoformat(),
                "results": results,
            },
        )
        print(json.dumps({"failed": failed, "results": results}, ensure_ascii=False))
        return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
