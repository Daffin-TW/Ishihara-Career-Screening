"""
Bangun src/data/occupation_riasec.csv dari "Career Interest Types.xlsx".

Sumber utama: O*NET Career Interest Types (Scale ID OI = skor 1-7,
Scale ID IH = tiga interest high-point). IH TIDAK dipakai sebagai skor
numerik; hanya diambil kodenya sebagai dimensi dominan.

Jalankan:
    python training/build_riasec_csv.py
"""
import collections
import csv
import os
import sys

import openpyxl

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX_PATH = os.path.join(BASE_DIR, "src", "data", "Career Interest Types.xlsx")
OCC_PATH = os.path.join(BASE_DIR, "src", "data", "occupation_importance.csv")
OUT_PATH = os.path.join(BASE_DIR, "src", "data", "occupation_riasec.csv")

DIMS = ["Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"]
SHORT = ["R", "I", "A", "S", "E", "C"]
IH_INDEX = {1: "R", 2: "I", 3: "A", 4: "S", 5: "E", 6: "C"}


def _to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def main():
    workbook = openpyxl.load_workbook(XLSX_PATH, read_only=True, data_only=True)
    sheet = workbook["Career Interest Types"]
    rows = sheet.iter_rows(values_only=True)
    header = next(rows)

    oi = collections.defaultdict(dict)
    ih = collections.defaultdict(dict)
    titles = {}
    dates = set()
    for record in rows:
        row = dict(zip(header, record))
        code = (row.get("O*NET-SOC Code") or "").strip()
        if not code:
            continue
        titles[code] = (row.get("Title") or "").strip()
        dates.add(row.get("Date"))
        scale = (row.get("Scale ID") or "").strip()
        name = (row.get("Element Name") or "").strip()
        value = row.get("Data Value")
        if scale == "OI" and name in DIMS:
            oi[code][name] = float(value)
        elif scale == "IH" and name in (
            "First Interest High-Point",
            "Second Interest High-Point",
            "Third Interest High-Point",
        ):
            ih[code][name] = _to_int(value)

    # Kategori karier dari occupation_importance.csv (filter kesehatan 29/31).
    categories = {}
    with open(OCC_PATH, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = row["Code"].strip()
            category = row["OccupationCategory"].strip()
            if category.startswith("[Kesehatan]") and not code.startswith(("29", "31")):
                continue
            categories[code] = category

    incomplete = []
    out = []
    for code, values in oi.items():
        if len(values) != len(DIMS):
            incomplete.append(code)
            continue
        high = ih.get(code, {})
        dominant = [
            IH_INDEX.get(high.get("First Interest High-Point")),
            IH_INDEX.get(high.get("Second Interest High-Point")),
            IH_INDEX.get(high.get("Third Interest High-Point")),
        ]
        record = {
            "Code": code,
            "Occupation": titles.get(code, ""),
            "OccupationCategory": categories.get(code, ""),
        }
        for short, dim in zip(SHORT, DIMS):
            record[short] = round(values[dim], 4)
        record["IH1"] = dominant[0] or ""
        record["IH2"] = dominant[1] or ""
        record["IH3"] = dominant[2] or ""
        out.append(record)

    out.sort(key=lambda r: (r["OccupationCategory"], r["Occupation"]))
    fields = ["Code", "Occupation", "OccupationCategory"] + SHORT + ["IH1", "IH2", "IH3"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)

    print(f"Sumber      : {os.path.basename(XLSX_PATH)}")
    print(f"Tanggal data: {sorted(d for d in dates if d)}")
    print(f"Okupasi OI  : {len(oi)} (lengkap 6 dimensi: {len(oi) - len(incomplete)})")
    print(f"IH tersedia : {len(ih)}")
    print(f"Output      : {OUT_PATH} ({len(out)} baris)")
    if incomplete:
        print("Tidak lengkap:", incomplete[:5])
    return 0


if __name__ == "__main__":
    sys.exit(main())
