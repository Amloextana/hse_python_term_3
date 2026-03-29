CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS dds;
CREATE SCHEMA IF NOT EXISTS marts;

-- таблицы в 3nf
CREATE TABLE IF NOT EXISTS dds.users (
    user_id BIGINT PRIMARY KEY,
    user_phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS dds.stores (
    store_id BIGINT PRIMARY KEY,
    store_address TEXT,
    city VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dds.drivers (
    driver_id BIGINT PRIMARY KEY,
    driver_phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS dds.items (
    item_id BIGINT PRIMARY KEY,
    item_title VARCHAR(255),
    item_category VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS dds.orders (
    order_id BIGINT PRIMARY KEY,
    user_id BIGINT REFERENCES dds.users(user_id),
    store_id BIGINT REFERENCES dds.stores(store_id),
    created_at TIMESTAMP,
    paid_at TIMESTAMP,
    canceled_at TIMESTAMP,
    payment_type VARCHAR(50),
    order_discount NUMERIC(5,2),
    delivery_cost NUMERIC(10,2),
    address_text TEXT,
    order_cancellation_reason TEXT
);

CREATE TABLE IF NOT EXISTS dds.order_items (
    order_id BIGINT REFERENCES dds.orders(order_id),
    item_id BIGINT REFERENCES dds.items(item_id),
    item_quantity INT,
    item_price NUMERIC(10,2),
    item_canceled_quantity INT,
    item_replaced_id BIGINT,
    item_discount NUMERIC(5,2),
    PRIMARY KEY (order_id, item_id)
);

CREATE TABLE IF NOT EXISTS dds.deliveries (
    id SERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES dds.orders(order_id),
    driver_id BIGINT REFERENCES dds.drivers(driver_id),
    delivery_started_at TIMESTAMP,
    delivered_at TIMESTAMP
);

-- витрины
CREATE TABLE IF NOT EXISTS marts.fct_orders (
    report_year INT, report_month INT, report_day INT, 
    city VARCHAR(100), store_id BIGINT,
    turnover NUMERIC(15,2), revenue NUMERIC(15,2), profit NUMERIC(15,2),
    total_orders INT, delivered_orders INT, canceled_orders INT,
    post_delivery_cancels INT, service_error_cancels INT,
    unique_buyers INT, avg_check NUMERIC(10,2),
    orders_per_buyer NUMERIC(10,2), revenue_per_buyer NUMERIC(15,2),
    courier_changes INT, active_couriers INT,
    PRIMARY KEY (report_year, report_month, report_day, city, store_id)
);

CREATE TABLE IF NOT EXISTS marts.fct_items (
    report_year INT, report_month INT, report_day INT, 
    city VARCHAR(100), store_id BIGINT, item_category VARCHAR(100), item_id BIGINT,
    item_turnover NUMERIC(15,2), ordered_qty INT, canceled_qty INT,
    orders_with_item INT, orders_with_cancel INT,
    PRIMARY KEY (report_year, report_month, report_day, city, store_id, item_category, item_id)
);