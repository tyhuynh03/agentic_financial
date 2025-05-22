-- <query description>
--  30-day moving average closing price for a specific stock on a specific date
-- </query description>
-- <query>
SELECT *
FROM (
    SELECT 
        "Date",
        "Ticker",
        ROUND(AVG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date" ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)::numeric, 2) AS moving_avg_30d
    FROM prices
    WHERE "Ticker" = :ticker
) sub
WHERE "Date" = :date;
-- </query>

-- <query description>
-- Find the week with highest trading volume for a specific stock in a specific year
-- </query description>
-- <query>
SELECT 
    DATE_TRUNC('week', "Date") AS week_start,
    SUM("Volume") AS weekly_volume
FROM 
    prices
WHERE 
    "Ticker" = :ticker AND
    DATE_TRUNC('year', "Date") = DATE :year
GROUP BY 
    DATE_TRUNC('week', "Date")
ORDER BY 
    weekly_volume DESC
LIMIT 1;
-- </query>

-- <query description>
-- Calculate cumulative return for a stock between two dates
-- </query description>
-- <query>
SELECT 
    ROUND(
        ((end_price."Close" - start_price."Close") / start_price."Close" * 100)::numeric, 2
    ) AS cumulative_return_percentage
FROM 
    (SELECT "Close" FROM prices WHERE "Ticker" = :ticker AND "Date" = :start_date LIMIT 1) AS start_price,
    (SELECT "Close" FROM prices WHERE "Ticker" = :ticker AND "Date" = :end_date LIMIT 1) AS end_price;
-- </query>

-- <query description>
-- Find company with highest average trading volume in a specific year
-- </query description>
-- <query>
SELECT 
    p."Ticker",
    c.name,
    ROUND(AVG(p."Volume")::numeric, 0) as avg_daily_volume
FROM 
    prices p
    JOIN companies c ON p."Ticker" = c.symbol
WHERE 
    DATE_TRUNC('year', p."Date") = DATE :year
GROUP BY 
    p."Ticker", c.name
ORDER BY 
    avg_daily_volume DESC
LIMIT 1;
-- </query>

-- <query description>
-- Find company with lowest volatility (standard deviation of daily returns) in a specific year
-- </query description>
-- <query>
WITH daily_returns AS (
    SELECT 
        "Ticker",
        "Date",
        ("Close" - LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date")) / 
        LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date") as daily_return
    FROM prices
    WHERE DATE_TRUNC('year', "Date") = DATE :year
)
SELECT 
    dr."Ticker",
    c.name,
    ROUND(STDDEV(dr.daily_return)::numeric * 100, 2) as volatility_percentage
FROM 
    daily_returns dr
    JOIN companies c ON dr."Ticker" = c.symbol
WHERE 
    dr.daily_return IS NOT NULL
GROUP BY 
    dr."Ticker", c.name
ORDER BY 
    volatility_percentage ASC
LIMIT 1;
-- </query>

-- <query description>
-- Rank top 3 companies by total return in a specific year
-- </query description>
-- <query>
WITH start_prices AS (
    SELECT "Ticker", "Close" AS start_price
    FROM prices
    WHERE "Date" = :start_date
),
end_prices AS (
    SELECT "Ticker", "Close" AS end_price
    FROM prices
    WHERE "Date" = :end_date
),
returns AS (
    SELECT 
        s."Ticker",
        ROUND(((e.end_price - s.start_price) / s.start_price * 100)::numeric, 2) AS total_return_pct
    FROM start_prices s
    JOIN end_prices e ON s."Ticker" = e."Ticker"
)
SELECT 
    r."Ticker",
    c."name" AS company_name,
    r.total_return_pct
FROM returns r
LEFT JOIN companies c ON r."Ticker" = c."symbol"
ORDER BY total_return_pct DESC
LIMIT 3;
-- </query>

-- <query description>
-- Calculate median closing price for a stock in a specific year
-- </query description>
-- <query>
SELECT 
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "Close")::numeric, 2) AS median_close_price
FROM prices
WHERE "Ticker" = :ticker
  AND "Date" BETWEEN :start_date AND :end_date;
-- </query>

