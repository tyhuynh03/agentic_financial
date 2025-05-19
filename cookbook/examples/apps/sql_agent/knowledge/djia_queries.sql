-- Sample queries for DJIA data analysis

-- <query description>
-- Get closing price for a specific stock on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON ("Date") "Close" 
FROM prices 
WHERE "Ticker" = :ticker AND "Date" = :date;
-- </query>

-- <query description>
-- Get closing price directly from company name and date
-- </query description>
-- <query>
SELECT DISTINCT ON (p."Date") p."Close" 
FROM prices p 
JOIN companies c ON p."Ticker" = c.symbol 
WHERE c.name LIKE '%' || :company_name || '%' 
AND p."Date" = :date;
-- </query>

-- <query description>
-- Get stock symbol from company name (exact match)
-- </query description>
-- <query>
SELECT DISTINCT ON (name) symbol, name 
FROM companies 
WHERE LOWER(name) = LOWER(:company_name) 
OR LOWER(name) LIKE LOWER(:company_name) || '%'
OR LOWER(name) LIKE '%' || LOWER(:company_name) || '%';
-- </query>

-- <query description>
-- Get stock symbol from company name
-- </query description>
-- <query>
SELECT symbol FROM companies WHERE name LIKE '%' || :company_name || '%';
-- </query>

-- <query description>
-- Get latest stock prices for all companies
-- </query description>
-- <query>
SELECT "Ticker", "Date", "Close", "Volume" FROM prices WHERE "Date" = (SELECT MAX("Date") FROM prices) ORDER BY "Close" DESC;
-- </query>

-- <query description>
-- Get sector information for a specific company
-- </query description>
-- <query>
SELECT sector FROM companies WHERE symbol = :ticker;
-- </query>

-- <query description>
-- Get daily trading volume for a specific stock
-- </query description>
-- <query>
SELECT "Date", "Volume" FROM prices WHERE "Ticker" = :ticker ORDER BY "Date" DESC LIMIT 30;
-- </query>

-- <query description>
-- Find companies with highest dividend yield
-- </query description>
-- <query>
SELECT name, symbol, sector, dividend_yield FROM companies WHERE dividend_yield > 0 ORDER BY dividend_yield DESC;
-- </query>

