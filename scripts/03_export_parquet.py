#!/usr/bin/env python3
"""Turn each year's three CSVs into Parquet, for the Hub viewer and DuckDB.

Every column keeps its name and its text. The codes are digits whose leading
zeros mean something (警察署等コード 059, 本票番号 0001), so nothing is cast.
Three things are done and all are stated on the card:

  the text is UTF-8 instead of cp932
  honhyo gains latitude and longitude in decimal degrees, and a point
  geometry, from 地点 緯度（北緯） and 地点 経度（東経）, which hold degrees,
  minutes and seconds packed into 9 and 10 digits; a value of all zeros,
  or a point outside Japan, gives NULL
  the rows are sorted by 都道府県コード, 警察署等コード, 本票番号

The CSVs are rewritten as UTF-8 by Python before DuckDB reads them. DuckDB
1.5.5's own shift_jis reader stops on the 2024 honhyo at byte 31,999,999,
on a line that is plain ASCII.

The Parquet is written without bloom filters: DuckDB reads them for every
row group a filter touches, even the ones the statistics rule out, and over
HTTP that is a request per row group.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "parquet"
WORK = ROOT / "data" / "work"
TABLES = ("honhyo", "hojuhyo", "kosokuhyo")
LAT = "地点　緯度（北緯）"
LON = "地点　経度（東経）"
KEY = ("都道府県コード", "警察署等コード", "本票番号")


def dms_to_degrees(value: str, degree_digits: int) -> float | None:
    """Packed DDMMSSsss (or DDDMMSSsss) to decimal degrees; all zeros is None."""
    if not value or set(value) == {"0"}:
        return None
    d = int(value[:degree_digits])
    mi = int(value[degree_digits : degree_digits + 2])
    s = int(value[degree_digits + 2 :]) / 1000
    return d + mi / 60 + s / 3600


def _dms_sql(col: str, n: int) -> str:
    c = f'"{col}"'
    return (
        f"case when {c} is null or regexp_full_match({c}, '0+') then null else "
        f"cast(substr({c}, 1, {n}) as integer) + cast(substr({c}, {n + 1}, 2) as integer) / 60.0 "
        f"+ cast(substr({c}, {n + 3}) as integer) / 1000.0 / 3600 end"
    )


def to_utf8(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with (
        open(src, encoding="cp932", newline="") as f,
        open(dst, "w", encoding="utf-8", newline="") as g,
    ):
        g.write(f.read())
    return dst


def select_sql(path: Path, honhyo: bool) -> str:
    """All columns as text; for honhyo, degrees and a point where the location is real.

    A location gets no degrees when either packed value is all zeros (the
    publisher's way of saying none; 2021 has one row with only the latitude
    zero) or when it falls outside Japan (2020 has twenty rows at 0'16"N
    0'36"E). The packed columns themselves are kept as they are.
    """
    src = f"read_csv('{path}', header = true, all_varchar = true, strict_mode = true, quote = '')"
    if not honhyo:
        return f"select * from {src}"
    raw = f"select *, {_dms_sql(LAT, 2)} as y, {_dms_sql(LON, 3)} as x from {src}"
    inside = "y between 20 and 46 and x between 122 and 154"
    return (
        f"select * exclude (y, x), "
        f"case when {inside} then y end as latitude, "
        f"case when {inside} then x end as longitude, "
        f"case when {inside} then st_point(x, y) end as geometry from ({raw})"
    )


def write(con, query: str, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(
        f"copy ({query}) to '{path}' (format parquet, compression zstd, "
        "row_group_size 100000, write_bloom_filter false)"
    )
    return con.sql(f"select count(*) from '{path}'").fetchone()[0]


def main() -> int:
    import csv

    import duckdb

    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    for year_dir in sorted(p for p in RAW.iterdir() if p.is_dir()):
        year = year_dir.name
        for t in TABLES:
            src = year_dir / f"{t}_{year}.csv"
            with open(src, encoding="cp932", newline="") as f:
                rows = sum(1 for _ in csv.reader(f)) - 1
            u = to_utf8(src, WORK / year / f"{t}.csv")
            order = ", ".join(f'"{k}"' for k in KEY) + (', "補充票番号"' if t == "hojuhyo" else "")
            p = OUT / year / f"{t}.parquet"
            got = write(con, f"{select_sql(u, t == 'honhyo')} order by {order}", p)
            if got != rows:
                raise SystemExit(f"{year}/{t}: {got} rows written, the CSV has {rows}")
            print(f"{year}/{t + '.parquet':18} {got:>8,} rows {p.stat().st_size:>12,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
