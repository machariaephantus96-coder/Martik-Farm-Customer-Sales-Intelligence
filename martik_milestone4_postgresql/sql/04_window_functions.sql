-- Rank products within category by revenue.
WITH ps AS (
 SELECT p.category,p.product_id,p.product_name,SUM(l.line_total_kes) AS revenue_kes
 FROM products p JOIN order_lines l USING(product_id)
 GROUP BY p.category,p.product_id,p.product_name
)
SELECT *,DENSE_RANK() OVER(PARTITION BY category ORDER BY revenue_kes DESC) AS category_rank
FROM ps ORDER BY category,category_rank;

-- Running cumulative monthly revenue.
WITH m AS (
 SELECT DATE_TRUNC('month',o.order_date)::date AS month_start,
        SUM(l.line_total_kes) AS revenue_kes
 FROM orders o JOIN order_lines l USING(order_id) GROUP BY 1
)
SELECT month_start,revenue_kes,
       SUM(revenue_kes) OVER(ORDER BY month_start) AS cumulative_revenue_kes
FROM m ORDER BY month_start;

-- Month-on-month change using LAG.
WITH m AS (
 SELECT DATE_TRUNC('month',o.order_date)::date AS month_start,
        SUM(l.line_total_kes) AS revenue_kes
 FROM orders o JOIN order_lines l USING(order_id) GROUP BY 1
)
SELECT month_start,revenue_kes,
       LAG(revenue_kes) OVER(ORDER BY month_start) AS previous_month_revenue_kes,
       revenue_kes-LAG(revenue_kes) OVER(ORDER BY month_start) AS change_kes,
       ROUND(100.0*(revenue_kes-LAG(revenue_kes) OVER(ORDER BY month_start))
       /NULLIF(LAG(revenue_kes) OVER(ORDER BY month_start),0),2) AS change_pct
FROM m ORDER BY month_start;

-- Rank customers by revenue.
WITH cs AS (
 SELECT c.customer_id,c.customer_name,SUM(l.line_total_kes) AS revenue_kes
 FROM customers c JOIN orders o USING(customer_id)
 JOIN order_lines l USING(order_id)
 GROUP BY c.customer_id,c.customer_name
)
SELECT *,RANK() OVER(ORDER BY revenue_kes DESC) AS revenue_rank
FROM cs ORDER BY revenue_rank;
