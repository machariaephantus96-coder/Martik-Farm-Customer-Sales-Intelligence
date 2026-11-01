-- Monthly revenue and gross margin.
SELECT DATE_TRUNC('month',o.order_date)::date AS month_start,
       COUNT(DISTINCT o.order_id) AS orders,
       SUM(l.line_total_kes) AS revenue_kes,
       SUM(l.gross_margin_kes) AS gross_margin_kes
FROM orders o JOIN order_lines l USING(order_id)
GROUP BY 1 ORDER BY 1;

-- Category performance.
SELECT p.category, SUM(l.line_total_kes) AS revenue_kes,
       SUM(l.gross_margin_kes) AS gross_margin_kes,
       SUM(l.billed_qty) AS billed_quantity
FROM order_lines l JOIN products p USING(product_id)
GROUP BY p.category ORDER BY revenue_kes DESC;

-- Top products.
SELECT p.product_id,p.product_name,p.category,
       SUM(l.billed_qty) AS units_sold,SUM(l.line_total_kes) AS revenue_kes
FROM order_lines l JOIN products p USING(product_id)
GROUP BY p.product_id,p.product_name,p.category
ORDER BY revenue_kes DESC LIMIT 20;

-- Customer value.
SELECT c.customer_id,c.customer_name,c.segment,c.county,
       COUNT(DISTINCT o.order_id) AS order_count,
       SUM(l.line_total_kes) AS lifetime_revenue_kes,
       AVG(o.order_total_kes) AS average_order_value_kes
FROM customers c JOIN orders o USING(customer_id)
JOIN order_lines l USING(order_id)
GROUP BY c.customer_id,c.customer_name,c.segment,c.county
ORDER BY lifetime_revenue_kes DESC LIMIT 25;

-- Store performance.
SELECT s.store_name,s.town,s.county,s.role,
       COUNT(DISTINCT l.order_id) AS orders_served,
       SUM(l.line_total_kes) AS revenue_kes,
       SUM(l.gross_margin_kes) AS gross_margin_kes
FROM stores s JOIN order_lines l USING(store_id)
GROUP BY s.store_id,s.store_name,s.town,s.county,s.role
ORDER BY revenue_kes DESC;

-- Payment methods and seasonal performance.
SELECT method,COUNT(*) AS payment_count,SUM(amount_kes) AS amount_kes
FROM payments GROUP BY method ORDER BY amount_kes DESC;

SELECT o.business_season,COUNT(DISTINCT o.order_id) AS orders,
       SUM(l.line_total_kes) AS revenue_kes
FROM orders o JOIN order_lines l USING(order_id)
GROUP BY o.business_season ORDER BY revenue_kes DESC;

SELECT is_credit,is_paid_late,COUNT(*) AS order_count,
       SUM(order_total_kes) AS order_value_kes,AVG(days_to_pay) AS avg_days_to_pay
FROM orders GROUP BY is_credit,is_paid_late ORDER BY is_credit,is_paid_late;
