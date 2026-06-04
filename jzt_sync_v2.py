#!/usr/bin/env python3
"""JZT Dashboard V2 Sync Script

生成 V2 专用 index.html 和 dates_index.json，同步到 JZT-Dashboard-v2 仓库。

Usage:
    python3 jzt_sync_v2.py --data-dir ~/JZT报数/data --output-dir ~/JZT-Dashboard-v2
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add V1 repo path for imports
V1_SCRIPT_DIR = Path.home() / ".hermes" / "scripts" / "jingzhuntong"


def generate_dates_index(data_dir: Path, max_days: int = 30) -> dict:
    """Generate dates_index.json from available split.json files.

    Args:
        data_dir: Directory containing split.json files
        max_days: Maximum number of days to keep

    Returns:
        dates_index dict with available_dates and latest
    """
    split_files = sorted(data_dir.glob("*_split.json"))
    if not split_files:
        return {"available_dates": [], "latest": ""}

    dates_map = {}
    for f in split_files:
        # Skip non-date files like latest_split.json, latest_meta.json
        name = f.stem  # e.g. "2026-06-04_2357_split" or "latest_split"
        if name.startswith("latest"):
            continue
        # Filename format: YYYY-MM-DD_SSSM_split.json
        parts = name.rsplit("_", 2)
        if len(parts) >= 2:
            date_str = parts[0]
            slot = parts[1]
            # Validate date format
            if len(date_str) == 10 and date_str[4] == "-" and date_str[7] == "-":
                if date_str not in dates_map or slot > dates_map[date_str]["slot"]:
                    dates_map[date_str] = {
                        "date": date_str,
                        "slot": slot,
                        "split_file": f.name,
                    }

    available = sorted(dates_map.values(), key=lambda x: x["date"], reverse=True)[:max_days]
    latest = available[0]["date"] if available else ""

    return {
        "available_dates": available,
        "latest": latest,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def main():
    import argparse
    p = argparse.ArgumentParser(description="JZT Dashboard V2 Sync")
    p.add_argument("--data-dir", required=True, help="Source data directory (from V1 repo)")
    p.add_argument("--output-dir", required=True, help="V2 repo output directory")
    p.add_argument("--v1-scripts-dir", default=str(V1_SCRIPT_DIR), help="V1 scripts directory")
    args = p.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    # Ensure output directories exist
    (output_dir / "data").mkdir(parents=True, exist_ok=True)
    (output_dir / "html").mkdir(parents=True, exist_ok=True)

    # 1. Generate dates_index.json
    dates_index = generate_dates_index(data_dir)
    dates_index_path = output_dir / "data" / "dates_index.json"
    dates_index_path.write_text(json.dumps(dates_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated dates_index.json with {len(dates_index['available_dates'])} dates")

    # 2. Copy all split.json files to V2 data directory
    split_files = list(data_dir.glob("*_split.json"))
    for f in split_files:
        import shutil
        shutil.copy2(f, output_dir / "data" / f.name)
    print(f"Copied {len(split_files)} split.json files")

    # 3. Generate latest_split.json link
    if dates_index["latest"]:
        latest_split = data_dir / f"{dates_index['latest']}_2357_split.json"
        # Find the actual latest file for that date
        for f in sorted(data_dir.glob(f"{dates_index['latest']}_*_split.json"), reverse=True):
            latest_split = f
            break
        if latest_split.exists():
            import shutil
            shutil.copy2(latest_split, output_dir / "data" / "latest_split.json")

    # 4. Run V2 renderer to generate index.html
    latest_split_path = output_dir / "data" / "latest_split.json"
    if latest_split_path.exists():
        # Add V2 scripts dir to path
        sys.path.insert(0, args.v1_scripts_dir)
        from jzt_dashboard_renderer_v2 import build_v2_html

        with open(latest_split_path) as f:
            split_data = json.load(f)

        skus = split_data.get("skus", [])
        meta = {
            "source_file_name": split_data.get("source_file", "—"),
            "source_file_modified_at": split_data.get("generated_at", "—"),
        }
        suggestions = []
        try:
            from jzt_deliver_feishu import generate_suggestions
            suggestions = generate_suggestions(skus, split_data)
        except Exception as e:
            print(f"Warning: Could not generate suggestions: {e}")

        html = build_v2_html(skus, split_data, meta, suggestions, dates_index, dates_index["latest"])
        index_path = output_dir / "index.html"
        index_path.write_text(html, encoding="utf-8")
        print(f"Generated V2 index.html")

        # Also copy to html/ directory
        html_dir_path = output_dir / "html" / "index.html"
        html_dir_path.parent.mkdir(parents=True, exist_ok=True)
        html_dir_path.write_text(html, encoding="utf-8")
        print(f"Copied to html/index.html")

    else:
        print("Warning: No latest_split.json found, skipping HTML generation")

    print(f"\nV2 sync complete. Output in: {output_dir}")
    print(f"GitHub Pages URL will be: https://sevenlucas7.github.io/JZT-Dashboard-v2/")


if __name__ == "__main__":
    main()
