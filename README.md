# The education wealth gap in the US, 1989–2025

How has the wealth gap between families headed by a college graduate and
families headed by someone with a high-school diploma or less changed since 1989?

![Median net worth by education of household head, and the ratio between them](figures/wealth_gap_education.png)

**`figures/wealth_gap_education.png`** (the main figure) shows median net worth
for the two groups (left) and the ratio between them (right), in 2025 dollars.
The ratio rose from 4.1× in 1989 to 6.2× in 2025; its low point was 2.8× in 1995.
**`figures/wealth_gap_by_age.png`** repeats the comparison within age groups of
the household head. Shaded areas are 95% confidence intervals.

## Data

Federal Reserve Board, [Survey of Consumer Finances](https://www.federalreserve.gov/econres/scfindex.htm)
(SCF), every survey from 1989 to 2025 (the 2025 survey was released Oct. 9, 2026):

- **Summary Extract Public Data** (CSV, one file per survey year). The Fed has
  restated every year in 2025 dollars.
- **Replicate weights**, used for the confidence intervals.
- **Historic Tables** (Table 4) and the Fed's published standard errors, used to
  check our numbers.

Notes:

- The "household head" is the SCF reference person.
- Medians are weighted and pool all five imputation implicates. They match the
  Fed's Table 4 exactly.
- Confidence intervals follow the Fed's
  [standard-error method](https://www.federalreserve.gov/econres/files/standard_error_documentation.pdf).
- Net worth excludes Social Security and defined-benefit pensions. The results
  describe the gap; they don't measure what a degree causes.

## Rerunning

Requires Python 3.9+.

```bash
pip install -r requirements.txt
python get_data.py     # download the SCF files to data/raw/ (~400 MB; skips files already there)
python estimates.py    # compute medians, ratios and CIs -> data/networth_by_education*.csv
python plot.py         # draw the figures -> figures/
```

`estimates.py` stops with an error if any estimate doesn't match the Fed's
published tables.

To export one survey year's records (one row per family per implicate) to CSV:

```bash
python export_year.py 1998   # -> data/scf1998_records.csv
```
