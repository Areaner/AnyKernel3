"""Regenerate the sub-level dropdown choices in kernel-custom.yml.

Reads data/<android>/<kernel>.json (kept fresh by update_data.py) and
rewrites the `options:` list of every sub_level_* input in
.github/workflows/kernel-custom.yml:

    - "auto (自动匹配最新安全补丁级别)"  (keep first, always)
    - "<sublevel> (<ASB month>)"     (one per monthly entry)
    - "lts (<lts full version>)"     (from the JSON "lts" field)

Idempotent: exits 0 and writes nothing when everything is already
up-to-date. Exits 1 on structural errors (missing file / section).
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "kernel-custom.yml"

# sub_level input key suffix -> data file (relative to repo root)
VERSIONS = {
    "5_10": "android12/5.10",
    "5_15": "android13/5.15",
    "6_1": "android14/6.1",
    "6_6": "android15/6.6",
    "6_12": "android16/6.12",
}


def build_options(data: dict) -> list[str]:
    """Build the option labels (without the list dash/indent)."""
    lines = ["auto (自动匹配最新安全补丁级别)"]
    entries = sorted(data.get("entries", []), key=lambda e: e["date"])
    for entry in entries:
        sub = entry["kernel"].rsplit(".", 1)[-1]
        lines.append(f"{sub} ({entry['date']})")
    lts = data.get("lts")
    if lts:
        lines.append(f"lts ({lts})")
    return lines


def main() -> int:
    if not WORKFLOW.exists():
        print(f"::error::workflow not found: {WORKFLOW}", file=sys.stderr)
        return 1
    text = WORKFLOW.read_text(encoding="utf-8")
    any_changed = False

    for key, rel in VERSIONS.items():
        data_file = ROOT / "data" / f"{rel}.json"
        if not data_file.exists():
            print(f"::error::data file not found: {data_file}", file=sys.stderr)
            return 1
        data = json.loads(data_file.read_text(encoding="utf-8"))
        options = build_options(data)
        block = "".join(f'          - "{o}"\n' for o in options)

        # options list of this input: everything between the `options:` line
        # and the next non-item line (or EOF)
        pattern = re.compile(
            rf"(?m)^      sub_level_{key}:\n"
            rf"(?:        [^\n]*\n)*?"
            rf"        options:\n"
            rf"((?:          - \"[^\"]*\"\n)+)"
        )
        match = pattern.search(text)
        if match is None:
            print(f"::error::sub_level_{key} options block not found in kernel-custom.yml",
                  file=sys.stderr)
            return 1
        if match.group(1) == block:
            print(f"sub_level_{key}: unchanged ({len(options)} options)")
            continue
        text = text[: match.start(1)] + block + text[match.end(1):]
        any_changed = True
        print(f"sub_level_{key}: updated ({len(options)} options)")

    if any_changed:
        WORKFLOW.write_text(text, encoding="utf-8", newline="\n")
        print("kernel-custom.yml choices regenerated.")
    else:
        print("kernel-custom.yml choices already up-to-date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
