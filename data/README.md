---
license: cc-by-4.0
language:
- ja
task_categories:
- tabular-classification
- tabular-regression
tags:
- japan
- traffic-accidents
- road-safety
- geospatial
- geoparquet
- npa
size_categories:
- 1M<n<10M
configs:
- config_name: 2019.honhyo
  data_files: parquet/2019/honhyo.parquet
- config_name: 2019.hojuhyo
  data_files: parquet/2019/hojuhyo.parquet
- config_name: 2019.kosokuhyo
  data_files: parquet/2019/kosokuhyo.parquet
- config_name: 2020.honhyo
  data_files: parquet/2020/honhyo.parquet
- config_name: 2020.hojuhyo
  data_files: parquet/2020/hojuhyo.parquet
- config_name: 2020.kosokuhyo
  data_files: parquet/2020/kosokuhyo.parquet
- config_name: 2021.honhyo
  data_files: parquet/2021/honhyo.parquet
- config_name: 2021.hojuhyo
  data_files: parquet/2021/hojuhyo.parquet
- config_name: 2021.kosokuhyo
  data_files: parquet/2021/kosokuhyo.parquet
- config_name: 2022.honhyo
  data_files: parquet/2022/honhyo.parquet
- config_name: 2022.hojuhyo
  data_files: parquet/2022/hojuhyo.parquet
- config_name: 2022.kosokuhyo
  data_files: parquet/2022/kosokuhyo.parquet
- config_name: 2023.honhyo
  data_files: parquet/2023/honhyo.parquet
- config_name: 2023.hojuhyo
  data_files: parquet/2023/hojuhyo.parquet
- config_name: 2023.kosokuhyo
  data_files: parquet/2023/kosokuhyo.parquet
- config_name: 2024.honhyo
  data_files: parquet/2024/honhyo.parquet
- config_name: 2024.hojuhyo
  data_files: parquet/2024/hojuhyo.parquet
- config_name: 2024.kosokuhyo
  data_files: parquet/2024/kosokuhyo.parquet
- config_name: 2025.honhyo
  data_files: parquet/2025/honhyo.parquet
  default: true
- config_name: 2025.hojuhyo
  data_files: parquet/2025/hojuhyo.parquet
- config_name: 2025.kosokuhyo
  data_files: parquet/2025/kosokuhyo.parquet
---

# npa-traffic-accidents

Every injury road accident recorded by the police in Japan, one row each, as
the National Police Agency publishes it: when and where it happened, the
road, the weather, the light, the signals, the two main parties, and how many
died within 24 hours and how many were hurt. 2019 to 2025, about 300,000
accidents a year.

CC BY 4.0, by way of the Public Data License 1.0 the agency applies.

## How it is laid out

One subset per year and table, `{year}.{table}`, as `wikimedia/wikipedia`
names its dumps. A new year is added beside the others and nothing already
here changes, so a result stays reproducible after the next year lands.

| table | what a row is |
|---|---|
| `honhyo` | 本票: one accident, with parties A and B |
| `hojuhyo` | 補充票: party C onward, one row each |
| `kosokuhyo` | 高速票: the expressway details of an accident on one |

| year | `honhyo` | `hojuhyo` | `kosokuhyo` | died | injured |
|---|---:|---:|---:|---:|---:|
| 2019 | 381,237 | 88,961 | 7,094 | 3,215 | 461,775 |
| 2020 | 309,178 | 66,332 | 4,649 | 2,839 | 369,476 |
| 2021 | 305,196 | 62,694 | 4,863 | 2,636 | 362,131 |
| 2022 | 300,839 | 61,399 | 5,655 | 2,611 | 356,602 |
| 2023 | 307,930 | 64,190 | 6,324 | 2,678 | 365,595 |
| 2024 | 290,895 | 59,963 | 6,181 | 2,663 | 344,395 |
| 2025 | 287,023 | 57,827 | 5,961 | 2,547 | 338,508 |

"Died" counts deaths within 24 hours. For 2024 the total, 2,663, is the
figure the agency announced for the year.

`raw/{year}/` holds the agency's own files for that year, byte for byte: the
three CSVs (cp932), the file definition and the code book (PDF, and from 2022
xlsx). 2020 also carries a table mapping its columns to the 2022 definition.
`raw/{year}/MANIFEST.sha256` records the sha256, the size and the
Last-Modified of each.

## Keys and codes

