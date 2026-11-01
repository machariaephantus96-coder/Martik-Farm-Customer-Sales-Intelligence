CREATE TABLE IF NOT EXISTS calendar (
 date DATE PRIMARY KEY, year INTEGER, month INTEGER, month_name TEXT,
 day_of_week TEXT, is_weekend BOOLEAN, is_public_holiday BOOLEAN,
 holiday_name TEXT, business_season TEXT, is_school_term_assumed BOOLEAN
);
CREATE TABLE IF NOT EXISTS customers (
 customer_id TEXT PRIMARY KEY, customer_name TEXT, segment TEXT,
 delivery_area TEXT, county TEXT, first_order_date DATE,
 contract_payment_terms_days INTEGER, credit_limit_kes NUMERIC(14,2),
 is_account BOOLEAN
);
CREATE TABLE IF NOT EXISTS products (
 product_id TEXT PRIMARY KEY, product_name TEXT, price_list_label TEXT,
 category TEXT, unit TEXT, base_price_jan2026_kes NUMERIC(14,2),
 source_store_id TEXT, shelf_life_days INTEGER, is_imported BOOLEAN,
 is_peak_season_premium BOOLEAN
);
CREATE TABLE IF NOT EXISTS stores (
 store_id TEXT PRIMARY KEY, store_name TEXT, town TEXT, county TEXT, role TEXT
);
CREATE TABLE IF NOT EXISTS promotions (
 promo_id TEXT PRIMARY KEY, promo_name TEXT, start_date DATE, end_date DATE,
 categories TEXT, discount_pct NUMERIC(8,4), eligible BOOLEAN
);
CREATE TABLE IF NOT EXISTS orders (
 order_id TEXT PRIMARY KEY, order_date DATE, customer_id TEXT,
 order_channel TEXT, delivery_area TEXT, county TEXT, payment_terms_days INTEGER,
 subtotal_kes NUMERIC(14,2), delivery_fee_kes NUMERIC(14,2),
 order_total_kes NUMERIC(14,2), invoice_due_date DATE, payment_status TEXT,
 delivered_late BOOLEAN, n_lines INTEGER, gross_margin_kes NUMERIC(14,2),
 margin_pct NUMERIC(8,4), payment_date DATE, days_to_pay INTEGER,
 days_past_due INTEGER, is_credit BOOLEAN, is_paid_late BOOLEAN,
 week_start DATE, day_of_week TEXT, is_public_holiday BOOLEAN,
 business_season TEXT, is_school_term_assumed BOOLEAN, segment TEXT,
 is_account BOOLEAN,
 FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
CREATE TABLE IF NOT EXISTS order_lines (
 line_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, product_id TEXT NOT NULL,
 store_id TEXT, quantity_ordered NUMERIC(14,3), quantity_rejected NUMERIC(14,3),
 reject_reason TEXT, unit_price_kes NUMERIC(14,2), discount_pct NUMERIC(8,4),
 promo_id TEXT, unit_cost_kes NUMERIC(14,2), line_total_kes NUMERIC(14,2),
 price_corrected BOOLEAN, is_qty_outlier BOOLEAN, billed_qty NUMERIC(14,3),
 gross_revenue_kes NUMERIC(14,2), discount_kes NUMERIC(14,2),
 cost_kes NUMERIC(14,2), gross_margin_kes NUMERIC(14,2),
 margin_pct NUMERIC(8,4), is_promo BOOLEAN, rejected_value_kes NUMERIC(14,2),
 FOREIGN KEY (order_id) REFERENCES orders(order_id),
 FOREIGN KEY (product_id) REFERENCES products(product_id),
 FOREIGN KEY (store_id) REFERENCES stores(store_id),
 FOREIGN KEY (promo_id) REFERENCES promotions(promo_id)
);
CREATE TABLE IF NOT EXISTS payments (
 payment_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, customer_id TEXT,
 payment_date DATE, amount_kes NUMERIC(14,2), method TEXT,
 FOREIGN KEY (order_id) REFERENCES orders(order_id),
 FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
CREATE TABLE IF NOT EXISTS price_list_monthly (
 month DATE NOT NULL, product_id TEXT NOT NULL,
 list_price_kes NUMERIC(14,2), unit_cost_kes NUMERIC(14,2),
 PRIMARY KEY (month, product_id),
 FOREIGN KEY (product_id) REFERENCES products(product_id)
);
CREATE INDEX IF NOT EXISTS idx_orders_customer_date ON orders(customer_id, order_date);
CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_lines_order ON order_lines(order_id);
CREATE INDEX IF NOT EXISTS idx_lines_product ON order_lines(product_id);
CREATE INDEX IF NOT EXISTS idx_lines_store ON order_lines(store_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
