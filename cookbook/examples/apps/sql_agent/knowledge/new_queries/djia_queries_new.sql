-- </query>

-- <query description>
-- Calculate average daily trading volume for a specific stock in a year
-- </query description>
-- <query>
SELECT 
    AVG("Volume") as avg_daily_volume
FROM prices 
WHERE "Ticker" = :ticker 
    AND EXTRACT(YEAR FROM "Date") = :year;
-- </query>

-- <query description>
-- Calculate percentage price change for a specific stock in a year (comparing first and last price)
-- </query description>
-- <query>
SELECT 
    ROUND((((l."Close" - f."Close") / f."Close") * 100)::numeric, 2) AS price_change_percentage
FROM 
    (SELECT "Close" FROM prices WHERE "Ticker" = :ticker AND DATE_PART('year', "Date") = :year ORDER BY "Date" ASC LIMIT 1) f,
    (SELECT "Close" FROM prices WHERE "Ticker" = :ticker AND DATE_PART('year', "Date") = :year ORDER BY "Date" DESC LIMIT 1) l;
-- </query>

-- <query description>
-- Compare total dividends between two companies in a specific year
-- </query description>
-- <query>
SELECT "Ticker", SUM("Dividends") as total_dividends 
FROM prices 
WHERE "Ticker" IN (:ticker1, :ticker2) 
AND EXTRACT(YEAR FROM "Date") = :year 
GROUP BY "Ticker";
-- </query>

-- <query description>
-- Calculate average dividend yield for all DJIA companies in a specific year
-- </query description>
-- <query>
WITH per_ticker_yield AS (
    SELECT 
        "Ticker", 
        SUM("Dividends") / NULLIF(AVG("Close"), 0) AS yield
    FROM prices
    WHERE "Date" BETWEEN :start_date AND :end_date
    GROUP BY "Ticker"
)
SELECT ROUND(AVG(yield)::numeric * 100, 2) AS avg_dividend_yield_percent
FROM per_ticker_yield;
-- </query>

-- <query description>
-- Find the company with the lowest volatility (standard deviation of daily returns) in a specific year
-- </query description>
-- <query>
WITH daily_returns AS (
    SELECT 
        "Ticker",
        "Date",
        ("Close" - LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date")) / 
        LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date") as daily_return
    FROM prices
    WHERE "Date" BETWEEN :start_date AND :end_date
)
SELECT 
    "Ticker",
    ROUND(STDDEV(daily_return)::numeric * 100, 2) as volatility_percent
FROM daily_returns
GROUP BY "Ticker"
ORDER BY volatility_percent ASC
LIMIT 1;
-- </query>

-- <query description>
-- Find the company with the highest single-day percentage drop in a specific year
-- </query description>
-- <query>
WITH daily_returns AS (
  SELECT
    "Ticker",
    "Date",
    (("Close" - LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date")) 
     / LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date")) * 100 AS daily_return_pct
  FROM prices
  WHERE "Date" BETWEEN :start_date AND :end_date
)
SELECT
  "Ticker",
  "Date",
  ROUND(daily_return_pct::numeric, 4) AS daily_return_pct
FROM daily_returns
WHERE daily_return_pct IS NOT NULL
ORDER BY daily_return_pct ASC NULLS LAST
LIMIT 1;
-- </query>

-- <query description>
-- Find the company with the highest single-day percentage gain in a specific year
-- </query description>
-- <query>
WITH daily_returns AS (
  SELECT
    "Ticker",
    "Date",
    (("Close" - LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date")) 
     / LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date")) * 100 AS daily_return_pct
  FROM prices
  WHERE "Date" BETWEEN :start_date AND :end_date
)
SELECT
  "Ticker",
  "Date",
  ROUND(daily_return_pct::numeric, 4) AS daily_return_pct
FROM daily_returns
WHERE daily_return_pct IS NOT NULL
ORDER BY daily_return_pct DESC NULLS LAST
LIMIT 1;
-- </query>


-- <query description>
-- Get closing price data for plotting stock price chart
-- </query description>
-- <query>
SELECT 
    "Date" as date,
    "Close" as close
FROM prices 
WHERE "Ticker" = :ticker 
    AND "Date" BETWEEN :start_date AND :end_date
ORDER BY "Date";
-- </query>