"""Median net worth by education of the household head, SCF 1989-2025, with
standard errors.

Reads the files downloaded by get_data.py and writes:

* data/networth_by_education.csv       one row per survey year
* data/networth_by_education_age.csv   one row per survey year x age group

Groups: families headed by a college graduate vs. by someone with a
high-school diploma or less, overall and within age groups of the head.

Method:
* "Head" is the SCF reference person; EDCL is that person's education
  (1 = no HS diploma, 2 = HS diploma, 3 = some college, 4 = college degree)
  and AGECL their age group (1 = <35, 2 = 35-44, ..., 6 = 75+).
* Point estimates pool all five imputation implicates with WGT (already
  scaled so the rows sum to the family population). This reproduces the
  Fed's published medians and means; the script checks that against Table 4.
* Standard errors follow the Fed's documentation
  (https://www.federalreserve.gov/econres/files/standard_error_documentation.pdf):
  sampling variance from the 999 bootstrap replicate weights (WT1Bk x MMk),
  first implicate only, plus imputation variance, the variance of the five
  implicate estimates times (1 + 1/5).
* The ratio's interval is computed on the log scale and exponentiated, so it
  is asymmetric and never goes below zero.
* All dollars are 2025 dollars, as released by the Fed.

Usage: python estimates.py
"""

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from get_data import RAW_DIR, STDERR_FILE, TABLES_FILE, YEARS, extract_file, replicate_file

ROOT = Path(__file__).parent
OVERALL_CSV = ROOT / "data" / "networth_by_education.csv"
BY_AGE_CSV = ROOT / "data" / "networth_by_education_age.csv"

GROUPS = {
    "college": [4],
    "hs_or_less": [1, 2],
}
# Fed Table 4 row labels for each EDCL code, used for the cross-check.
TABLE4_ROWS = {
    1: "No high school diploma",
    2: "High school diploma",
    3: "Some college",
    4: "College degree",
}
# AGECL code -> label; the Fed's Table 4 row label is the same text.
AGE_GROUPS = {
    1: "Less than 35",
    2: "35–44",
    3: "45–54",
    4: "55–64",
    5: "65–74",
    6: "75 or more",
}
Z95 = 1.959964


def weighted_median(values, weights):
    """Weighted median of values; weights may be a vector or an (n, k) matrix,
    in which case one median per column is returned."""
    order = np.argsort(values, kind="stable")
    v, w = values[order], weights[order]
    cum = np.cumsum(w, axis=0)
    return v[np.argmax(cum >= cum[-1] / 2, axis=0)]


def load_year(year):
    with zipfile.ZipFile(RAW_DIR / extract_file(year)) as z:
        with z.open(f"SCFP{year}.csv") as f:
            df = pd.read_csv(f, usecols=lambda c: c.upper() in
                             {"Y1", "X1", "WGT", "EDCL", "AGECL", "NETWORTH"})
    df.columns = df.columns.str.lower()
    df = df.rename(columns={"x1": "y1"})  # 1989 calls the record id X1
    df["implicate"] = df["y1"] % 10
    return df


def load_replicate_weights(year):
    """(n_families, 999) replicate weights for implicate 1, indexed by y1."""
    with zipfile.ZipFile(RAW_DIR / replicate_file(year)) as z:
        (name,) = z.namelist()
        rw = pd.read_stata(z.open(name))
    rw.columns = rw.columns.str.lower()
    rw = rw.rename(columns={"x1": "y1"}).set_index("y1")
    n = 999
    wt = rw[[f"wt1b{k}" for k in range(1, n + 1)]].to_numpy()
    mm = rw[[f"mm{k}" for k in range(1, n + 1)]].to_numpy()
    # A blank weight means the family was not drawn into that replicate.
    return pd.DataFrame(np.nan_to_num(wt * mm), index=rw.index)


class Year:
    """One survey year's data, with the replicate weights aligned to implicate 1."""

    def __init__(self, year):
        self.year = year
        self.df = load_year(year)
        imp1 = self.df[self.df["implicate"] == 1]
        self.rep = load_replicate_weights(year).loc[imp1["y1"]].to_numpy()
        self.imp1_mask = (self.df["implicate"] == 1).to_numpy()

    def medians(self, mask):
        """Pooled point estimate, the 5 implicate estimates, and 999 replicate
        estimates (implicate 1) of median net worth for rows where mask is true."""
        df = self.df
        nw, w = df["networth"].to_numpy(), df["wgt"].to_numpy()
        point = weighted_median(nw[mask], w[mask])
        by_imp = np.array([
            weighted_median(nw[mask & (df["implicate"] == i).to_numpy()],
                            w[mask & (df["implicate"] == i).to_numpy()])
            for i in range(1, 6)
        ])
        m1 = mask[self.imp1_mask]
        reps = weighted_median(nw[self.imp1_mask][m1], self.rep[m1])
        return point, by_imp, reps

    def summarize(self, mask, base_mask):
        """Mean, share of base_mask's families, and sample size for mask."""
        df = self.df[mask]
        return {
            "mean": np.average(df["networth"], weights=df["wgt"]),
            "share": df["wgt"].sum() / self.df.loc[base_mask, "wgt"].sum(),
            "n_families": len(df) // 5,  # unweighted sample size; 5 rows per family
        }


def total_se(by_imp, reps):
    """Fed method: bootstrap sampling variance + (1 + 1/5) x imputation variance."""
    return np.sqrt(np.var(reps, ddof=1) + 1.2 * np.var(by_imp, ddof=1))