-- <query description>
-- Calculate compound annual growth rate (CAGR) for a stock between two dates
-- </query description>
-- <query>
WITH date_prices AS (
    SELECT "Date", "Close"
    FROM prices
    WHERE "Ticker" = :ticker
      AND "Date" BETWEEN :start_date AND :end_date
),
first_last AS (
    SELECT 
        (SELECT "Close" FROM date_prices ORDER BY "Date" ASC LIMIT 1) AS first_price,
        (SELECT "Close" FROM date_prices ORDER BY "Date" DESC LIMIT 1) AS last_price,
        (EXTRACT(DAY FROM (MAX("Date") - MIN("Date"))) / 365.25)::numeric AS years
    FROM date_prices
)
SELECT 
    ROUND(
        ((POWER(last_price / first_price, 1.0 / NULLIF(years, 0)) - 1) * 100)::numeric,
        2
    ) AS cagr_percentage
FROM first_last;
-- </query>

-- <query description>
-- Calculate stock's beta relative to DJIA index for a specific year
-- </query description>
-- <query>
WITH daily_returns AS (
    SELECT 
        "Date",
        "Ticker",
        ("Close" - LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date")) / 
        LAG("Close") OVER (PARTITION BY "Ticker" ORDER BY "Date") as daily_return
    FROM prices
    WHERE "Date" BETWEEN :start_date AND :end_date
),
market_returns AS (
    SELECT 
        "Date",
        AVG(daily_return) as market_return
    FROM daily_returns
    GROUP BY "Date"
),
stock_market_returns AS (
    SELECT 
        s."Date",
        s.daily_return as stock_return,
        m.market_return
    FROM daily_returns s
    JOIN market_returns m ON s."Date" = m."Date"
    WHERE s."Ticker" = :ticker
    AND s.daily_return IS NOT NULL
    AND m.market_return IS NOT NULL
)
SELECT 
    ROUND(
        (COVAR_POP(stock_return, market_return) / VAR_POP(market_return))::numeric,
        2
    ) as beta
FROM stock_market_returns;
-- </query>

-- <query description>
-- Calculate annualized volatility for a stock in a specific year
-- </query description>
-- <query>
WITH daily_returns AS (
    SELECT 
        ("Close" - LAG("Close") OVER (ORDER BY "Date")) / 
        LAG("Close") OVER (ORDER BY "Date") as daily_return
    FROM prices
    WHERE "Ticker" = :ticker
    AND "Date" BETWEEN :start_date AND :end_date
)
SELECT 
    ROUND(
        (STDDEV(daily_return) * SQRT(252) * 100)::numeric,
        2
    ) as annualized_volatility
FROM daily_returns
WHERE daily_return IS NOT NULL;
-- </query>

-- <query description>
-- Calculate correlation between daily returns of two stocks in a specific year
-- </query description>
-- <query>
WITH stock1_returns AS (
    SELECT 
        "Date",
        ("Close" - LAG("Close") OVER (ORDER BY "Date")) / 
        LAG("Close") OVER (ORDER BY "Date") as daily_return
    FROM prices
    WHERE "Ticker" = :ticker1
    AND "Date" BETWEEN :start_date AND :end_date
),
stock2_returns AS (
    SELECT 
        "Date",
        ("Close" - LAG("Close") OVER (ORDER BY "Date")) / 
        LAG("Close") OVER (ORDER BY "Date") as daily_return
    FROM prices
    WHERE "Ticker" = :ticker2
    AND "Date" BETWEEN :start_date AND :end_date
),
combined_returns AS (
    SELECT 
        s1.daily_return as return1,
        s2.daily_return as return2
    FROM stock1_returns s1
    JOIN stock2_returns s2 ON s1."Date" = s2."Date"
    WHERE s1.daily_return IS NOT NULL 
    AND s2.daily_return IS NOT NULL
)
SELECT 
    ROUND(
        CORR(return1, return2)::numeric,
        2
    ) as correlation
FROM combined_returns;
-- </query>

-- <query description>
-- Count trading days where closing price is within one standard deviation of mean
-- </query description>
-- <query>
WITH price_stats AS (
    SELECT 
        AVG("Close") as mean_price,
        STDDEV("Close") as std_price
    FROM prices
    WHERE "Ticker" = :ticker
    AND "Date" BETWEEN :start_date AND :end_date
)
SELECT 
    COUNT(*) as days_within_std
FROM prices p, price_stats ps
WHERE p."Ticker" = :ticker
AND p."Date" BETWEEN :start_date AND :end_date
AND p."Close" BETWEEN (ps.mean_price - ps.std_price) AND (ps.mean_price + ps.std_price);
-- </query>
