-- </query>

-- <query description>
-- Calculate average closing price for a specific stock in a date range
-- </query description>
-- <query>
SELECT 
    AVG("Close") as avg_closing_price
FROM prices 
WHERE "Ticker" = :ticker 
    AND "Date" BETWEEN :start_date AND :end_date;
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