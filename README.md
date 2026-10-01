# npa-traffic-accidents

Dataset: https://huggingface.co/datasets/yuiseki/npa-traffic-accidents

The National Police Agency's open data on every injury road accident in
Japan, 2019 to 2025, one subset per year and table, and the code that fetches,
checks and converts it. This repository holds the code; the data is on the
Hub.

## Where things are

```
scripts/01_download.py        every file each year's page links, with sha256 and Last-Modified
scripts/02_verify.py          rows, deaths and injured pinned per year; keys, references, locations
scripts/03_export_parquet.py  cp932 CSV -> UTF-8 -> Parquet; degrees and a point for honhyo
src/publish.py                pushes the data and its card to the Hub
tests/                        degrees from packed DMS, the export, no bloom filters

data/README.md                the dataset card. Uploaded as-is
data/LICENSE                  the CC BY notice and the modifications, in Japanese as the terms ask
data/provenance.yaml          the years, the counts, the codes, and what was done
data/raw/<year>/              generated, 448 MiB in all, the agency's own files
data/parquet/<year>/          generated, 106 MiB
```

## Running it

```sh
uv run python scripts/01_download.py
uv run python scripts/02_verify.py
uv run python scripts/03_export_parquet.py
uv run python src/publish.py          # dry run; --push to upload
uv run pytest
```

A couple of minutes. Adding a year is adding it to `YEARS` in
`01_download.py` and `publish.py`, and its figures to `02_verify.py`.

## Four traps

**Coordinates are packed DMS.** `430607590` is 43°06'07.590"N, not a number
of degrees. All zeros means no location; so does a point in the Gulf of
Guinea, which 2020 has twenty of.

**The prefecture code is the police's.** Tokyo is `30`. Hokkaido is five.

**Counts are zero-padded text.** `死者数` is `000` or `001`. Compared with
`'0'` as text, every row differs.

**DuckDB's shift_jis reader breaks a byte.** On the 2024 `honhyo` it stops at
byte 31,999,999, a byte before the 32,000,000 mark, on a line that is plain
ASCII. The export rewrites the CSVs as UTF-8 with Python's cp932 codec first.

## Licence

The code here is MIT. The data it fetches is CC BY 4.0, by way of the Public
Data License 1.0 the agency applies:

    出典：警察庁ウェブサイト
    （https://www.npa.go.jp/publications/statistics/koutsuu/opendata/index_opendata.html）を加工して作成

See `data/LICENSE` for the notice and the modifications.
