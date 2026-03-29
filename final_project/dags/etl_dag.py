import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
from airflow.utils.dates import days_ago
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
import logging

def load_parquet_to_raw():
    """Читает Parquet и загружает его в raw таблицу БД без изменений"""
    df = pd.read_parquet("/opt/airflow/data/")
    df = df.astype(object).where(pd.notnull(df), None)
    engine = create_engine("postgresql+psycopg2://airflow:airflow@postgres:5432/airflow")
    
    df.to_sql("raw_deliveries", engine, schema="raw", if_exists="replace", index=False)


def on_failure_callback(context):
    """Логи для airflow.DAG"""
    exception = context.get("exception")
    task_id = context.get("task_instance").task_id
    logging.error(f"Таск {task_id} завершился с ошибкой: {exception}")


# Идемпотентные SQL-скрипты для нормализации (из raw в dds)
# Описание таблиц лежит в /docs
SQL_NORMALIZE_DDS = """
    -- 1. Справочник: Users 
    INSERT INTO dds.users (user_id, user_phone)
    SELECT CAST(user_id AS BIGINT), MAX(CAST(user_phone AS TEXT))
    FROM raw.raw_deliveries WHERE user_id IS NOT NULL
    GROUP BY CAST(user_id AS BIGINT)
    
    ON CONFLICT (user_id) DO UPDATE SET 
    user_phone = EXCLUDED.user_phone;

    -- 2. Справочник: Stores
    INSERT INTO dds.stores (store_id, store_address, city)
    SELECT CAST(store_id AS BIGINT), MAX(CAST(store_address AS TEXT)), MAX(split_part(CAST(store_address AS TEXT), ',', 2))
    FROM raw.raw_deliveries WHERE store_id IS NOT NULL
    GROUP BY CAST(store_id AS BIGINT)

    ON CONFLICT (store_id) DO UPDATE SET 
    store_address = EXCLUDED.store_address,
    city = EXCLUDED.city;

    -- 3. Справочник: Drivers
    INSERT INTO dds.drivers (driver_id, driver_phone)
    SELECT CAST(driver_id AS BIGINT), MAX(CAST(driver_phone AS TEXT))
    FROM raw.raw_deliveries WHERE driver_id IS NOT NULL
    GROUP BY CAST(driver_id AS BIGINT)

    ON CONFLICT (driver_id) DO UPDATE SET 
    driver_phone = EXCLUDED.driver_phone;

    -- 4. Справочник: Items
    INSERT INTO dds.items (item_id, item_title, item_category)
    SELECT CAST(item_id AS BIGINT), MAX(CAST(item_title AS TEXT)), MAX(CAST(item_category AS TEXT))
    FROM raw.raw_deliveries WHERE item_id IS NOT NULL
    GROUP BY CAST(item_id AS BIGINT)

    ON CONFLICT (item_id) DO UPDATE SET 
    item_title = EXCLUDED.item_title,
    item_category = EXCLUDED.item_category;

    -- 5. Транзакции: Orders
    INSERT INTO dds.orders (order_id, user_id, store_id, created_at, paid_at, canceled_at, payment_type, order_discount, delivery_cost, address_text, order_cancellation_reason)
    SELECT 
    CAST(order_id AS BIGINT), 
    MAX(CAST(user_id AS BIGINT)), 
    MAX(CAST(store_id AS BIGINT)), 
    MAX(CAST(created_at AS TIMESTAMP)), 
    MAX(CAST(paid_at AS TIMESTAMP)), 
    MAX(CAST(canceled_at AS TIMESTAMP)), 
    MAX(CAST(payment_type AS TEXT)), 
    MAX(CAST(order_discount AS NUMERIC)), 
    MAX(CAST(delivery_cost AS NUMERIC)), 
    MAX(CAST(address_text AS TEXT)), 
    MAX(CAST(order_cancellation_reason AS TEXT))
    FROM raw.raw_deliveries
    GROUP BY CAST(order_id AS BIGINT)

    ON CONFLICT (order_id) DO UPDATE SET 
    user_id = EXCLUDED.user_id,
    store_id = EXCLUDED.store_id,
    created_at = EXCLUDED.created_at,
    paid_at = EXCLUDED.paid_at,
    canceled_at = EXCLUDED.canceled_at,
    payment_type = EXCLUDED.payment_type,
    order_discount = EXCLUDED.order_discount,
    delivery_cost = EXCLUDED.delivery_cost,
    address_text = EXCLUDED.address_text,
    order_cancellation_reason = EXCLUDED.order_cancellation_reason;

    -- 6. Транзакции: Order Items
    INSERT INTO dds.order_items (order_id, item_id, item_quantity, item_price, item_canceled_quantity, item_replaced_id, item_discount)
    SELECT 
    CAST(order_id AS BIGINT), 
    CAST(item_id AS BIGINT), 
    MAX(CAST(item_quantity AS INT)), 
    MAX(CAST(item_price AS NUMERIC(10,2))), 
    MAX(CAST(item_canceled_quantity AS INT)), 
    MAX(CAST(CAST(item_replaced_id AS FLOAT) AS BIGINT)), 
    MAX(CAST(item_discount AS NUMERIC(5,2)))
    FROM raw.raw_deliveries
    GROUP BY CAST(order_id AS BIGINT), CAST(item_id AS BIGINT)

    ON CONFLICT (order_id, item_id) DO UPDATE SET 
    item_quantity = EXCLUDED.item_quantity,
    item_price = EXCLUDED.item_price,
    item_canceled_quantity = EXCLUDED.item_canceled_quantity,
    item_replaced_id = EXCLUDED.item_replaced_id,
    item_discount = EXCLUDED.item_discount;

    -- 7. Факты доставок (здесь PK просто serial, поэтому так добавляем новые записи)
    DELETE FROM dds.deliveries WHERE order_id IN (SELECT DISTINCT CAST(order_id AS BIGINT) FROM raw.raw_deliveries);
    
    INSERT INTO dds.deliveries (order_id, driver_id, delivery_started_at, delivered_at)
    SELECT 
    CAST(order_id AS BIGINT), 
    CAST(driver_id AS BIGINT), 
    MAX(CAST(delivery_started_at AS TIMESTAMP)), 
    MAX(CAST(delivered_at AS TIMESTAMP))
    FROM raw.raw_deliveries 
    WHERE driver_id IS NOT NULL
    GROUP BY CAST(order_id AS BIGINT), CAST(driver_id AS BIGINT);
"""


