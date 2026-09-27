# Data dictionary

Source: an invented fixture committed as `data/sample_zip_data.csv`. No external dataset or personal data is included. The demo intentionally rejects rows whose `data_type` is not `synthetic`.

| Field | Type / unit | Validation |
| --- | --- | --- |
| zip_code | Text identifier | Exactly five ASCII digits; unique; leading zeros retained |
| state | Text | Uppercase US state abbreviation or DC; no geographic cross-check |
| population | Integer count | Nonnegative |
| households | Integer count | Between zero and population |
| median_household_income | Numeric USD per year | Finite, nonnegative, invented ZIP-level median |
| unemployment_pct | Numeric percentage points | Finite, 0–100; 4.2 means 4.2%, not 420% |
| data_year | Integer | 1900–2100; same year for every row; illustrative only |
| data_type | Text | Must equal `synthetic` |

## Quality decisions

- Reject the file rather than silently drop invalid records.
- Require the exact documented header order and no missing or extra fields.
- Keep ZIP identifiers as text throughout CSV, SQLite, JSON, and HTML.
- Never replace an existing database when input validation fails.
- Keep data-source limitations visible beside results.

## Summary definitions

`sample_zip_count`: number of rows grouped by state.

`sample_population` and `sample_households`: sums within those rows, not state estimates.

`mean_of_zip_income_medians`: unweighted mean across ZIP-level income medians. A population median cannot be reconstructed from these medians alone. The pipeline deliberately does not aggregate unemployment percentages without labor-force denominators.
