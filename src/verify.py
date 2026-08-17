"""
src/verify.py — Stratified sampling, interactive verification CLI, and accuracy calculation.

Usage
-----
# 1. Generate 20-app stratified verification sample from pass_1.json
python -m src.verify --sample

# 2. Interactive CLI flow to record ground truth and error taxonomy
python -m src.verify --run

# 3. Compute and print accuracy metrics from ground_truth.json
python -m src.verify --accuracy
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
_PASS_1 = _ROOT / "data" / "pass_1.json"
_FINAL = _ROOT / "data" / "final.json"
_VERIFICATION_SAMPLE = _ROOT / "data" / "verification_sample.json"
_GROUND_TRUTH = _ROOT / "data" / "ground_truth.json"

# Fields evaluated for ground truth accuracy
EVALUATED_FIELDS = [
    "auth_methods",
    "self_serve_status",
    "api_type",
    "api_breadth",
    "mcp_available",
    "mcp_official",
    "buildability_verdict",
    "primary_blocker",
]

# Error taxonomy categories
ERROR_TYPES = [
    "search_failure",
    "hallucination",
    "pricing_confusion",
    "mcp_false_positive",
    "mcp_false_negative",
    "buildability_misclassification",
    "other",
]


def load_dataset(file_path: Path) -> list[dict[str, Any]]:
    """Load records from a JSON array or line-delimited JSON (NDJSON) file."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return []

    raw = file_path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    # NDJSON format
    if raw.startswith("{"):
        records = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return records

    # JSON Array format
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    return []


# ─────────────────────────────────────────────────────────────────────────────
# 1. Stratified Sampling
# ─────────────────────────────────────────────────────────────────────────────

def stratified_sample(
    apps: list[dict[str, Any]], target_total: int = 20
) -> list[dict[str, Any]]:
    """
    Pick a stratified sample of apps from pass_1.json:
    Target: 2 per category, covering a mix of confidence levels (High/Medium/Low),
    MCP status (Yes/No), and self-serve/gated access.
    """
    if not apps:
        return []

    # Group by category
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for app in apps:
        cat = app.get("category", "Uncategorized")
        by_category[cat].append(app)

    sampled: list[dict[str, Any]] = []

    # For each category, select up to 2 apps with diverse attributes
    for cat, cat_apps in by_category.items():
        if len(cat_apps) <= 2:
            sampled.extend(cat_apps)
        else:
            # Sort/score candidates to favor mix of confidence & MCP/Self-serve variation
            # Pick 1 high/medium confidence + 1 low confidence or MCP=Yes if available
            cat_apps_sorted = sorted(
                cat_apps,
                key=lambda a: (
                    a.get("confidence") == "Low",
                    a.get("mcp_available") == "Yes",
                    a.get("human_review_required", False),
                ),
            )
            # Pick first and last to maximize diversity
            first = cat_apps_sorted[0]
            second = cat_apps_sorted[-1] if cat_apps_sorted[-1] != first else cat_apps_sorted[1]
            sampled.append(first)
            sampled.append(second)

    # Adjust to target_total if needed
    if len(sampled) > target_total:
        sampled = sampled[:target_total]
    elif len(sampled) < target_total and len(apps) > len(sampled):
        remaining = [a for a in apps if a not in sampled]
        needed = target_total - len(sampled)
        sampled.extend(remaining[:needed])

    return sampled


def sample_apps(
    pass_1_path: Path = _PASS_1, sample_out_path: Path = _VERIFICATION_SAMPLE
) -> list[dict[str, Any]]:
    """Sample apps from pass_1.json and write to verification_sample.json."""
    apps = load_dataset(pass_1_path)
    if not apps:
        print(f"Warning: No apps found in {pass_1_path}. Checking final.json...")
        apps = load_dataset(_FINAL)

    if not apps:
        print("Error: No apps available to sample from!")
        return []

    sample = stratified_sample(apps, target_total=20)
    sample_out_path.parent.mkdir(parents=True, exist_ok=True)
    sample_out_path.write_text(
        json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"✓ Successfully wrote stratified sample of {len(sample)} apps to {sample_out_path}"
    )
    return sample


