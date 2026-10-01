#!/usr/bin/env python3
"""Check that each year's CSVs are the files recorded and hang together.

Read with the csv module only, so nothing here shares a parser with the
Parquet export. The figures are those of the files fetched on 2026-10-02; a
year whose figures change is a year the publisher replaced, which its page
says never happens.

  rows of every table, and the deaths and injured of honhyo
  every honhyo row has a unique 都道府県コード, 警察署等コード, 本票番号
  every hojuhyo and kosokuhyo row belongs to a honhyo row
  every coordinate is 9 and 10 digits with minutes and seconds under 60;
  the rows with no location (either value all zeros) and the rows whose
  location falls outside Japan are counted and pinned
"""

import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
KEY = ("都道府県コード", "警察署等コード", "本票番号")

# year: honhyo, hojuhyo, kosokuhyo rows; deaths; injured;
#       rows with no location; rows located outside Japan
EXPECTED = {
    2019: (381237, 88961, 7094, 3215, 461775, 74, 0),
    2020: (309178, 66332, 4649, 2839, 369476, 21, 20),
    2021: (305196, 62694, 4863, 2636, 362131, 33, 0),
    2022: (300839, 61399, 5655, 2611, 356602, 20, 0),
    2023: (307930, 64190, 6324, 2678, 365595, 0, 0),
    2024: (290895, 59963, 6181, 2663, 344395, 0, 0),
    2025: (287023, 57827, 5961, 2547, 338508, 3, 0),
}


def read(path: Path) -> tuple[list[str], list[list[str]]]:
    with open(path, encoding="cp932", newline="") as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]


def degrees(s: str, n: int) -> tuple[float, bool]:
    d, mi, sec = int(s[:n]), int(s[n : n + 2]), int(s[n + 2 :]) / 1000
    return d + mi / 60 + sec / 3600, mi < 60 and sec < 60


def main() -> int:
    failures = []

    def check(ok: bool, what: str) -> None:
        print(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            failures.append(what)

    for year, (n_hon, n_hoju, n_koso, deaths, injured, no_loc, abroad) in EXPECTED.items():
        d = RAW / str(year)
        bad = 0
        for line in (d / "MANIFEST.sha256").read_text().splitlines():
            sha, size, _lm, name = line.split("  ")
            data = (d / name).read_bytes()
            bad += hashlib.sha256(data).hexdigest() != sha or len(data) != int(size)
        check(bad == 0, f"{year}: every file matches the manifest ({bad} do not)")

        h, hon = read(d / f"honhyo_{year}.csv")
        check(len(hon) == n_hon, f"{year}: honhyo {len(hon):,} rows, expected {n_hon:,}")
        check(all(len(r) == len(h) for r in hon), f"{year}: every honhyo row has {len(h)} fields")
        ix = [h.index(k) for k in KEY]
        keys = {tuple(r[i] for i in ix) for r in hon}
        check(len(keys) == len(hon), f"{year}: the honhyo key is unique")
        got = (
            sum(int(r[h.index("死者数")]) for r in hon),
            sum(int(r[h.index("負傷者数")]) for r in hon),
        )
        check(got == (deaths, injured), f"{year}: deaths {got[0]:,}, injured {got[1]:,}")

        lat = h.index(next(c for c in h if "緯度" in c))
        lon = h.index(next(c for c in h if "経度" in c))
        shape = sum(
            not (r[lat].isdigit() and len(r[lat]) == 9 and r[lon].isdigit() and len(r[lon]) == 10)
            for r in hon
        )
        check(shape == 0, f"{year}: every coordinate is 9 and 10 digits ({shape} are not)")

        def missing(r, lat=lat, lon=lon):
            return set(r[lat]) == {"0"} or set(r[lon]) == {"0"}

        zero = sum(missing(r) for r in hon)
        check(zero == no_loc, f"{year}: {zero} rows with no location, expected {no_loc}")
        outside = 0
        for r in hon:
            if missing(r):
                continue
            (y, ok1), (x, ok2) = degrees(r[lat], 2), degrees(r[lon], 3)
            outside += not (ok1 and ok2 and 20 <= y <= 46 and 122 <= x <= 154)
        check(outside == abroad, f"{year}: {outside} locations outside Japan, expected {abroad}")

        for name, n in (("hojuhyo", n_hoju), ("kosokuhyo", n_koso)):
            hh, rows = read(d / f"{name}_{year}.csv")
            check(len(rows) == n, f"{year}: {name} {len(rows):,} rows, expected {n:,}")
            jx = [hh.index(k) for k in KEY]
            orphans = sum(tuple(r[i] for i in jx) not in keys for r in rows)
            check(
                orphans == 0, f"{year}: every {name} row belongs to a honhyo row ({orphans} do not)"
            )

    if failures:
        print(f"\n{len(failures)} checks failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
