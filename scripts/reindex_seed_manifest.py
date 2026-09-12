from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

BACKEND_DIR = (
    PROJECT_ROOT
    / "backend"
)

MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "demo_seed_manifest.json"
)

sys.path.insert(
    0,
    str(BACKEND_DIR),
)


from app.services.pinata_service import (  # noqa: E402
    download_from_ipfs,
)

from app.services.rag_service import (  # noqa: E402
    rag_service,
)


async def reindex(
    *,
    reset: bool,
    attempts: int,
) -> None:

    if not MANIFEST_PATH.exists():
        raise SystemExit(
            (
                "Manifest not found: "
                f"{MANIFEST_PATH}"
            )
        )

    data = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    records = [
        item
        for item in data.get(
            "records",
            [],
        )
        if (
            item.get("status")
            == "success"
            and item.get(
                "record_hash"
            )
            and item.get(
                "ipfs_cid"
            )
        )
    ]

    if reset:
        print(
            (
                "Resetting Chroma collection "
                "because --reset was supplied..."
            )
        )

        rag_service.clear_index()

    indexed = 0
    skipped = 0
    failed = 0

    for index, item in enumerate(
        records,
        start=1,
    ):
        record_hash = str(
            item[
                "record_hash"
            ]
        )

        cid = str(
            item[
                "ipfs_cid"
            ]
        )

        prefix = (
            f"[{index:02d}/"
            f"{len(records):02d}] "
            f"{record_hash[:12]}..."
        )

        try:
            #
            # Most important change:
            # do not redownload/reindex records that
            # already succeeded on an earlier run.
            #
            if rag_service.has_record(
                record_hash
            ):
                skipped += 1

                print(
                    (
                        f"{prefix} "
                        "already indexed - skipped"
                    )
                )

                continue

            #
            # Missing record:
            # retrieve it with retry/backoff.
            #
            content = (
                await download_from_ipfs(
                    cid,
                    max_attempts=(
                        attempts
                    ),
                )
            )

            rag_service.index_record(
                record_hash=(
                    record_hash
                ),
                pdf_content=(
                    content
                ),
            )

            indexed += 1

            print(
                f"{prefix} indexed"
            )

        except Exception as exc:
            failed += 1

            print(
                (
                    f"{prefix} "
                    f"FAILED: {exc}"
                )
            )

    print()

    print(
        (
            f"Indexed new: {indexed}; "
            f"skipped existing: {skipped}; "
            f"failed: {failed}"
        )
    )

    if failed:
        print()
        print(
            (
                "Some records are still unavailable. "
                "Run the same command again; "
                "successful records will be skipped "
                "and only missing records retried."
            )
        )

        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Resume/rebuild Chroma from seeded "
            "IPFS records. Existing records are "
            "skipped by default and gateway "
            "failures are retried."
        )
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Explicitly clear Chroma before "
            "reindexing. Do NOT use this for "
            "normal retry/resume runs."
        ),
    )

    parser.add_argument(
        "--attempts",
        type=int,
        default=5,
        help=(
            "Gateway attempts per missing CID "
            "(default: 5)."
        ),
    )

    args = parser.parse_args()

    if args.attempts <= 0:
        parser.error(
            (
                "--attempts must be "
                "greater than zero"
            )
        )

    asyncio.run(
        reindex(
            reset=args.reset,
            attempts=args.attempts,
        )
    )


if __name__ == "__main__":
    main()