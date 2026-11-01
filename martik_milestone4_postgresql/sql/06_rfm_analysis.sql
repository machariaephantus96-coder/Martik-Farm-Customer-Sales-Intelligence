-- RFM recalculated from normalized transactions, not customer_rfm.csv.
-- Reference date is the latest order date in this dataset.
WITH ref AS (SELECT MAX(order_date)::date AS as_of_date FROM orders),
metrics AS (
 SELECT o.customer_id,
        (SELECT as_of_date FROM ref)-MAX(o.order_date)::date AS recency_days,
        COUNT(DISTINCT o.order_id) AS frequency,
        SUM(l.line_total_kes) AS monetary_kes,
        AVG(o.order_total_kes) AS avg_order_value_kes
 FROM orders o JOIN order_lines l USING(order_id)
 GROUP BY o.customer_id
),
scores AS (
 SELECT *,
        NTILE(5) OVER(ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER(ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER(ORDER BY monetary_kes ASC) AS m_score
 FROM metrics
)
SELECT customer_id,recency_days,frequency,ROUND(monetary_kes,2) AS monetary_kes,
       ROUND(avg_order_value_kes,2) AS avg_order_value_kes,
       r_score,f_score,m_score,(r_score+f_score+m_score) AS rfm_total_score,
       CASE
        WHEN r_score>=4 AND f_score>=4 AND m_score>=4 THEN 'Champions'
        WHEN r_score>=3 AND f_score>=3 THEN 'Loyal Customers'
        WHEN r_score>=4 AND f_score<=2 THEN 'New / Promising'
        WHEN r_score<=2 AND f_score>=3 THEN 'At Risk'
        WHEN r_score<=2 AND f_score<=2 THEN 'Lost / Hibernating'
        ELSE 'Needs Attention'
       END AS calculated_rfm_segment
FROM scores ORDER BY rfm_total_score DESC,monetary_kes DESC;
