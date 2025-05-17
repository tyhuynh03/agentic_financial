-- Sample queries for DJIA data analysis

-- <query description>
-- Get the latest stock prices for all companies
-- </query description>
-- <query>
SELECT 
    c.name,
    p.Ticker,
    p.Date,
    p.Close,
    p.Volume
FROM companies c
JOIN prices p ON c.symbol = p.Ticker
WHERE p.Date = (SELECT MAX(Date) FROM prices)
ORDER BY p.Close DESC;
-- </query>

-- <query description>
-- Find companies with highest dividend yield in each sector
-- </query description>
-- <query>
WITH ranked_dividends AS (
    SELECT 
        name,
        symbol,
        sector,
        dividend_yield,
        ROW_NUMBER() OVER (PARTITION BY sector ORDER BY dividend_yield DESC) as rank
    FROM companies
    WHERE dividend_yield > 0
)
SELECT 
    name,
    symbol,
    sector,
    dividend_yield
FROM ranked_dividends
WHERE rank = 1
ORDER BY dividend_yield DESC;
-- </query>

-- <query description>
-- Calculate 30-day moving average for each stock
-- </query description>
-- <query>
SELECT 
    p.Ticker,
    c.name,
    p.Date,
    p.Close,
    AVG(p.Close) OVER (
        PARTITION BY p.Ticker 
        ORDER BY p.Date 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) as moving_avg_30d
FROM prices p
JOIN companies c ON p.Ticker = c.symbol
WHERE p.Date >= CURRENT_DATE - INTERVAL '60 days'
ORDER BY p.Ticker, p.Date;
-- </query>

-- <query description>
-- Find stocks with highest trading volume in the last week
-- </query description>
-- <query>
SELECT 
    p.Ticker,
    c.name,
    SUM(p.Volume) as total_volume
FROM prices p
JOIN companies c ON p.Ticker = c.symbol
WHERE p.Date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY p.Ticker, c.name
ORDER BY total_volume DESC
LIMIT 10;
-- </query>

-- <query description>
-- Compare current price to 52-week high/low for each stock
-- </query description>
-- <query>
WITH latest_prices AS (
    SELECT 
        Ticker,
        Close as current_price,
        Date
    FROM prices
    WHERE Date = (SELECT MAX(Date) FROM prices)
)
SELECT 
    c.name,
    c.symbol,
    lp.current_price,
    c."52_week_high",
    c."52_week_low",
    ROUND((lp.current_price - c."52_week_low") / (c."52_week_high" - c."52_week_low") * 100, 2) as price_position_percent
FROM companies c
JOIN latest_prices lp ON c.symbol = lp.Ticker
ORDER BY price_position_percent DESC;
-- </query>

-- <query description>
-- Compare stock performance between technology and healthcare sectors
-- </query description>
-- <query>
SELECT 
    c.sector,
    AVG(prices."Close") as avg_price,
    MAX(prices."Close") as max_price,
    MIN(prices."Close") as min_price,
    COUNT(DISTINCT c.symbol) as num_companies
FROM prices
JOIN companies c ON prices."Ticker" = c.symbol
WHERE c.sector IN ('Technology', 'Healthcare')
GROUP BY c.sector
ORDER BY avg_price DESC;
-- </query>

-- <query description>
-- Get the daily trading volume for Apple stock (AAPL)
-- </query description>
-- <query>
SELECT 
    "Date", 
    "Volume" 
FROM prices 
WHERE "Ticker" = 'AAPL' 
ORDER BY "Date" DESC 
LIMIT 30;
-- </query> 