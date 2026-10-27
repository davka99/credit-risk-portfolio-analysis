-- SQLite. Synthetic credit-risk portfolio only.
-- 1. Monthly 30+ DPD exposure share
SELECT month, ROUND(SUM(ead),2) AS total_ead,
       ROUND(SUM(CASE WHEN dpd >= 30 THEN ead ELSE 0 END),2) AS dpd30_ead,
       ROUND(100.0*SUM(CASE WHEN dpd >= 30 THEN ead ELSE 0 END)/NULLIF(SUM(ead),0),2) AS dpd30_pct
FROM snapshots GROUP BY month ORDER BY month;

-- 2. One-month roll rates, account-weighted; 90+ represents severe delinquency, not proven default.
WITH paired AS (
  SELECT s.loan_id, s.month, s.dpd_bucket AS from_bucket,
         LEAD(s.dpd_bucket) OVER(PARTITION BY s.loan_id ORDER BY s.month) AS to_bucket
  FROM snapshots s
)
SELECT from_bucket, to_bucket, COUNT(*) AS transitions,
       ROUND(100.0*COUNT(*) / SUM(COUNT(*)) OVER(PARTITION BY from_bucket),2) AS pct
FROM paired WHERE to_bucket IS NOT NULL
GROUP BY from_bucket,to_bucket ORDER BY from_bucket,to_bucket;

-- 3. Latest month segment exposure and illustrative 12-month expected loss proxy
WITH latest AS (SELECT MAX(month) AS m FROM snapshots)
SELECT l.segment,COUNT(*) AS accounts,ROUND(SUM(s.ead),2) AS ead,
       ROUND(SUM(s.ead*l.pd_12m_assumed*l.lgd_assumed),2) AS ecl_proxy
FROM snapshots s JOIN loans l ON l.loan_id=s.loan_id
JOIN latest x ON s.month=x.m GROUP BY l.segment ORDER BY ead DESC;
