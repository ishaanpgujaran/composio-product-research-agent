"""
batch.py — Batch runner for the Composio product research pipeline.

Usage
-----
# Dry-run: first 3 apps, stdout pretty-print + write data/pass_1.json
python src/batch.py --dry-run

# Full batch: all 100 apps, concurrency=5, resumable
python src/batch.py

# Override concurrency or input file
python src/batch.py --concurrency 8
python src/batch.py --apps data/my_apps.json --out data/my_pass_1.json

Environment
-----------
GEMINI_API_KEY   required
COMPOSIO_API_KEY optional (falls back to Gemini grounding if absent)
BATCH_CONCURRENCY default 5 (overridden by --concurrency)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ── Ensure project root is on sys.path so 'src.*' resolves when run as a script ─
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.research import research_app, ResearchError  # noqa: E402

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT    = Path(__file__).resolve().parent.parent
_APPS    = _ROOT / "data" / "apps.json"
_PASS_1  = _ROOT / "data" / "pass_1.json"

# ── Logging: one clean line per app, no spam ──────────────────────────────────
logging.basicConfig(
    level=logging.WARNING,         # suppress research.py DEBUG chatter
    format="%(levelname)s %(message)s",
    stream=sys.stderr,
)
# Our own module gets INFO so progress lines appear on stderr without DEBUG noise
_log = logging.getLogger("batch")
_log.setLevel(logging.INFO)

# ── Dry-run app count ─────────────────────────────────────────────────────────
_DRY_RUN_N = 3


# ─────────────────────────────────────────────────────────────────────────────
# pass_1.json I/O  (newline-delimited JSON for append-safe incremental writes)
# ─────────────────────────────────────────────────────────────────────────────

def _load_completed(out_path: Path) -> dict[str, dict]:
    """
    Return {app_name: record} for every app already written to pass_1.json.
    Handles both newline-delimited JSON (NDJSON) and a JSON array.
    """
    completed: dict[str, dict] = {}
    if not out_path.exists() or out_path.stat().st_size == 0:
        return completed

    raw = out_path.read_text(encoding="utf-8").strip()
    if not raw:
        return completed

    # Try NDJSON first (our incremental write format)
    if raw.startswith("{"):
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                completed[rec["app_name"]] = rec
            except (json.JSONDecodeError, KeyError):
                pass
        return completed

    # Fall back to JSON array (e.g., from a previous full write)
    try:
        records = json.loads(raw)
        if isinstance(records, list):
            for rec in records:
                if isinstance(rec, dict) and "app_name" in rec:
                    completed[rec["app_name"]] = rec
    except json.JSONDecodeError:
        _log.warning("Could not parse %s — starting fresh", out_path)

    return completed


def _append_record(out_path: Path, record: dict) -> None:
    """
    Append one JSON record as a newline to pass_1.json.
    Thread-/async-safe because each write is a single atomic append.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# Stub record — written when research_app() raises ResearchError
# ─────────────────────────────────────────────────────────────────────────────

