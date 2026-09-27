CREATE TABLE zip_metrics (
    zip_code TEXT PRIMARY KEY CHECK(length(zip_code) = 5 AND zip_code NOT GLOB '*[^0-9]*'),
    state TEXT NOT NULL CHECK(length(state) = 2),
    population INTEGER NOT NULL CHECK(population >= 0),
    households INTEGER NOT NULL CHECK(households >= 0 AND households <= population),
    median_household_income REAL NOT NULL CHECK(median_household_income >= 0),
    unemployment_pct REAL NOT NULL CHECK(unemployment_pct BETWEEN 0 AND 100),
    data_year INTEGER NOT NULL CHECK(data_year BETWEEN 1900 AND 2100),
    data_type TEXT NOT NULL CHECK(data_type = 'synthetic')
);
CREATE INDEX idx_zip_metrics_state ON zip_metrics(state);
