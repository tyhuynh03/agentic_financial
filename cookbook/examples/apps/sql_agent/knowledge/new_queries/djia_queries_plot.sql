-- <query description>
-- Get daily returns data for plotting histogram (plot histogram of daily returns)
-- </query description>
-- <query>
WITH daily_prices AS (
    SELECT 
        "Date",
        "Close",
        LAG("Close") OVER (ORDER BY "Date") as prev_close
    FROM prices 
    WHERE "Ticker" = :ticker 
        AND "Date" >= :start_date 
        AND "Date" <= :end_date
)
SELECT 
    "Date",
    CAST(ROUND((("Close" - prev_close) / prev_close * 100)::numeric, 2) AS FLOAT) as daily_return
FROM daily_prices
WHERE prev_close IS NOT NULL
ORDER BY "Date";
-- </query>

-- <query description>
-- Get closing price data for plotting time series
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