# ─────────────────────────────────────────────────────────────────────────────
# 2. Interactive CLI Flow
# ─────────────────────────────────────────────────────────────────────────────

def run_verification(
    sample_path: Path = _VERIFICATION_SAMPLE,
    ground_truth_path: Path = _GROUND_TRUTH,
) -> None:
    """
    Interactive CLI flow: for each sampled app, print the agent's answer for every field,
    prompt ground truth and correctness (y/n), saving continuously to ground_truth.json.
    """
    sample = load_dataset(sample_path)
    if not sample:
        print(f"Sample file {sample_path} not found or empty. Generating sample first...")
        sample = sample_apps(sample_out_path=sample_path)

    if not sample:
        print("No sampled apps to verify.")
        return

    # Load existing ground truth for resume support
    existing_gt = load_dataset(ground_truth_path)
    gt_map: dict[str, dict[str, Any]] = {
        item["app_name"]: item for item in existing_gt if isinstance(item, dict) and "app_name" in item
    }

    print("\n" + "=" * 70)
    print(" COMPOSIO GROUND-TRUTH VERIFICATION CLI")
    print(" Resumable CLI flow. Press Ctrl+C at any time to save and exit.")
    print("=" * 70 + "\n")

    for idx, app in enumerate(sample, 1):
        app_name = app.get("app_name", f"App_{idx}")
        cat = app.get("category", "Unknown")

        if app_name in gt_map and gt_map[app_name].get("completed", False):
            print(f"[{idx}/{len(sample)}] Skipping '{app_name}' (already verified).")
            continue

        print(f"\n──────────────────────────────────────────────────────────────────────")
        print(f" APP [{idx}/{len(sample)}]: {app_name.upper()}  (Category: {cat})")
        print(f" Description: {app.get('description', 'N/A')}")
        print(f"──────────────────────────────────────────────────────────────────────")

        fields_result: dict[str, Any] = {}

        try:
            for field in EVALUATED_FIELDS:
                agent_val = app.get(field)
                if isinstance(agent_val, list):
                    agent_str = ", ".join(map(str, agent_val))
                else:
                    agent_str = str(agent_val) if agent_val is not None else "null"

                print(f"\n• Field: {field}")
                print(f"  Agent Answer : {agent_str}")

                # Prompt correctness
                while True:
                    ans = input("  Is correct? [Y/n]: ").strip().lower()
                    if ans in ("", "y", "yes"):
                        is_correct = True
                        gt_val = agent_val
                        err_type = None
                        break
                    elif ans in ("n", "no"):
                        is_correct = False
                        break
                    else:
                        print("  Please enter 'y' or 'n'.")

                if not is_correct:
                    custom_gt = input(f"  Type Ground Truth (Enter to keep '{agent_str}'): ").strip()
                    if custom_gt:
                        gt_val = custom_gt
                    else:
                        gt_val = agent_val

                    print("\n  Select Error Taxonomy:")
                    for e_idx, et in enumerate(ERROR_TYPES, 1):
                        print(f"    {e_idx}) {et}")
                    
                    err_choice = input(f"  Error Type [1-{len(ERROR_TYPES)}, default=7]: ").strip()
                    try:
                        c_num = int(err_choice)
                        if 1 <= c_num <= len(ERROR_TYPES):
                            err_type = ERROR_TYPES[c_num - 1]
                        else:
                            err_type = "other"
                    except ValueError:
                        err_type = "other"
                
                fields_result[field] = {
                    "agent_answer": agent_val,
                    "ground_truth": gt_val,
                    "correct": is_correct,
                    "error_type": err_type,
                }

            # Mark app verification as complete
            app_gt_record = {
                "app_name": app_name,
                "category": cat,
                "completed": True,
                "fields": fields_result,
            }
            gt_map[app_name] = app_gt_record

            # Save continuously
            ground_truth_path.parent.mkdir(parents=True, exist_ok=True)
            ground_truth_path.write_text(
                json.dumps(list(gt_map.values()), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"\n✓ Saved progress for '{app_name}' to {ground_truth_path}")

        except KeyboardInterrupt:
            print("\n\nVerification paused by user. Progress saved.")
            return

    print("\n" + "=" * 70)
    print(" Verification complete for all sampled applications!")
    print("=" * 70)
    compute_accuracy(ground_truth_path)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Accuracy Computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_accuracy(ground_truth_path: Path = _GROUND_TRUTH) -> dict[str, Any]:
    """
    Compute and print overall accuracy %, field-level accuracy, and error taxonomy counts.
    """
    records = load_dataset(ground_truth_path)
    if not records:
        print(f"No ground truth data found at {ground_truth_path}.")
        return {}

    total_checks = 0
    total_correct = 0

    field_total: Counter[str] = Counter()
    field_correct: Counter[str] = Counter()
    error_taxonomy: Counter[str] = Counter()

    for rec in records:
        fields = rec.get("fields", {})
        for field, details in fields.items():
            total_checks += 1
            field_total[field] += 1
            
            is_corr = details.get("correct", False)
            if is_corr:
                total_correct += 1
                field_correct[field] += 1
            else:
                err_type = details.get("error_type", "other")
                if err_type:
                    error_taxonomy[err_type] += 1

    overall_acc = (total_correct / total_checks * 100.0) if total_checks > 0 else 0.0

    print("\n" + "=" * 70)
    print(" ACCURACY & VERIFICATION SUMMARY REPORT")
    print("=" * 70)
    print(f" Total Apps Verified : {len(records)}")
    print(f" Total Fields Checked: {total_checks}")
    print(f" Correct Fields      : {total_correct}")
    print(f" Overall Accuracy    : {overall_acc:.1f}%\n")

    print("Field-Level Accuracy Breakdown:")
    print("-" * 50)
    field_acc_map = {}
    for f in EVALUATED_FIELDS:
        f_tot = field_total[f]
        f_corr = field_correct[f]
        f_acc = (f_corr / f_tot * 100.0) if f_tot > 0 else 0.0
        field_acc_map[f] = f_acc
        print(f"  • {f:<25}: {f_acc:5.1f}% ({f_corr}/{f_tot})")

    print("\nError Taxonomy Breakdown:")
    print("-" * 50)
    if error_taxonomy:
        for err_type, count in error_taxonomy.most_common():
            pct = (count / (total_checks - total_correct) * 100.0) if (total_checks - total_correct) > 0 else 0.0
            print(f"  • {err_type:<30}: {count:2d} ({pct:4.1f}%)")
    else:
        print("  • No errors recorded!")

    print("=" * 70 + "\n")

    return {
        "overall_accuracy": overall_acc,
        "total_checks": total_checks,
        "total_correct": total_correct,
        "field_accuracy": field_acc_map,
        "error_taxonomy": dict(error_taxonomy),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Composio Research Pipeline — Stratified Sampling & Verification CLI"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Generate 20-app stratified verification sample",
    )
    parser.add_argument(
        "--run", action="store_true", help="Run interactive verification CLI flow"
    )
    parser.add_argument(
        "--accuracy", action="store_true", help="Compute & print accuracy metrics"
    )

    args = parser.parse_args()

    if args.sample:
        sample_apps()
    elif args.run:
        run_verification()
    elif args.accuracy:
        compute_accuracy()
    else:
        # Default behavior: run sampling if missing, then prompt verification
        if not _VERIFICATION_SAMPLE.exists():
            sample_apps()
        if _GROUND_TRUTH.exists():
            compute_accuracy()
        else:
            run_verification()


if __name__ == "__main__":
    main()
