#!/usr/bin/env python3
"""Push the publisher's files, their Parquet and the card to the Hugging Face Hub.

The CSVs go up as files rather than through datasets.push_to_hub, because
push_to_hub re-encodes. The bytes under raw/<year>/ are the publisher's own,
with a manifest per year, so they are uploaded unchanged. A new year is added
beside the others; the years already on the Hub are not touched.

    uv run python src/publish.py             # dry run
    uv run python src/publish.py --push
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "yuiseki/npa-traffic-accidents"

# Declared on the card, and therefore checked before anything moves.
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
TABLES = ("honhyo", "hojuhyo", "kosokuhyo")
CONFIGS = {f"{y}.{t}": f"parquet/{y}/{t}.parquet" for y in YEARS for t in TABLES}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()

    card = (ROOT / "data" / "README.md").read_text(encoding="utf-8")
    for name, path in CONFIGS.items():
        if not re.search(rf"^- config_name: {re.escape(name)}$", card, re.M):
            raise SystemExit(f"the card declares no config named {name}")
        if not re.search(rf"^  data_files: {re.escape(path)}$", card, re.M):
            raise SystemExit(f"the card's data_files do not point at {path}")
        if not (ROOT / "data" / path).exists():
            raise SystemExit(f"missing {path}; run scripts/03 first")

    # The files are the claim. A manifest that does not describe them means the
    # copy on the Hub is not the copy that was checked.
    files = ["README.md", "LICENSE", "provenance.yaml"]
    for y in YEARS:
        d = ROOT / "data" / "raw" / str(y)
        listed = {}
        for line in (d / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
            sha, _size, _lm, name = line.split("  ")
            listed[name] = sha
        on_disk = sorted(p.name for p in d.iterdir() if p.name != "MANIFEST.sha256")
        if sorted(listed) != on_disk:
            raise SystemExit(f"raw/{y}: MANIFEST.sha256 and the directory do not agree")
        for name, sha in listed.items():
            if hashlib.sha256((d / name).read_bytes()).hexdigest() != sha:
                raise SystemExit(f"raw/{y}/{name}: not the file in the manifest")
        files += [f"raw/{y}/MANIFEST.sha256"] + [f"raw/{y}/{n}" for n in on_disk]
    print(f"{len(YEARS)} years of raw files match their manifests")
    files += list(CONFIGS.values())
    total = sum((ROOT / "data" / f).stat().st_size for f in files)
    print(f"{a.repo}\n  {len(files)} files, {total / 1e6:.1f} MB")

    if not a.push:
        print("\ndry run. pass --push to upload")
        return 0

    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(a.repo, repo_type="dataset", exist_ok=True, private=False)
    api.upload_folder(
        folder_path=str(ROOT / "data"),
        repo_id=a.repo,
        repo_type="dataset",
        allow_patterns=files,
    )
    print(f"\npushed to https://huggingface.co/datasets/{a.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