-- <query description>
-- Calculate 30-day moving average for a specific stock
-- </query description>
-- <query>
SELECT "Date", "Close", AVG("Close") OVER (ORDER BY "Date" ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as moving_avg_30d 
FROM prices 
WHERE "Ticker" = :ticker 
ORDER BY "Date" DESC 
LIMIT 30;
-- </query>

-- <query description>
-- Find stocks with highest trading volume in the last week
-- </query description>
-- <query>
SELECT "Ticker", SUM("Volume") as total_volume 
FROM prices 
WHERE "Date" >= CURRENT_DATE - INTERVAL '7 days' 
GROUP BY "Ticker" 
ORDER BY total_volume DESC 
LIMIT 10;
-- </query>

-- <query description>
-- Compare current price to 52-week high/low for a specific stock
-- </query description>
-- <query>
SELECT c.name, c.symbol, p."Close" as current_price, c."52_week_high", c."52_week_low"
FROM companies c 
JOIN prices p ON c.symbol = p."Ticker" 
WHERE c.symbol = :ticker AND p."Date" = (SELECT MAX("Date") FROM prices);
-- </query>

-- <query description>
-- Compare stock performance between two sectors
-- </query description>
-- <query>
SELECT c.sector, AVG(p."Close") as avg_price 
FROM prices p 
JOIN companies c ON p."Ticker" = c.symbol 
WHERE c.sector IN (:sector1, :sector2) 
GROUP BY c.sector;
-- </query>

-- <query description>
-- Get opening price for a specific stock on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON ("Date") "Open" 
FROM prices 
WHERE "Ticker" = :ticker AND "Date" = :date;
-- </query>

-- <query description>
-- Get opening and closing prices for a specific stock in a date range
-- </query description>
-- <query>
SELECT "Date", "Open", "Close" 
FROM prices 
WHERE "Ticker" = :ticker 
AND "Date" BETWEEN :start_date AND :end_date 
ORDER BY "Date";
-- </query>

-- <query description>
-- Get highest price for a specific stock on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON ("Date") "High" 
FROM prices 
WHERE "Ticker" = :ticker AND "Date" = :date;
-- </query>

-- <query description>
-- Get lowest price for a specific stock on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON ("Date") "Low" 
FROM prices 
WHERE "Ticker" = :ticker AND "Date" = :date;
-- </query>

-- <query description>
-- Get daily price range (high and low) for a specific stock
-- </query description>
-- <query>
SELECT "Date", "High", "Low", ("High" - "Low") as daily_range 
FROM prices 
WHERE "Ticker" = :ticker 
AND "Date" BETWEEN :start_date AND :end_date 
ORDER BY "Date";
-- </query>

-- <query description>
-- Get lowest price for a company by name on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON (p."Date") p."Low" 
FROM prices p 
JOIN companies c ON p."Ticker" = c.symbol 
WHERE c.name LIKE :company_name 
AND p."Date" = :date;
-- </query>

-- <query description>
-- Get trading volume for a company by name on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON (p."Date") p."Volume" 
FROM prices p 
JOIN companies c ON p."Ticker" = c.symbol 
WHERE c.name LIKE :company_name 
AND p."Date" = :date;
-- </query>

-- <query description>
-- Get trading volume for a specific stock on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON ("Date") "Volume" 
FROM prices 
WHERE "Ticker" = :ticker AND "Date" = :date;
-- </query>

-- <query description>
-- Get lowest closing price and its date for a specific stock in a year
-- </query description>
-- <query>
SELECT DISTINCT ON ("Close") "Date", "Close"
FROM prices 
WHERE "Ticker" = :ticker 
AND EXTRACT(YEAR FROM "Date") = :year
ORDER BY "Close" ASC;
-- </query>

-- <query description>
-- Get highest closing price and its date for a specific stock in a year
-- </query description>
-- <query>
SELECT DISTINCT ON ("Close") "Date", "Close"
FROM prices 
WHERE "Ticker" = :ticker 
AND EXTRACT(YEAR FROM "Date") = :year
ORDER BY "Close" DESC;
-- </query>

-- <query description>
-- Count number of dividends paid by a company in a specific year
-- </query description>
-- <query>
SELECT COUNT(*) AS dividend_count 
FROM prices 
WHERE "Ticker" = :ticker 
AND EXTRACT(YEAR FROM "Date") = :year 
AND "Dividends" > 0;
-- </query>

-- <query description>
-- Get dividend payment dates and amounts for a company in a specific year
-- </query description>
-- <query>
SELECT "Date", "Dividends" 
FROM prices 
WHERE "Ticker" = :ticker 
AND EXTRACT(YEAR FROM "Date") = :year 
AND "Dividends" > 0 
ORDER BY "Date";
-- </query>

-- <query description>
-- Get total dividend amount paid by a company in a specific year
-- </query description>
-- <query>
SELECT SUM("Dividends") AS total_dividends 
FROM prices 
WHERE "Ticker" = :ticker 
AND EXTRACT(YEAR FROM "Date") = :year 
AND "Dividends" > 0;
-- </query>

-- <query description>
-- Get dividend amount for a specific stock on a specific date
-- </query description>
-- <query>
SELECT "Date", "Dividends" 
FROM prices 
WHERE "Ticker" = :ticker 
AND "Date" = :date 
AND "Dividends" > 0 
LIMIT 1;
-- </query>

-- <query description>
-- Get dividend amount for a specific stock in a date range
-- </query description>
-- <query>
SELECT "Date", "Dividends" 
FROM prices 
WHERE "Ticker" = :ticker 
AND "Date" BETWEEN :start_date AND :end_date 
AND "Dividends" > 0 
ORDER BY "Date";
-- </query>

-- <query description>
-- Compare closing prices of two companies on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON (a."Date")
    a."Ticker" as ticker1,
    b."Ticker" as ticker2,
    a."Close" as price1,
    b."Close" as price2,
    CASE 
        WHEN a."Close" > b."Close" THEN a."Ticker"
        ELSE b."Ticker"
    END as higher_ticker
FROM prices a 
JOIN prices b ON a."Date" = b."Date"
WHERE a."Ticker" = :ticker1 
AND b."Ticker" = :ticker2
AND a."Date" = :date;
-- </query>

-- <query description>
-- Compare closing prices of two companies by name on a specific date
-- </query description>
-- <query>
SELECT DISTINCT ON (p1."Date")
    c1.name as company1,
    c2.name as company2,
    p1."Close" as price1,
    p2."Close" as price2,
    CASE 
        WHEN p1."Close" > p2."Close" THEN c1.name
        ELSE c2.name
    END as higher_company
FROM prices p1
JOIN prices p2 ON p1."Date" = p2."Date"
JOIN companies c1 ON p1."Ticker" = c1.symbol
JOIN companies c2 ON p2."Ticker" = c2.symbol
WHERE c1.name LIKE :company1
AND c2.name LIKE :company2
AND p1."Date" = :date;
-- </query>