# Витрины формируются с 0 (TRUNCATE) из данных обработанных таблиц
# Идемпотентность реализована на этапе загрузки данных в dds
# Если прилетят новые данные/дубликаты/обновления старых данных, то они обработаются там
# Это сделано что бы данные в витринах соответствовали данным в dds, например если строку удалят в таблице из dds,
# то это гарантированно отобразится в витринах. А если отрубят свет при создании витрин, то придется заново запускать, что поделать
SQL_BUILD_MARTS = """
    -- ВИТРИНА 1: ЗАКАЗЫ
    TRUNCATE TABLE marts.fct_orders;
    
    -- Шаг 1: Считаем деньги по каждому товару отдельно
    WITH item_calculations AS (
    SELECT 
    order_id,
    item_price,
    item_quantity,
        
    -- Если скидки нет, считаем как 0
    CASE WHEN item_discount IS NULL THEN 0 ELSE item_discount END as i_discount,
    
    -- Если отмен не было, считаем как 0
    CASE WHEN item_canceled_quantity IS NULL THEN 0 ELSE item_canceled_quantity END as c_quantity
    FROM dds.order_items
    ),
    
    -- Шаг 2: Считаем деньги по целому заказу
    order_money AS (
    SELECT 
    order_id,
    -- Оборот (без учета отмен, но со скидкой на товар)
    SUM(item_price * item_quantity * (1 - (i_discount / 100.0))) as raw_turnover,
    
    -- Выручка (с учетом отмененных товаров и скидки)
    SUM(item_price * (item_quantity - c_quantity) * (1 - (i_discount / 100.0))) as raw_revenue
    FROM item_calculations
    GROUP BY order_id
    ),
    
    -- Шаг 3: Считаем курьеров на заказ
    courier_counts AS (
    SELECT 
    order_id,
    COUNT(driver_id) as drivers_per_order,
    MAX(delivered_at) as final_delivered_at
    FROM dds.deliveries
    GROUP BY order_id
    )
    
    -- Шаг 4: Собираем финальную витрину
    INSERT INTO marts.fct_orders
    SELECT 
    EXTRACT(YEAR FROM o.created_at) as report_year,
    EXTRACT(MONTH FROM o.created_at) as report_month,
    EXTRACT(DAY FROM o.created_at) as report_day,
    s.city,
    o.store_id,
    
    -- Итоговый оборот (с учетом скидки на весь заказ)
    SUM(om.raw_turnover * (1 - (CASE WHEN o.order_discount IS NULL THEN 0 ELSE o.order_discount END) / 100.0)) as turnover,
    
    -- Итоговая выручка
    SUM(om.raw_revenue * (1 - (CASE WHEN o.order_discount IS NULL THEN 0 ELSE o.order_discount END) / 100.0)) as revenue,
    
    -- Прибыль (Выручка минус доставка)
    SUM(om.raw_revenue * (1 - (CASE WHEN o.order_discount IS NULL THEN 0 ELSE o.order_discount END) / 100.0) - o.delivery_cost) as profit,
    
    -- Количественные метрики
    COUNT(o.order_id) as total_orders,
    SUM(CASE WHEN cc.final_delivered_at IS NOT NULL THEN 1 ELSE 0 END) as delivered_orders,
    SUM(CASE WHEN o.canceled_at IS NOT NULL THEN 1 ELSE 0 END) as canceled_orders,
    SUM(CASE WHEN o.canceled_at > cc.final_delivered_at THEN 1 ELSE 0 END) as post_delivery_cancels,
    SUM(CASE WHEN o.order_cancellation_reason = 'Ошибка приложения' OR o.order_cancellation_reason = 'Проблемы с оплатой' THEN 1 ELSE 0 END) as service_error_cancels,
    
    -- Покупатели
    COUNT(DISTINCT o.user_id) as unique_buyers,
    SUM(om.raw_revenue * (1 - (CASE WHEN o.order_discount IS NULL THEN 0 ELSE o.order_discount END) / 100.0)) / COUNT(o.order_id) as avg_check,
    CAST(COUNT(o.order_id) AS NUMERIC) / COUNT(DISTINCT o.user_id) as orders_per_buyer,
    SUM(om.raw_revenue * (1 - (CASE WHEN o.order_discount IS NULL THEN 0 ELSE o.order_discount END) / 100.0)) / COUNT(DISTINCT o.user_id) as revenue_per_buyer,
    
    -- Курьеры
    SUM(CASE WHEN cc.drivers_per_order > 1 THEN 1 ELSE 0 END) as courier_changes,
    SUM(cc.drivers_per_order) as active_couriers

    FROM dds.orders o
    JOIN order_money om ON o.order_id = om.order_id
    JOIN dds.stores s ON o.store_id = s.store_id
    LEFT JOIN courier_counts cc ON o.order_id = cc.order_id
    GROUP BY 
    EXTRACT(YEAR FROM o.created_at),
    EXTRACT(MONTH FROM o.created_at),
    EXTRACT(DAY FROM o.created_at),
    s.city,
    o.store_id;


    -- ВИТРИНА 2: ТОВАРЫ
    TRUNCATE TABLE marts.fct_items;
    
    INSERT INTO marts.fct_items
    SELECT 
    EXTRACT(YEAR FROM o.created_at) as report_year,
    EXTRACT(MONTH FROM o.created_at) as report_month,
    EXTRACT(DAY FROM o.created_at) as report_day,
    s.city,
    o.store_id,
    i.item_category,
    oi.item_id,
    
    -- Оборот товара (цена * кол-во * скидка)
    SUM(oi.item_price * oi.item_quantity * (1 - (CASE WHEN oi.item_discount IS NULL THEN 0 ELSE oi.item_discount END) / 100.0)) as item_turnover,
    
    SUM(oi.item_quantity) as ordered_qty,
    
    -- Отмененные единицы
    SUM(CASE WHEN oi.item_canceled_quantity IS NULL THEN 0 ELSE oi.item_canceled_quantity END) as canceled_qty,
    
    -- Заказы с товаром
    COUNT(DISTINCT o.order_id) as orders_with_item,
    
    -- Заказы с отменой этого товара
    SUM(CASE WHEN oi.item_canceled_quantity > 0 THEN 1 ELSE 0 END) as orders_with_cancel
        
    FROM dds.order_items oi
    JOIN dds.orders o ON oi.order_id = o.order_id
    JOIN dds.stores s ON o.store_id = s.store_id
    JOIN dds.items i ON oi.item_id = i.item_id
    GROUP BY 
    EXTRACT(YEAR FROM o.created_at),
    EXTRACT(MONTH FROM o.created_at),
    EXTRACT(DAY FROM o.created_at),
    s.city,
    o.store_id,
    i.item_category,
    oi.item_id;
"""

with DAG(
    dag_id="delivery_sql_elt",
    default_args={
        'on_failure_callback': on_failure_callback,
    },
    schedule_interval="@daily",
    start_date=days_ago(0),
    catchup=False,
    tags=['final_project']
) as dag:

    task_extract_to_raw = PythonOperator(
        task_id="load_parquet_to_raw",
        python_callable=load_parquet_to_raw
    )

    task_normalize_dds = SQLExecuteQueryOperator(
        task_id="normalize_raw_to_dds",
        conn_id="postgres_default",
        sql=SQL_NORMALIZE_DDS
    )

    task_build_marts = SQLExecuteQueryOperator(
        task_id="build_data_marts",
        conn_id="postgres_default",
        sql=SQL_BUILD_MARTS
    )

    task_extract_to_raw >> task_normalize_dds >> task_build_marts