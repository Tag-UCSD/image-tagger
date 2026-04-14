"""
Canonical Science Pipeline Backfill Script
==========================================

Processes images through the canonical science pipeline in batches.
Runs in-process (not via the API) so it can be executed directly
inside the container or locally with a DB connection.

Usage (inside container):
    python -m backend.scripts.backfill_science_runs
    python -m backend.scripts.backfill_science_runs --batch 50 --limit 1000
    python -m backend.scripts.backfill_science_runs --ids 2 3 4 5
    python -m backend.scripts.backfill_science_runs --id-range 100 200
    python -m backend.scripts.backfill_science_runs --retry-failed
    python -m backend.scripts.backfill_science_runs --status

Options:
    --batch N        Images to process per DB commit cycle (default: 20)
    --limit N        Max images to queue in this run (default: unlimited)
    --ids ID ...     Process specific image IDs only
    --id-range START END  Process IDs in [START, END] inclusive
    --retry-failed   Re-queue FAILED runs before processing
    --status         Print pipeline status and exit
    --dry-run        Queue runs but do not execute; useful with --status
"""

from __future__ import annotations

import argparse
import logging
import time

from backend.database.core import SessionLocal
from backend.models.science_runs import ScienceRun
from backend.science.pipeline import SciencePipeline, SciencePipelineConfig
from backend.services.science_runs import (
    ACTIVE_SCIENCE_VERSION,
    CANONICAL_CONFIG,
    ensure_science_run,
    get_config_fingerprint,
    get_science_status,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backfill")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_status(db) -> None:
    s = get_science_status(db)
    total = s["total_images"]
    completed = s["current_completed"]
    pct = (completed / total * 100) if total else 0
    print(f"""
Science Pipeline Status  [{ACTIVE_SCIENCE_VERSION}]
─────────────────────────────────────────
  Completed : {completed:>6,}  ({pct:.1f}%)
  Pending   : {s['pending']:>6,}
  Running   : {s['running']:>6,}
  Failed    : {s['failed']:>6,}
  Total     : {total:>6,}
""")


def _reset_failed_runs(db) -> int:
    """Reset FAILED runs to PENDING so they are retried."""
    version = ACTIVE_SCIENCE_VERSION
    fingerprint = get_config_fingerprint(CANONICAL_CONFIG)
    rows = (
        db.query(ScienceRun)
        .filter(
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
            ScienceRun.status == "FAILED",
        )
        .all()
    )
    for run in rows:
        run.status = "PENDING"
        run.error_message = None
        run.started_at = None
        db.add(run)
    db.commit()
    return len(rows)


def _pending_run_ids(db, limit: int | None) -> list[int]:
    """Return IDs of PENDING science runs, optionally capped."""
    version = ACTIVE_SCIENCE_VERSION
    fingerprint = get_config_fingerprint(CANONICAL_CONFIG)
    q = (
        db.query(ScienceRun.image_id)
        .filter(
            ScienceRun.science_version == version,
            ScienceRun.config_fingerprint == fingerprint,
            ScienceRun.status == "PENDING",
        )
        .order_by(ScienceRun.image_id)
    )
    if limit is not None:
        q = q.limit(limit)
    return [row[0] for row in q.all()]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill canonical science pipeline runs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--batch", type=int, default=20, metavar="N",
                        help="Images processed per pipeline cycle (default: 20)")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Max images to process in this invocation")
    parser.add_argument("--ids", type=int, nargs="+", metavar="ID",
                        help="Process only these specific image IDs")
    parser.add_argument("--id-range", type=int, nargs=2, metavar=("START", "END"),
                        help="Process IDs in [START, END] inclusive")
    parser.add_argument("--retry-failed", action="store_true",
                        help="Reset FAILED runs to PENDING before processing")
    parser.add_argument("--status", action="store_true",
                        help="Print status and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Queue runs but do not execute the pipeline")
    args = parser.parse_args()

    db = SessionLocal()

    try:
        if args.status:
            _print_status(db)
            return

        # ── 1. Optionally reset failures ──────────────────────────────────
        if args.retry_failed:
            n = _reset_failed_runs(db)
            logger.info("Reset %d FAILED → PENDING.", n)

        # ── 2. Resolve target image IDs ───────────────────────────────────
        explicit_ids: list[int] | None = None
        if args.ids:
            explicit_ids = list(args.ids)
        elif args.id_range:
            start, end = args.id_range
            explicit_ids = list(range(start, end + 1))

        if explicit_ids is not None:
            logger.info("Explicit target: %d images.", len(explicit_ids))
            for image_id in explicit_ids:
                ensure_science_run(db, image_id, trigger_source="backfill_script")
            db.commit()

        # ── 3. Collect PENDING runs ───────────────────────────────────────
        image_ids = _pending_run_ids(db, limit=args.limit)
        logger.info(
            "Found %d PENDING runs (limit=%s).",
            len(image_ids), args.limit or "none",
        )

        if not image_ids:
            logger.info("Nothing to process.")
            _print_status(db)
            return

        if args.dry_run:
            logger.info("--dry-run: skipping pipeline execution.")
            _print_status(db)
            return

        # ── 4. Run the pipeline ───────────────────────────────────────────
        cfg = SciencePipelineConfig.from_mapping(CANONICAL_CONFIG)
        cfg.enable_affordance = False  # runs unconditionally inside canonical method

        pipeline = SciencePipeline(db=db, config=cfg)

        total = len(image_ids)
        ok = failed = 0
        t0 = time.monotonic()

        for i, image_id in enumerate(image_ids, 1):
            success = pipeline.process_image_canonical(
                image_id=image_id,
                trigger_source="backfill_script",
            )
            if success:
                ok += 1
            else:
                failed += 1

            # Progress report every batch images
            if i % args.batch == 0 or i == total:
                elapsed = time.monotonic() - t0
                rate = i / elapsed if elapsed > 0 else 0
                eta_s = (total - i) / rate if rate > 0 else 0
                logger.info(
                    "[%d/%d]  ok=%d  failed=%d  rate=%.1f/min  eta=%s",
                    i, total, ok, failed,
                    rate * 60,
                    f"{eta_s/60:.0f}m" if eta_s > 60 else f"{eta_s:.0f}s",
                )

        # ── 5. Final summary ──────────────────────────────────────────────
        elapsed = time.monotonic() - t0
        logger.info(
            "Done. %d succeeded, %d failed in %.1fs (%.1f/min).",
            ok, failed, elapsed, ok / elapsed * 60 if elapsed > 0 else 0,
        )
        _print_status(db)

    finally:
        db.close()


if __name__ == "__main__":
    main()
