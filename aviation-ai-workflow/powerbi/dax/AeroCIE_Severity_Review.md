# AeroCIE severity review | Power BI import measures

Import the `v_severity_scenarios.csv` export from the synthetic SQLite pipeline as a new table named `v_severity_scenarios`. Use integer or decimal types for the three scenario columns and `requested_hull_value_usd`. The existing PBIP model remains a starter; validate the resulting measures in Power BI Desktop.

```DAX
Scenario Base Stress USD =
SUM ( 'v_severity_scenarios'[scenario_base_usd] )

Scenario High Stress USD =
SUM ( 'v_severity_scenarios'[scenario_high_usd] )

Submissions Requiring Evidence =
CALCULATE (
    DISTINCTCOUNT ( 'v_severity_scenarios'[submission_id] ),
    'v_severity_scenarios'[insufficient_evidence] = 1
)

Scenario Data Coverage =
DIVIDE (
    CALCULATE ( COUNTROWS ( 'v_severity_scenarios' ),
        NOT ISBLANK ( 'v_severity_scenarios'[scenario_base_usd] ) ),
    COUNTROWS ( 'v_severity_scenarios' )
)
```

The scenario amounts are illustrative sensitivity values, not expected loss, claim reserves or unpriced insurance premiums. Avoid displaying a sum as loss exposure across repeated overlapping cases or duplicated imports. A production semantic model should use a unique submission dimension and single-record filtering.

**SQL arithmetic:** Low = 100 × MRO wait proxy + requested hull × 0.0025 × positive parts cost index above 1.0; Base uses 250 and 0.005; High uses 500 and 0.01. These parameters are examples and have no actuarial calibration.
