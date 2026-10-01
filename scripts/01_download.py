#!/usr/bin/env python3
"""Fetch the traffic accident open data of the National Police Agency, by year.

Each year has a page (opendata/<year>/opendata_<year>.html) listing three CSVs
(honhyo, hojuhyo, kosokuhyo) and the file definition and code book as PDF,
and from 2022 also as xlsx. Everything the page links under its own year
directory is taken, unchanged, into data/raw/<year>/.

The page says published data is never corrected, but several files carry a
Last-Modified long after their year was published (2019 and 2020 on
2025-04-18, 2021 on 2026-04-06). The manifest records the Last-Modified of
every file as it was fetched, with its sha256, so a later run can tell a file
that was put again from one that was changed.

A year already in data/raw with a manifest entry for every file is not
fetched again. Adding a year is adding it to YEARS.

    uv run python scripts/01_download.py
"""

import hashlib
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw"
SITE = "https://www.npa.go.jp"
BASE = f"{SITE}/publications/statistics/koutsuu/opendata"
YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
TABLES = ("honhyo", "hojuhyo", "kosokuhyo")
UA = "Mozilla/5.0 (npa-traffic-accidents; +https://github.com/yuiseki/npa-traffic-accidents)"


def get(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read(), r.headers.get("Last-Modified", "")
        except OSError as e:
            if attempt == 2:
                raise
            print(f"retry {url}: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise AssertionError


def links(year: int) -> list[str]:
    """The files a year's page links in its own directory."""
    page, _ = get(f"{BASE}/{year}/opendata_{year}.html")
    hrefs = re.findall(rb'href="([^"]+)"', page)
    prefix = f"/publications/statistics/koutsuu/opendata/{year}/"
    names = sorted({h.decode().rsplit("/", 1)[1] for h in hrefs if h.decode().startswith(prefix)})
    names = [n for n in names if not n.endswith(".html")]
    for t in TABLES:
        if f"{t}_{year}.csv" not in names:
            raise SystemExit(f"{year}: the page does not link {t}_{year}.csv")
    return names


def main() -> int:
    for year in YEARS:
        d = OUT / str(year)
        manifest = d / "MANIFEST.sha256"
        if manifest.exists():
            print(f"{year}: already here")
            continue
        d.mkdir(parents=True, exist_ok=True)
        lines = []
        for name in links(year):
            data, lm = get(f"{BASE}/{year}/{name}")
            if not data:
                raise SystemExit(f"{year}/{name}: empty")
            tmp = d / (name + ".part")
            tmp.write_bytes(data)
            shutil.move(tmp, d / name)
            lines.append(f"{hashlib.sha256(data).hexdigest()}  {len(data)}  {lm}  {name}")
            time.sleep(0.5)
        manifest.write_text("\n".join(lines) + "\n")
        print(f"{year}: {len(lines)} files, {sum(int(x.split('  ')[1]) for x in lines):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
