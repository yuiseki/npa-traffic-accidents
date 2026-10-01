import importlib.util
from pathlib import Path

import duckdb
import pytest

_spec = importlib.util.spec_from_file_location(
    "export", Path(__file__).parents[1] / "scripts" / "03_export_parquet.py"
)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

HEADER = (
    "資料区分,都道府県コード,警察署等コード,本票番号,死者数,地点　緯度（北緯）,地点　経度（東経）"
)


def _csv(tmp_path, rows: list[str]) -> Path:
    p = tmp_path / "honhyo_2024.csv"
    p.write_bytes(("\r\n".join([HEADER, *rows]) + "\r\n").encode("cp932"))
    return p


@pytest.mark.parametrize(
    ("value", "digits", "degrees"),
    [
        ("430607590", 2, 43 + 6 / 60 + 7.590 / 3600),
        ("1412109599", 3, 141 + 21 / 60 + 9.599 / 3600),
        ("000000000", 2, None),
    ],
)
def test_dms_to_degrees(value, digits, degrees):
    got = m.dms_to_degrees(value, digits)
    assert got == pytest.approx(degrees) if degrees is not None else got is None


def test_to_utf8_rewrites_cp932(tmp_path):
    src = _csv(tmp_path, ["1,30,001,0001,0,353215150,1394429127"])
    dst = m.to_utf8(src, tmp_path / "u.csv")
    assert dst.read_text(encoding="utf-8").splitlines()[0] == HEADER


def test_export_keeps_codes_as_text_and_adds_degrees(tmp_path):
    src = _csv(
        tmp_path, ["1,10,059,0001,0,430607590,1412109599", "1,30,001,0002,1,000000000,0000000000"]
    )
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    rel = con.sql(m.select_sql(m.to_utf8(src, tmp_path / "u.csv"), honhyo=True))
    rows = rel.order("本票番号").fetchall()
    cols = rel.columns
    first = dict(zip(cols, rows[0], strict=True))
    assert first["警察署等コード"] == "059" and first["本票番号"] == "0001"
    assert first["latitude"] == pytest.approx(43.102108, abs=1e-6)
    assert first["longitude"] == pytest.approx(141.352666, abs=1e-6)
    second = dict(zip(cols, rows[1], strict=True))
    assert second["latitude"] is None and second["geometry"] is None
    assert second["地点　緯度（北緯）"] == "000000000"


def test_written_without_bloom_filters(tmp_path):
    src = _csv(
        tmp_path, [f"1,{i % 51 + 10},001,{i:04d},0,353215150,1394429127" for i in range(3000)]
    )
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    p = tmp_path / "t.parquet"
    m.write(con, m.select_sql(m.to_utf8(src, tmp_path / "u.csv"), honhyo=True), p)
    got = con.sql(
        f"select count(*) filter (where bloom_filter_offset is not null) from parquet_metadata('{p}')"
    ).fetchone()[0]
    assert got == 0


@pytest.mark.parametrize(
    ("lat", "lon"),
    [
        ("000000000", "1333037516"),  # 2021: only the latitude is missing
        ("000016566", "0000036144"),  # 2020: twenty rows at 0'16"N 0'36"E
    ],
)
def test_a_location_that_is_not_in_japan_gets_no_degrees(tmp_path, lat, lon):
    src = _csv(tmp_path, [f"1,83,001,0001,0,{lat},{lon}"])
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    row = con.sql(m.select_sql(m.to_utf8(src, tmp_path / "u.csv"), honhyo=True)).fetchone()
    assert row[-3:] == (None, None, None)
