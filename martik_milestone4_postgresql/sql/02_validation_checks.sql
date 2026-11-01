SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'stores', COUNT(*) FROM stores
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_lines', COUNT(*) FROM order_lines
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'promotions', COUNT(*) FROM promotions
UNION ALL SELECT 'calendar', COUNT(*) FROM calendar
UNION ALL SELECT 'price_list_monthly', COUNT(*) FROM price_list_monthly
ORDER BY table_name;

-- Each orphan count should be zero.
SELECT COUNT(*) AS orphan_orders_customer FROM orders o
LEFT JOIN customers c USING(customer_id) WHERE c.customer_id IS NULL;
SELECT COUNT(*) AS orphan_lines_order FROM order_lines l
LEFT JOIN orders o USING(order_id) WHERE o.order_id IS NULL;
SELECT COUNT(*) AS orphan_lines_product FROM order_lines l
LEFT JOIN products p USING(product_id) WHERE p.product_id IS NULL;
SELECT COUNT(*) AS orphan_payments_order FROM payments p
LEFT JOIN orders o USING(order_id) WHERE o.order_id IS NULL;

-- Investigate any differences greater than KSh 1.
WITH x AS (SELECT order_id, SUM(line_total_kes) AS lines_subtotal
           FROM order_lines GROUP BY order_id)
SELECT o.order_id, o.subtotal_kes, x.lines_subtotal,
       ROUND(o.subtotal_kes-x.lines_subtotal,2) AS difference_kes
FROM orders o JOIN x USING(order_id)
WHERE ABS(o.subtotal_kes-x.lines_subtotal)>1
ORDER BY ABS(o.subtotal_kes-x.lines_subtotal) DESC LIMIT 100;

SELECT COUNT(DISTINCT order_id) AS orders,
       COUNT(*) AS order_lines, SUM(billed_qty) AS billed_quantity,
       SUM(line_total_kes) AS line_revenue_kes,
       SUM(cost_kes) AS cost_kes, SUM(gross_margin_kes) AS gross_margin_kes
FROM order_lines;
