# Power BI Build Guide

## Fastest build path

1. Open Power BI Desktop.
2. Get data → Text/CSV and load ../data/submissions.csv as table Submissions.
3. Confirm field types using the data dictionary.
4. Create the measures in measures.dax.
5. Build the three report pages below.
6. Save as ES-Commercial-Property-Underwriting.pbix in this folder.
7. Optionally save a Power BI Project (.pbip) version for source control.

## Page 1 — Underwriting Executive View

KPI cards: Submission Count; Total TIV; Quoted Premium; Quote Rate; Referral Rate; Weighted CAT Score.
Visuals: TIV by State and Decision; premium by Industry; decision mix; top accounts by TIV.
Slicers: State, Industry, Decision, HazardGrade, Broker.

## Page 2 — Referral & Appetite

Matrix: Occupancy × HazardGrade. Scatter: CATScore vs LossRatio3Yr with bubble size = TIV and legend = Decision.
Add the referral queue, High CAT TIV %, and Average Deductible.

## Page 3 — Pricing & Portfolio Mix

Requested vs quoted rate scatter; average quoted rate by occupancy; quoted premium by broker; submission-level pricing table.

## Formatting

Use a restrained underwriting style, clear currency units, consistent percentage formatting, and explicit Synthetic Portfolio Demonstration labeling.

## PBIX integrity note

A genuine PBIX should be created and saved by Power BI Desktop. Do not rename or fabricate another file type as .pbix.