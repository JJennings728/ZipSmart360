# Northstar Calibration Methodology

## Objective

Create a realistic major-U.S.-airline insurance model without claiming access to confidential airline or broker placement data.

## Public facts used

### Fleet

United Airlines' 2025 Form 10-K reports a 1,066-aircraft mainline fleet with detailed aircraft-type counts.

Northstar uses only the user-selected families and proportionally scales those counts to exactly 1,050 aircraft.

### Traffic

United reported approximately 181.1m passengers and 271.6bn RPM in 2025.

Northstar uses approximately 98.5% of those exposures to reflect its 1,050-aircraft scale:

- passengers: 178m
- RPM: 267bn

### Insurance allocation methodology

Public United capacity-purchase contracts describe:

- hull / war premium allocation from composite rates applied to average fleet value;
- liability allocation from composite liability rates applied to RPM; and
- war liability allocation using RPM and onboard passengers.

Northstar uses the same general architecture.

### Self-insurance constraint

Public United aircraft-financing documents permit fleet-wide self-insurance tied to aggregate insurable value, with the 2024-1 documents using a 1% formula, subject to broker certification for higher industry-standard levels and separate industry-standard per-aircraft deductibles.

Northstar uses:

- 1.00% of TIV as a public-reference ceiling;
- 0.50% of TIV as the central synthetic retained-layer estimate.

### Global airline premium cross-check

Cirium estimated approximately $1.62bn of global airline all-risk hull and liability net written premium for 2024.

Northstar's modeled hull + liability premium of approximately $71.0m is 4.38% of that pool.

This is used only as a reasonableness test.

## Confidence levels

| Item | Confidence |
|---|---|
| United fleet counts | High — SEC filing |
| United passenger / RPM exposure | High — SEC filing |
| Insurance allocation methodology | High — public contracts |
| Public self-insurance formula constraint | High — SEC financing documents |
| Northstar aircraft agreed values | Medium — synthetic market-style assumptions |
| Northstar annual premium | Medium / low — reverse-engineered estimate |
| Northstar actual-style SIR | Medium / low — derived, not disclosed |
| Hull War / AVN52 price | Low / medium — synthetic |
| Reinsurance treaty structure | Low — entirely synthetic |

## Rule

Never present a reverse-engineered figure as a disclosed United Airlines insurance term.
