-- Sample-only totals; these are not state population estimates.
-- Mean of ZIP-level medians is NOT a statewide median household income.
SELECT state,
       COUNT(*) AS sample_zip_count,
       SUM(population) AS sample_population,
       SUM(households) AS sample_households,
       ROUND(AVG(median_household_income), 2) AS mean_of_zip_income_medians
FROM zip_metrics
GROUP BY state
ORDER BY state;