An accident is `都道府県コード`, `警察署等コード`, `本票番号` together; the
three are unique in every year's `honhyo`, and every `hojuhyo` and
`kosokuhyo` row points at a `honhyo` row by them.

Every column of the source is text in the Parquet, under its own Japanese
name. The codes are digits whose leading zeros matter (`警察署等コード` 059,
`本票番号` 0001). The meaning of each code is in the year's code book.

**`都道府県コード` is the police's, not JIS.** Tokyo is `30`, not `13`.
Hokkaido is five codes, one per regional headquarters (`10` Sapporo, `11`
Hakodate, `12` Asahikawa, `13` Kushiro, `14` Kitami), and then `20` Aomori to
`97` Okinawa, 51 in all.

## Where

`地点　緯度（北緯）` and `地点　経度（東経）` are degrees, minutes and seconds
packed into 9 and 10 digits, on the world geodetic system: `430607590` is
43°06'07.590"N. Read as a number it puts Hokkaido at latitude 430 million.

`honhyo` here adds `latitude` and `longitude` in decimal degrees and a point
`geometry` (GeoParquet). They are NULL where the source has no usable
location; the packed columns are kept as they were.

| year | no location (a value of all zeros) | located outside Japan |
|---|---:|---:|
| 2019 | 74 | 0 |
| 2020 | 21 | 20 |
| 2021 | 33 | 0 |
| 2022 | 20 | 0 |
| 2023 | 0 | 0 |
| 2024 | 0 | 0 |
| 2025 | 3 | 0 |

One 2021 row has only its latitude zero. The twenty 2020 rows outside Japan
are all from Kanagawa and all at 0°00'16.566"N 0°00'36.144"E.

```sql
-- DuckDB, straight off the Hub: fatal accidents in Tokyo in 2024, by hour
SELECT "発生日時　　時" AS hour, count(*) AS accidents
FROM 'hf://datasets/yuiseki/npa-traffic-accidents/parquet/2024/honhyo.parquet'
WHERE "都道府県コード" = '30' AND CAST("死者数" AS INTEGER) > 0
GROUP BY 1 ORDER BY 1;
```

`死者数` is three digits (`000`, `001`), so compare it as a number. Against
the text `'0'` every row is unequal and the query counts every accident.
Done right it gives 145 fatal accidents in Tokyo in 2024, with 146 dead.

## The columns changed in 2022

| table | 2019 to 2021 | 2022 on |
|---|---:|---:|
| `honhyo` | 58 columns | 68 |
| `hojuhyo` | 15 | 16 |
| `kosokuhyo` | 17 | 16 |

2022 added sunrise and sunset times, vehicle shape, automatic transmission,
safety-support car, days since a cognitive test and how the driver learned,
each for parties A and B, and dropped direction of travel, roundabout
diameter and the old vehicle shape. Joining years means matching columns by
name and leaving the missing ones empty; the 2020 mapping table in `raw/2020/`
says which old code became which new one.

## Things the publisher says, and what the files show

The page says published data is never corrected afterwards, so the files may
differ from the agency's own statistical tables. The files' Last-Modified
dates are later than their publication for 2019 and 2020 (2025-04-18) and
2021 (2026-04-06). Whether they were put again or changed cannot be told
without the earlier copies. This dataset records what it fetched on
2026-10-02; `scripts/02_verify.py` in the source repository pins every row
count and total above, so a later fetch that differs will say so.

## Reproducing it

```bash
git clone https://github.com/yuiseki/npa-traffic-accidents
cd npa-traffic-accidents
uv run python scripts/01_download.py      # every file each year's page links
uv run python scripts/02_verify.py        # counts, keys, references, locations
uv run python scripts/03_export_parquet.py
```

The CSVs are rewritten as UTF-8 by Python before DuckDB reads them. DuckDB
1.5.5's own `shift_jis` reader stops on the 2024 `honhyo` at byte 31,999,999,
on a line that is plain ASCII.

## Licence

CC BY 4.0. Credit, in the form the agency's terms give:

    出典：警察庁ウェブサイト
    （https://www.npa.go.jp/publications/statistics/koutsuu/opendata/index_opendata.html）を加工して作成

The agency applies the Public Data License 1.0 (公共データ利用規約（第1.0版）),
which permits use in accordance with CC BY 4.0. The terms ask that a
modification be declared and that modified content not be presented as the
government's own; this dataset is not published by the Government of Japan.
`LICENSE` beside this file states the modifications in Japanese. The files
under `raw/` are unchanged.
