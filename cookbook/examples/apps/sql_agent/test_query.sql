-- Test query for comparing sector performance
SELECT 
    c.sector,
    AVG(prices.Close) as avg_price,
    MAX(prices.Close) as max_price,
    MIN(prices.Close) as min_price,
    COUNT(DISTINCT c.symbol) as num_companies
FROM prices
JOIN companies c ON prices."Ticker" = c.symbol
WHERE c.sector IN ('Technology', 'Healthcare')
GROUP BY c.sector
ORDER BY avg_price DESC; 