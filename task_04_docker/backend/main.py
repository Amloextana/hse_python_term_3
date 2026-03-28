import os
from typing import List
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator


app = FastAPI(title="Energy Data API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CSV_PATH = os.path.join(os.path.dirname(__file__), "data.csv")


class RecordCreate(BaseModel):
    timestep: str
    consumption_eur: float
    consumption_sib: float
    price_eur: float
    price_sib: float

    @field_validator("consumption_eur", "consumption_sib")
    @classmethod
    def consumption_non_negative(cls, v: float) -> float:
        """Проверка потребления электроэнергии на отриц. число"""
        if v < 0:
            raise ValueError("Consumption must be >= 0")
        return v

    @field_validator("price_eur", "price_sib")
    @classmethod
    def price_non_negative(cls, v: float) -> float:
        """Проверка цены электроэнергии на отриц. число"""
        if v < 0:
            raise ValueError("Price must be >= 0")
        return v


class Record(RecordCreate):
    id: int


def load_data() -> pd.DataFrame:
    """Загрузка csv файла"""
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Data file not found: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    if "id" not in df.columns:
        df.insert(0, "id", range(1, len(df) + 1))
        df.to_csv(CSV_PATH, index=False)
    else:
        df["id"] = df["id"].astype(int)
    return df


def save_data(df: pd.DataFrame) -> None:
    """Сохранение изменений в csv файл"""
    df.to_csv(CSV_PATH, index=False)


@app.get("/records", response_model=List[Record], status_code=200)
def get_records():
    """Получение всех записей"""
    try:
        df = load_data()
        return df.to_dict(orient="records")
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e


@app.post("/records", response_model=Record, status_code=201)
def create_record(record: RecordCreate):
    """Добавление записи"""
    try:
        df = load_data()
        new_id = int(df["id"].max()) + 1 if len(df) > 0 else 1
        new_row = {"id": new_id, **record.model_dump()}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_data(df)
        return new_row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e


@app.delete("/records/{record_id}", status_code=200)
def delete_record(record_id: int):
    """Удаление записи"""
    try:
        df = load_data()
        if record_id not in df["id"].values:
            raise HTTPException(
                status_code=404,
                detail=f"Record with id={record_id} not found",
            )
        df = df[df["id"] != record_id].reset_index(drop=True)
        save_data(df)
        return {"message": f"Record {record_id} successfully deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}") from e
