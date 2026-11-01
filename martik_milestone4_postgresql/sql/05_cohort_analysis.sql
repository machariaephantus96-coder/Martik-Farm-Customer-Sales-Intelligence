WITH first_orders AS (
 SELECT customer_id,DATE_TRUNC('month',MIN(order_date))::date AS cohort_month
 FROM orders GROUP BY customer_id
),
activity AS (
 SELECT DISTINCT o.customer_id,f.cohort_month,
        DATE_TRUNC('month',o.order_date)::date AS activity_month,
        ((EXTRACT(YEAR FROM DATE_TRUNC('month',o.order_date))-EXTRACT(YEAR FROM f.cohort_month))*12
        +(EXTRACT(MONTH FROM DATE_TRUNC('month',o.order_date))-EXTRACT(MONTH FROM f.cohort_month)))::int
        AS months_since_cohort
 FROM orders o JOIN first_orders f USING(customer_id)
),
sizes AS (
 SELECT cohort_month,COUNT(*) AS cohort_customers
 FROM first_orders GROUP BY cohort_month
),
retained AS (
 SELECT cohort_month,months_since_cohort,COUNT(DISTINCT customer_id) AS retained_customers
 FROM activity GROUP BY cohort_month,months_since_cohort
)
SELECT r.cohort_month,r.months_since_cohort,s.cohort_customers,
       r.retained_customers,
       ROUND(100.0*r.retained_customers/NULLIF(s.cohort_customers,0),2) AS retention_pct
FROM retained r JOIN sizes s USING(cohort_month)
ORDER BY r.cohort_month,r.months_since_cohort;
