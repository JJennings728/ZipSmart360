# Data Dictionary — E&S Commercial Property Underwriting

All records are synthetic and created solely for portfolio demonstration.

| Field | Type | Definition | Analytical use |
|---|---|---|---|
| SubmissionID | Text | Synthetic submission identifier | Primary key |
| Broker | Text | Synthetic wholesale/specialty broker | Broker mix analysis |
| State | Text | U.S. state abbreviation | Geographic concentration |
| Industry | Text | Broad industry class | Portfolio segmentation |
| Occupancy | Text | Primary property occupancy | Hazard/appetite segmentation |
| Construction | Text | Simplified construction class | Property vulnerability proxy |
| YearBuilt | Integer | Construction year | Age analysis |
| SprinklerPct | Decimal | Percent sprinkler protection | Protection adequacy indicator |
| TIV | Currency | Total insured value | Exposure / authority / concentration |
| Limit | Currency | Requested property limit | Capacity requirement |
| Deductible | Currency | Property deductible | Risk-sharing indicator |
| CATScore | Integer 1-10 | Synthetic catastrophe severity score | Referral and concentration screening |
| LossRatio3Yr | Decimal | Synthetic three-year loss ratio | Historical loss-quality indicator |
| HazardGrade | Text A-D | Synthetic hazard grade | Appetite / referral screening |
| RequestedRatePer100 | Decimal | Requested property rate per $100 TIV | Market pricing context |
| QuotedRatePer100 | Decimal | Demonstration quoted rate per $100 TIV | Premium analytics |
| Decision | Text | Quote, Refer, or Decline | Workflow outcome |
| ReferralReason | Text | Primary review trigger | Human-review transparency |

## Derived measures

- Quoted Premium = TIV × QuotedRatePer100 ÷ 100
- Rate Change % = (QuotedRatePer100 - RequestedRatePer100) ÷ RequestedRatePer100
- Building Age = 2026 - YearBuilt
- High CAT = CATScore >= 8
- Large Account = TIV >= $25,000,000

These formulas are demonstrative and are not actuarial indications, filed rates, carrier guidelines, or binding authority.