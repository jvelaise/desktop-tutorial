"""Export one survey year's records, with the columns used in the analysis and
readable group labels, to data/scf{YEAR}_records.csv.

Each family appears five times (one row per imputation implicate). Weights
(wgt) sum to the family population across all rows; dollars are 2025 dollars.

Usage: python export_year.py 1998
"""

import sys
import zipfile

import pandas as pd

from estimates import AGE_GROUPS, GROUPS, ROOT, TABLE4_ROWS
from get_data import RAW_DIR, extract_file

COLUMNS = ["YY1", "Y1", "WGT", "AGE", "AGECL", "EDUC", "EDCL",
           "INCOME", "ASSET", "DEBT", "NETWORTH"]


def main(year):
    with zipfile.ZipFile(RAW_DIR / extract_file(year)) as z:
        with z.open(f"SCFP{year}.csv") as f:
            # 1989 names the ids XX1/X1 rather than YY1/Y1.
            df = pd.read_csv(f, usecols=lambda c: c.upper() in {*COLUMNS, "XX1", "X1"})
    df.columns = df.columns.str.lower()
    df = df.rename(columns={"xx1": "yy1", "x1": "y1"})
    df.insert(2, "implicate", df["y1"] % 10)
    df.insert(df.columns.get_loc("agecl") + 1, "age_group", df["agecl"].map(AGE_GROUPS))
    df.insert(df.columns.get_loc("edcl") + 1, "education", df["edcl"].map(TABLE4_ROWS))
    code_to_group = {c: g for g, codes in GROUPS.items() for c in codes}
    df.insert(df.columns.get_loc("education") + 1, "group",
              df["edcl"].map(code_to_group).fillna("some_college"))
    out = ROOT / "data" / f"scf{year}_records.csv"
    df.sort_values(["yy1", "implicate"]).to_csv(out, index=False)
    print(f"Wrote {out.relative_to(ROOT)}: {len(df):,} rows "
          f"({df['yy1'].nunique():,} families x 5 implicates), {df.shape[1]} columns")


if __name__ == "__main__":
    main(int(sys.argv[1]))
