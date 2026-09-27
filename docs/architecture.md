# Architecture and design decisions

The pipeline reads the committed synthetic CSV, validates the entire file, loads a temporary SQLite database, runs an explicit SQL summary, and replaces the previous database only after successful ingestion. It then writes presentation exports. The local API reads the database in read-only mode.

| Layer | Responsibility | Files |
| --- | --- | --- |
| Input | Reproducible invented fixture | `data/sample_zip_data.csv` |
| Validation | Identity, completeness, numeric domains, duplicate checks | `validate_csv` in `zipsmart.py` |
| Storage | Typed constraints and state lookup index | `sql/schema.sql` |
| Analysis | Transparent, reproducible aggregation | `sql/state_summary.sql` |
| Reporting | CSV, JSON, quality report, standalone HTML | `build` in `zipsmart.py`, `web/dashboard.html` |
| Access | Loopback-only read endpoints | `server.py` |

## Tradeoffs

- **SQLite and standard library:** easy for a reviewer to reproduce without cloud credentials or package installation; not a distributed production platform.
- **Strict rejection:** makes errors visible rather than hiding them through imputation; source cleanup is a separate responsibility.
- **Parameterized queries:** user input cannot change SQL syntax.
- **Synthetic-only input:** permits transparent demonstration without presenting unverified data as real observations.
- **Static dashboard:** works offline and exposes all sample rows; unsuitable for confidential datasets.
- **Database replacement:** protects a previous database from failed validation/ingestion. Export files are written afterward, so the complete output directory is not a single atomic transaction. Re-run a build interrupted during export before serving it.

## Manual walkthrough for interviews

1. Run the build and show the quality report.
2. Explain why `00501` must be text.
3. Open the state summary SQL and verify the Iowa sample population total of 35,700.
4. Explain why averaging area medians does not yield a state median.
5. Filter the dashboard to Iowa and request the same records through `/api/zips?state=IA`.
6. Change a fixture value in a temporary copy to demonstrate rejection, then run the tests.
7. Distinguish the implemented local demo from possible commercial product features.
