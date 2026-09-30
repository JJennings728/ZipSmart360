-- E&S Commercial Property Underwriting Portfolio
-- Synthetic demonstration only; not carrier pricing or actuarial guidance.

DROP VIEW IF EXISTS vw_underwriting_model;

CREATE VIEW vw_underwriting_model AS
SELECT SubmissionID, Broker, State, Industry, Occupancy, Construction, YearBuilt,
       (2026 - YearBuilt) AS BuildingAge, SprinklerPct, TIV, [Limit], Deductible,
       CATScore, LossRatio3Yr, HazardGrade, RequestedRatePer100, QuotedRatePer100,
       ROUND(TIV * QuotedRatePer100 / 100.0, 2) AS QuotedPremium,
       ROUND((QuotedRatePer100 - RequestedRatePer100) / NULLIF(RequestedRatePer100,0), 4) AS RateChangePct,
       CASE WHEN CATScore >= 8 THEN 1 ELSE 0 END AS HighCATFlag,
       CASE WHEN TIV >= 25000000 THEN 1 ELSE 0 END AS LargeAccountFlag,
       Decision, ReferralReason
FROM submissions;

-- Portfolio KPI summary
SELECT COUNT(*) AS SubmissionCount, SUM(TIV) AS TotalTIV, SUM([Limit]) AS TotalLimit,
       SUM(ROUND(TIV * QuotedRatePer100 / 100.0, 2)) AS QuotedPremium,
       AVG(QuotedRatePer100) AS AvgQuotedRatePer100, AVG(CATScore) AS AvgCATScore,
       AVG(LossRatio3Yr) AS AvgLossRatio3Yr,
       SUM(CASE WHEN Decision='Quote' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS QuoteRate,
       SUM(CASE WHEN Decision='Refer' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS ReferralRate,
       SUM(CASE WHEN Decision='Decline' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS DeclineRate
FROM vw_underwriting_model;

-- State concentration
SELECT State, COUNT(*) AS Submissions, SUM(TIV) AS TIV, SUM(QuotedPremium) AS QuotedPremium
FROM vw_underwriting_model GROUP BY State ORDER BY TIV DESC;

-- Referral queue
SELECT SubmissionID, Broker, State, Occupancy, TIV, CATScore, LossRatio3Yr, HazardGrade,
       QuotedRatePer100, ReferralReason
FROM vw_underwriting_model WHERE Decision='Refer'
ORDER BY CATScore DESC, TIV DESC;