def _make_error_stub(app_name: str, category: str, error_msg: str) -> dict:
    """
    Minimal valid AppResearch dict for a failed app so the batch never stops.
    All substantive fields are 'Unknown'; human_review_required=True.
    """
    return {
        "app_name": app_name,
        "category": category,
        "description": "Research failed — see human_review_notes.",
        "auth_methods": ["Unknown"],
        "credential_acquisition": "Unknown",
        "self_serve_status": "Unknown",
        "api_type": ["Unknown"],
        "api_breadth": "Unknown",
        "api_documentation_url": None,
        "mcp_available": "Unknown",
        "mcp_official": "Unknown",
        "mcp_url": None,
        "buildability_verdict": "Unknown",
        "primary_blocker": f"Research pipeline error: {error_msg}",
        "evidence": [],
        "confidence": "Low",
        "human_review_required": True,
        "human_review_notes": f"BATCH ERROR: {error_msg}",
        "_error": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Per-app worker
# ─────────────────────────────────────────────────────────────────────────────

async def _research_one(
    app: dict,
    sem: asyncio.Semaphore,
    out_path: Path,
    idx: int,
    total: int,
    dry_run: bool,
) -> tuple[str, dict | None, str | None]:
    """
    Research a single app under the semaphore.

    Returns (app_name, record_or_None, error_msg_or_None).
    Always appends to out_path (result or stub).
    """
    # research_app and ResearchError are imported at module level

    app_name = app["app_name"]
    category = app.get("category", "Unknown")

    async with sem:
        _log.info("[%d/%d] Researching %s…", idx, total, app_name)
        t0 = time.monotonic()
        try:
            result      = await research_app(app_name, category)
            record      = json.loads(result.model_dump_json())
            elapsed     = time.monotonic() - t0
            review_flag = "⚑ review" if result.human_review_required else "✓"
            _log.info(
                "  ✓ %s [%s | %s | %.1fs] %s",
                app_name,
                result.confidence,
                result.buildability_verdict,
                elapsed,
                review_flag,
            )
            if dry_run:
                # Pretty-print to stdout for dry-run inspection
                print(f"\n{'─'*60}")
                print(f"  {app_name}  ({category})")
                print(f"{'─'*60}")
                print(result.model_dump_json(indent=2))
                sys.stdout.flush()

            _append_record(out_path, record)
            return app_name, record, None

        except ResearchError as exc:
            elapsed = time.monotonic() - t0
            _log.warning(
                "  ✗ %s [FAILED in %.1fs]: %s", app_name, elapsed, exc
            )
            stub = _make_error_stub(app_name, category, str(exc))
            _append_record(out_path, stub)
            return app_name, None, str(exc)

        except Exception as exc:
            elapsed = time.monotonic() - t0
            _log.warning(
                "  ✗ %s [UNEXPECTED ERROR in %.1fs]: %s", app_name, elapsed, exc
            )
            stub = _make_error_stub(app_name, category, f"Unexpected: {exc}")
            _append_record(out_path, stub)
            return app_name, None, f"Unexpected: {exc}"


# ─────────────────────────────────────────────────────────────────────────────
# Summary printer
# ─────────────────────────────────────────────────────────────────────────────

def _print_summary(
    results: list[tuple[str, dict | None, str | None]],
    elapsed_total: float,
    dry_run: bool,
) -> None:
    label = "DRY-RUN" if dry_run else "BATCH"
    succeeded   = [r for r in results if r[1] is not None]
    failed      = [r for r in results if r[2] is not None]
    review_apps = [
        r[0] for r in succeeded
        if r[1] and r[1].get("human_review_required")
    ]

    conf_counts: Counter = Counter(
        r[1].get("confidence", "Unknown")
        for r in succeeded
        if r[1]
    )
    verdict_counts: Counter = Counter(
        r[1].get("buildability_verdict", "Unknown")
        for r in succeeded
        if r[1]
    )

    divider = "═" * 60
    print(f"\n{divider}")
    print(f"  {label} SUMMARY  ({elapsed_total:.1f}s total)")
    print(divider)
    print(f"  Total researched : {len(results)}")
    print(f"  Succeeded        : {len(succeeded)}")
    print(f"  Failed (stub)    : {len(failed)}")
    print()
    print("  Confidence breakdown:")
    for level in ("High", "Medium", "Low"):
        count = conf_counts.get(level, 0)
        bar   = "█" * count
        print(f"    {level:8s}: {count:3d}  {bar}")
    print()
    print("  Buildability breakdown:")
    for verdict in ("Easy", "Possible", "Difficult", "Blocked", "Unknown"):
        count = verdict_counts.get(verdict, 0)
        if count:
            print(f"    {verdict:12s}: {count}")
    print()
    print(f"  Human review required: {len(review_apps)} app(s)")
    for name in review_apps:
        print(f"    • {name}")
    if failed:
        print()
        print(f"  Errors ({len(failed)}):")
        for name, _, err in failed:
            print(f"    ✗ {name}: {err}")
    print(divider)


# ─────────────────────────────────────────────────────────────────────────────
# Main batch runner
# ─────────────────────────────────────────────────────────────────────────────

async def run_batch(
    apps_path: Path,
    out_path: Path,
    concurrency: int,
    dry_run: bool,
) -> None:
    # ── Load app list ─────────────────────────────────────────────────────────
    if not apps_path.exists():
        print(f"ERROR: {apps_path} not found. Paste your app list first.", file=sys.stderr)
        sys.exit(1)

    all_apps: list[dict] = json.loads(apps_path.read_text(encoding="utf-8"))
    if dry_run:
        all_apps = all_apps[:_DRY_RUN_N]
        _log.info("DRY-RUN: processing first %d apps", _DRY_RUN_N)

    total = len(all_apps)

    # ── Resumability: skip already-completed apps ─────────────────────────────
    completed = _load_completed(out_path)
    if completed:
        _log.info(
            "Resuming: %d apps already in %s — skipping them",
            len(completed), out_path.name,
        )

    todo = [a for a in all_apps if a["app_name"] not in completed]
    if not todo:
        print(f"All {total} apps already in {out_path}. Nothing to do.")
        return

    skipped = total - len(todo)
    if skipped:
        _log.info("Skipping %d already-researched apps.", skipped)

    # ── Validate env ──────────────────────────────────────────────────────────
    if not os.getenv("GEMINI_API_KEY"):
        print(
            "ERROR: GEMINI_API_KEY is not set.\n"
            "  → cp .env.example .env  and fill in your key.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Semaphore + progress tracking ─────────────────────────────────────────
    sem             = asyncio.Semaphore(concurrency if not dry_run else 1)
    processed_count = 0
    results: list[tuple[str, dict | None, str | None]] = []

    # Preserve already-skipped apps in results for the summary
    for name, rec in completed.items():
        results.append((name, rec, None))

    t_start = time.monotonic()

    # Progress callback every 10 apps (full batch only)
    def _on_done(app_name: str, record: dict | None, err: str | None) -> None:
        nonlocal processed_count
        processed_count += 1
        if not dry_run and processed_count % 10 == 0:
            done_so_far = len(completed) + processed_count
            _log.info("[%d/%d] checkpoint reached", done_so_far, total)

    # ── Fire tasks ────────────────────────────────────────────────────────────
    tasks = [
        _research_one(
            app=app,
            sem=sem,
            out_path=out_path,
            idx=len(completed) + i + 1,
            total=total,
            dry_run=dry_run,
        )
        for i, app in enumerate(todo)
    ]

    # Run concurrently; gather preserves order for summary
    raw_results = await asyncio.gather(*tasks, return_exceptions=False)

    for r in raw_results:
        results.append(r)
        _on_done(*r)

    elapsed = time.monotonic() - t_start
    _print_summary(results, elapsed, dry_run)

    if not dry_run:
        # Rewrite pass_1.json as a clean JSON array at the end of a full batch
        # so downstream scripts (verify.py, analyze.py) can json.load() it easily.
        all_records = list(_load_completed(out_path).values())
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(all_records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(out_path)
        _log.info("pass_1.json rewritten as JSON array (%d records).", len(all_records))


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Composio product research batch runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help=f"Research only the first {_DRY_RUN_N} apps and pretty-print to stdout.",
    )
    p.add_argument(
        "--apps",
        type=Path,
        default=_APPS,
        metavar="PATH",
        help=f"Input JSON file (default: {_APPS})",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=_PASS_1,
        metavar="PATH",
        help=f"Output NDJSON file (default: {_PASS_1})",
    )
    p.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("BATCH_CONCURRENCY", "5")),
        metavar="N",
        help="Max concurrent research tasks (default: 5 or BATCH_CONCURRENCY env var)",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    mode = "DRY-RUN" if args.dry_run else f"FULL BATCH (concurrency={args.concurrency})"
    print(f"\n{'═'*60}")
    print(f"  Composio Research Pipeline — {mode}")
    print(f"  apps  : {args.apps}")
    print(f"  output: {args.out}")
    print(f"{'═'*60}\n")

    asyncio.run(
        run_batch(
            apps_path=args.apps,
            out_path=args.out,
            concurrency=args.concurrency,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
