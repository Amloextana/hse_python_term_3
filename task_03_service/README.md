# Task 3 — Energy Dashboard (FastAPI + Streamlit)

Мини-дашборд потребления энергии с CRUD-операциями.  
Backend: FastAPI | Frontend: Streamlit

## Структура проекта

```
task_03_service/
├── backend/
│   ├── main.py
│   └── data.csv
├── frontend/
│   ├── app.py
│   └── requirements.txt
├── requirements.txt
└── README.md
```

## Локальный запуск

### 1. Установка зависимостей

```bash
cd task_03_service
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Запуск Backend (FastAPI)

```bash
# из папки task_03_service/
uvicorn backend.main:app --port 8000
```

Swagger UI → http://localhost:8000/docs

### 3. Запуск Frontend (Streamlit)

В новом терминале:

```bash
cd task_03_service/frontend
streamlit run app.py
```

UI → http://localhost:8501


## API Endpoints

| Метод    | Endpoint            | Описание               | HTTP статус         |
|----------|---------------------|------------------------|---------------------|
| `GET`    | `/records`          | Получить все записи    | 200                 |
| `POST`   | `/records`          | Добавить запись        | 201                 |
| `DELETE` | `/records/{id}`     | Удалить запись по id   | 200 / 404           |

## Деплой

### Backend → Render.com

1. Зайти на [render.com](https://render.com), создать **New → Web Service**
2. Подключить GitHub репозиторий
3. Настройки сервиса:
   - **Root Directory**: `task_03_service`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. Нажать **Create Web Service**
5. Скопировать URL вида `https://your-app.onrender.com`


### Frontend → Streamlit Cloud

1. Зайти на [share.streamlit.io](https://share.streamlit.io), войти через GitHub
2. **New app** → выбрать репозиторий
3. Настройки:
   - **Main file path**: `task_03_service/frontend/app.py`
4. Нажать **Advanced settings → Secrets** и добавить:
   ```toml
   BACKEND_URL = "https://your-app.onrender.com"
   ```
5. Нажать **Deploy**
