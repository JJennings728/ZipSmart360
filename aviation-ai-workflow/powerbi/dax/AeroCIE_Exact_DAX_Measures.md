# AeroCIE Underwriting KPI library | DAX

In Power BI Desktop, import `v_submission_features.csv` and `v_mro_latest.csv` as tables with these exact names. Add the following measures to `v_submission_features`. These measures calculate research heuristics only and must be displayed with underwriter review authority.

## MRO_Severity_Index

```dax
MRO_Severity_Index =
VAR _Make = SELECTEDVALUE ( 'v_submission_features'[manufacturer] )
VAR _Model = SELECTEDVALUE ( 'v_submission_features'[model] )
RETURN
    IF (
        ISBLANK ( _Make ) || ISBLANK ( _Model ),
        BLANK (),
        CALCULATE (
            DIVIDE (
                SUMX (
                    'v_mro_latest',
                    'v_mro_latest'[repair_wait_days] *
                        ( 2 - 'v_mro_latest'[parts_availability_index] )
                ),
                SUMX (
                    'v_mro_latest',
                    2 - 'v_mro_latest'[parts_availability_index]
                )
            ),
            REMOVEFILTERS ( 'v_mro_latest' ),
            TREATAS (
                ROW ( "Make", _Make, "Model", _Model ),
                'v_mro_latest'[manufacturer],
                'v_mro_latest'[model]
            )
        )
    )
```

## Triage_Risk_Points

```dax
Triage_Risk_Points =
VAR _Age = SELECTEDVALUE ( 'v_submission_features'[aircraft_age_years] )
VAR _Hours = SELECTEDVALUE ( 'v_submission_features'[total_flight_hours] )
VAR _TypeTime = SELECTEDVALUE ( 'v_submission_features'[make_model_hours] )
VAR _Losses = SELECTEDVALUE ( 'v_submission_features'[losses_last_five_years] )
VAR _Composite = SELECTEDVALUE ( 'v_submission_features'[composite_material_flag] )
VAR _Training = SELECTEDVALUE ( 'v_submission_features'[recurrent_training_verified] )
VAR _Utilization = SELECTEDVALUE ( 'v_submission_features'[annual_flight_hours] )
VAR _MRO = [MRO_Severity_Index]
VAR _EvidenceMissing = SELECTEDVALUE ( 'v_submission_features'[insufficient_evidence], 1 )
VAR _SingleSubmission = HASONEVALUE ( 'v_submission_features'[submission_id] )
VAR _Missing =
    NOT _SingleSubmission || _EvidenceMissing <> 0 ||
    ISBLANK ( _Age ) || ISBLANK ( _Hours ) || ISBLANK ( _TypeTime ) ||
    ISBLANK ( _Losses ) || ISBLANK ( _Composite ) || ISBLANK ( _Training ) ||
    ISBLANK ( _Utilization ) || ISBLANK ( _MRO )
VAR _AgePoints = SWITCH ( TRUE (), _Age > 30, 20, _Age > 15, 10, 0 )
VAR _HoursPoints = SWITCH ( TRUE (), _Hours < 500, 18, _Hours < 1500, 8, 0 )
VAR _TypePoints = SWITCH ( TRUE (), _TypeTime < 25, 18, _TypeTime < 100, 8, 0 )
VAR _LossPoints = SWITCH ( TRUE (), _Losses >= 2, 30, _Losses = 1, 15, 0 )
VAR _MROPoints = SWITCH ( TRUE (), _MRO > 60, 20, _MRO > 30, 10, 0 )
VAR _CompositePoints = IF ( _Composite = 1, 5, 0 )
VAR _TrainingPoints = IF ( _Training = 0, 10, 0 )
RETURN
    IF ( _Missing, BLANK (),
        MIN ( 100, _AgePoints + _HoursPoints + _TypePoints +
            _LossPoints + _MROPoints + _CompositePoints + _TrainingPoints )
    )
```

## Automated_Triage_Status

```dax
Automated_Triage_Status =
VAR _RiskPoints = [Triage_Risk_Points]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( _RiskPoints ), "Refer",
        _RiskPoints <= 25, "Quote",
        _RiskPoints >= 70, "Decline",
        "Refer"
    )
```

## Submissions

```dax
Submissions =
COUNTROWS ( 'v_submission_triage' )
```

## Refer_Count

```dax
Refer_Count =
CALCULATE ( COUNTROWS ( 'v_submission_triage' ), 'v_submission_triage'[triage_recommendation] = "Refer" )
```

## Automated_Triage_Score

```dax
Automated_Triage_Score =
[Triage_Risk_Points]
```

The DAX eligibility gate reads `insufficient_evidence` from SQLite; this includes missing or stale MRO source observations. The calculated measure is defined for exactly one selected submission. Multiple selections produce a blank score and a Refer label. Compare DAX and SQL scoring for the same submission during Windows Power BI review.

The MRO weight is `2 - parts_availability_index` so a lower availability means higher repair wait-time weighting. The MRO result is measured in days; it is not an actuarial loss severity estimate.
