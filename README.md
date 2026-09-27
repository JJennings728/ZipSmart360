# ZIPSmart360

**ZIP-level analytics pipeline for reproducible data validation, SQL analysis, API access, and decision-support reporting.**

[Portfolio](PORTFOLIO.md) · [Evaluation Memo](PORTFOLIO_EVALUATION.md) · [Architecture](docs/architecture.md) · [Data Dictionary](docs/data-dictionary.md)

## Overview

ZIPSmart360 is a runnable data-engineering portfolio project that turns structured geographic records into validated, queryable analytical outputs.

The project demonstrates an end-to-end workflow:

**CSV input → validation → SQLite → SQL analysis → JSON/CSV exports → local API → interactive dashboard**

The implementation is intentionally lightweight and reproducible. It uses Python 3.10+ and the standard library, requires no API keys or paid services, and can be run locally by a reviewer.

## Capabilities

| Area | Implementation |
| --- | --- |
| Data ingestion | CSV parsing with explicit schema expectations |
| Validation | Required fields, identifier integrity, duplicate detection, numeric-domain checks, finite-value checks, year consistency |
| Relational storage | SQLite schema with primary key, CHECK constraints, and state index |
| SQL analytics | Explicit grouped aggregations in versioned SQL files |
| API | Local JSON endpoints with parameter validation and HTTP error handling |
| Reporting | CSV, JSON, quality report, and interactive HTML dashboard |
| Verification | Seven automated test methods covering calculations, repeatability, invalid input, SQL parameterization, and HTTP behavior |
| Documentation | Architecture notes, data dictionary, setup instructions, and example outputs |

## Run locally

```bash
git clone https://github.com/JJennings728/ZipSmart360.git
cd ZipSmart360

python -m unittest discover -s tests -v
python zipsmart.py
python server.py
```

On Windows, `py` can be used instead of `python`.

Open:

```text
http://127.0.0.1:8000
```

The generated dashboard can also be opened directly from `build/dashboard.html`.

## API surface

| Endpoint | Purpose |
| --- | --- |
| `/api/health` | Service status and record count |
| `/api/zips` | Retrieve all demonstration records |
| `/api/zips?state=IA` | Filter records by state |
| `/api/zip?zip=00501` | Retrieve one ZIP while preserving leading zeros |

The API validates inputs and returns explicit 400, 404, and 503 responses for supported error conditions.

## Data-quality design

ZIPSmart360 treats identifiers and analytical semantics deliberately.

ZIP codes are stored as text so values such as `00501` are not corrupted. Invalid datasets are rejected before replacing the existing SQLite database. Repeated builds from the same input generate identical text outputs.

The project also distinguishes between technically valid calculations and valid interpretation. For example, the arithmetic mean of ZIP-level household-income medians is not represented as a state median household income.

## Repository structure

```text
ZipSmart360/
├── data/                  # Synthetic input fixture
├── docs/                  # Architecture, data dictionary, dashboard preview
├── examples/              # Checked-in reference outputs
├── sql/                   # Schema and analytical SQL
├── tests/                 # Automated verification
├── web/                   # Dashboard template
├── server.py              # Local JSON API
└── zipsmart.py            # Validation, build, analysis, and export pipeline
```

## Portfolio context

ZIPSmart360 is the executable software-engineering anchor for a broader portfolio spanning:

- applied AI and agent workflow design;
- commercial insurance exposure-data engineering;
- facultative reinsurance pricing;
- aviation underwriting analytics; and
- data architecture.

See the [full portfolio](PORTFOLIO.md).

## Scope and limitations

This repository uses 12 explicitly synthetic records. It is a portfolio demonstration, not a production geographic-risk platform, actuarial model, carrier system, or commercial API.

The local server binds to `127.0.0.1` and does not implement production authentication, billing, rate limiting, observability, or cloud deployment.

AI assistance was used in development. The repository is published so the implementation, tests, assumptions, and design decisions can be inspected directly.

## Author

**James Jennings**  
Applied AI · Risk Analytics · Data Engineering · Insurance

[LinkedIn](https://www.linkedin.com/in/james-jennings-2053b4a8) · [GitHub](https://github.com/JJennings728)