def estimate_gap(yr, base_mask):
    """College vs HS-or-less medians, their SEs, and the ratio with a 95% CI."""
    edcl = yr.df["edcl"].to_numpy()
    out, logs = {}, {}
    for group, codes in GROUPS.items():
        mask = base_mask & np.isin(edcl, codes)
        point, by_imp, reps = yr.medians(mask)
        se = total_se(by_imp, reps)
        out.update({
            f"median_{group}": point,
            f"median_{group}_se": se,
            f"median_{group}_lo": point - Z95 * se,
            f"median_{group}_hi": point + Z95 * se,
            **{f"{k}_{group}": v for k, v in yr.summarize(mask, base_mask).items()},
        })
        logs[group] = (np.log(point), np.log(by_imp), np.log(reps))
    (pc, ic, rc), (ph, ih, rh) = logs["college"], logs["hs_or_less"]
    log_se = total_se(ic - ih, rc - rh)
    out.update({
        "median_ratio": np.exp(pc - ph),
        "median_ratio_lo": np.exp(pc - ph - Z95 * log_se),
        "median_ratio_hi": np.exp(pc - ph + Z95 * log_se),
        "mean_ratio": out["mean_college"] / out["mean_hs_or_less"],
    })
    return out


def read_table4():
    """Return {(year, row label): (median, mean)} in dollars from Fed Table 4."""
    t = pd.read_excel(RAW_DIR / TABLES_FILE, sheet_name="Table 4", header=None)
    header_row = t.index[t[0].astype(str).str.strip() == "Family characteristic"][0]
    year_cols = {int(y): c for c, y in t.loc[header_row].items() if str(y).isdigit()}
    labels = t[0].astype(str).str.strip()
    out = {}
    for label in [*TABLE4_ROWS.values(), *AGE_GROUPS.values()]:
        r = t.index[labels == label][0]
        for year, c in year_cols.items():
            out[(year, label)] = (float(t.at[r, c]) * 1e3, float(t.at[r, c + 1]) * 1e3)
    return out


def check_against_table4(yr, table4):
    # The table is rounded to tens of dollars (two decimals in thousands).
    df = yr.df
    checks = [(var, code, label)
              for var, rows in [("edcl", TABLE4_ROWS), ("agecl", AGE_GROUPS)]
              for code, label in rows.items()]
    for var, code, label in checks:
        sub = df[df[var] == code]
        median = weighted_median(sub["networth"].to_numpy(), sub["wgt"].to_numpy())
        mean = np.average(sub["networth"], weights=sub["wgt"])
        pub_median, pub_mean = table4[(yr.year, label)]
        for stat, ours, pub in [("median", median, pub_median), ("mean", mean, pub_mean)]:
            if abs(ours - pub) > 6:
                raise AssertionError(
                    f"{yr.year} {label} {stat}: ours {ours:,.0f} vs Table 4 {pub:,.0f}"
                )


def compare_with_fed_stderrs(years):
    """Print our SEs next to the Fed's for 2022 and 2025 (net worth by education).
    The Fed's come from internal data, so expect them to differ somewhat.
    Their 'Table 2' sheet has the education labels shifted down one row, so
    rows are located by position below the section heading."""
    t = pd.read_excel(RAW_DIR / STDERR_FILE, sheet_name="Table 2", header=None)
    head = t.index[t[0].astype(str).str.strip() == "Education of reference person"][0]
    print("\nMedian net worth SE, thousands of 2025 $ (ours, public data | Fed, internal data):")
    for year, col in [(2022, 2), (2025, 4)]:
        yr = years[year]
        edcl = yr.df["edcl"].to_numpy()
        for i, (code, label) in enumerate(TABLE4_ROWS.items()):
            _, by_imp, reps = yr.medians(edcl == code)
            fed = float(t.at[head + i, col])
            print(f"  {year} {label:<24} {total_se(by_imp, reps) / 1e3:6.1f} | {fed:6.1f}")


def build_tables():
    table4 = read_table4()
    years, overall, by_age = {}, [], []
    for year in YEARS:
        print(f"  {year}")
        yr = years[year] = Year(year)
        check_against_table4(yr, table4)
        everyone = np.ones(len(yr.df), dtype=bool)
        overall.append({"year": year, **estimate_gap(yr, everyone)})
        agecl = yr.df["agecl"].to_numpy()
        for code, label in AGE_GROUPS.items():
            # Within an age group, share = fraction of that age group's families.
            by_age.append({"year": year, "agecl": code, "age_group": label,
                           **estimate_gap(yr, agecl == code)})
    compare_with_fed_stderrs(years)
    return pd.DataFrame(overall), pd.DataFrame(by_age)


def main():
    print("Estimating (point estimates checked against Fed Table 4):")
    overall, by_age = build_tables()
    OVERALL_CSV.parent.mkdir(exist_ok=True)
    overall.to_csv(OVERALL_CSV, index=False, float_format="%.4f")
    by_age.to_csv(BY_AGE_CSV, index=False, float_format="%.4f")

    k = lambda col: (overall[col] / 1e3).round(0)
    print("\nMedian net worth, thousands of 2025 $ [95% CI], and ratio [95% CI]:")
    print(pd.DataFrame({
        "year": overall["year"],
        "college": k("median_college"), "lo": k("median_college_lo"), "hi": k("median_college_hi"),
        "hs_or_less": k("median_hs_or_less"), "lo ": k("median_hs_or_less_lo"),
        "hi ": k("median_hs_or_less_hi"),
        "ratio": overall["median_ratio"].round(2), "r_lo": overall["median_ratio_lo"].round(2),
        "r_hi": overall["median_ratio_hi"].round(2),
    }).to_string(index=False))
    print(f"\nWrote {OVERALL_CSV.relative_to(ROOT)} and {BY_AGE_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
