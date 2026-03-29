#оставил старую версию что бы тестировать локально
FROM apache/airflow:2.7.2-python3.10

USER airflow
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dags/ /opt/airflow/dags/
COPY data_test/ /opt/airflow/data/