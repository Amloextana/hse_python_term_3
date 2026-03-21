FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install --no-cache-dir flake8 && \
    flake8 app.py --max-line-length=120

CMD ["streamlit", "run", "app.py", "--server.port", "8889", "--server.address", "0.0.0.0"]
