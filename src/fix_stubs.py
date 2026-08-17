"""
Script to target only the stubbed/failed records in data/pass_1.json,
re-run research for them using a model with active quota (gemini-3.5-flash),
and replace their stub entries in data/pass_1.json with clean results.
"""

import sys
import json
import asyncio
import logging
from pathlib import Path

# Add project root to sys.path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.research import research_app, ResearchError
from src.schema import AppResearch

_PASS_1 = _ROOT / "data" / "pass_1.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("fix_stubs")

async def main():
    if not _PASS_1.exists():
        logger.error("pass_1.json does not exist!")
        return

    # Read existing records
    records = []
    with open(_PASS_1, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    # Identify stubs
    stubs = [r for r in records if r.get("_error")]
    clean_records = {r["app_name"]: r for r in records if not r.get("_error")}

    logger.info("Found %d total records (%d clean, %d stubs)", len(records), len(clean_records), len(stubs))

    if not stubs:
        logger.info("No stubs found to fix.")
        return

    print("\n" + "=" * 60)
    print(f"  FIXING {len(stubs)} STUBBED APPS (using gemini-3.5-flash)")
    print("=" * 60)

    fixed_count = 0
    for stub in stubs:
        app_name = stub["app_name"]
        category = stub.get("category", "Unknown")
        print(f"\n--> Re-running research for: {app_name} ({category})")
        
        try:
            res: AppResearch = await research_app(app_name, category)
            res_dict = res.model_dump(mode="json")
            clean_records[app_name] = res_dict
            fixed_count += 1
            print(f"  ✓ SUCCESS for {app_name} [confidence={res.confidence}, verdict={res.buildability_verdict}]")
        except Exception as exc:
            logger.error("  ✗ Still failed for %s: %s", app_name, exc)

        # Pause to prevent rate limit spikes between stub retries
        await asyncio.sleep(12)

    # Rewrite pass_1.json maintaining original order as much as possible
    new_records = []
    seen = set()
    for r in records:
        app_name = r["app_name"]
        if app_name in seen:
            continue
        seen.add(app_name)
        if app_name in clean_records:
            new_records.append(clean_records[app_name])
        else:
            new_records.append(r)

    with open(_PASS_1, "w", encoding="utf-8") as f:
        for r in new_records:
            f.write(json.dumps(r) + "\n")

    print("\n" + "=" * 60)
    print(f"  STUB REPAIR COMPLETE: {fixed_count}/{len(stubs)} stubs repaired.")
    print(f"  pass_1.json now contains {len(new_records)} records.")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
