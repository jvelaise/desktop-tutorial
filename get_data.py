"""Download the Survey of Consumer Finances files used by estimates.py.

Files come from https://www.federalreserve.gov/econres/scfindex.htm:

* Summary Extract Public Data, CSV, one zip per survey year (scfp{YEAR}excel.zip).
  The Fed re-releases every year's extract with each new survey; the current
  set (released 2026-10-09) is in 2025 dollars, so years are comparable.
* Replicate weights (Stata version), one zip per survey year: 999 bootstrap
  weights for the first implicate, used for sampling standard errors.
  About 360 MB in total.
* Historic Tables based on public data, inflation-adjusted to 2025 dollars.
  estimates.py checks its point estimates against Table 4 of this workbook.
* The Fed's standard errors for the 2022 and 2025 headline tables, used as a
  rough check on our standard errors.

Usage: python get_data.py   (files already downloaded are skipped)
"""

import sys
import urllib.request
import zipfile
from pathlib import Path

BASE_URL = "https://www.federalreserve.gov/econres/files/"
YEARS = list(range(1989, 2026, 3))  # 1989, 1992, ..., 2022, 2025
TABLES_FILE = "scf2025_tables_public_real_historical.xlsx"
STDERR_FILE = "2025_tables1_2_stderrs.xlsx"
RAW_DIR = Path(__file__).parent / "data" / "raw"
USER_AGENT = "Mozilla/5.0 (research script; SCF wealth-gap figure)"


def extract_file(year):
    return f"scfp{year}excel.zip"


def replicate_file(year):
    # Surveys before 2001 use two-digit years in the file name.
    return f"scf{year % 100:02d}rw1s.zip" if year < 2001 else f"scf{year}rw1s.zip"


def download(name):
    dest = RAW_DIR / name
    if dest.exists():
        print(f"  have {name}")
        return dest
    print(f"  get  {name}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    # federalreserve.gov returns 403 to urllib's default User-Agent.
    req = urllib.request.Request(BASE_URL + name, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)
    tmp.rename(dest)
    return dest


def check_zip(path, suffix):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower().endswith(suffix)]
    if len(names) != 1:
        sys.exit(f"{path.name}: expected one {suffix} file, found {names}")


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading to {RAW_DIR}")
    for year in YEARS:
        check_zip(download(extract_file(year)), ".csv")
        check_zip(download(replicate_file(year)), ".dta")
    download(TABLES_FILE)
    download(STDERR_FILE)
    print("Done.")


if __name__ == "__main__":
    main()
