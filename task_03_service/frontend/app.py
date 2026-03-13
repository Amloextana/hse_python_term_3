import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

try:
    API_URL = st.secrets["BACKEND_URL"]
except (KeyError, FileNotFoundError):
    API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Энергетический дашборд", layout="wide")
st.title("Дашборд потребления энергии")


def fetch_data() -> pd.DataFrame:
    try:
        resp = requests.get(f"{API_URL}/records", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except requests.exceptions.ConnectionError:
        st.error("Нет подключения к бэкенду. Убедитесь, что FastAPI запущен.")
        return pd.DataFrame()
    except requests.exceptions.Timeout:
        st.error("Бэкенд не отвечает (таймаут).")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Неожиданная ошибка: {e}")
        return pd.DataFrame()


df = fetch_data()

st.subheader("Таблица")
if df.empty:
    st.info("Записи не найдены.")
else:
    st.dataframe(df, use_container_width=True, hide_index=True)

if not df.empty and "timestep" in df.columns:
    st.subheader("Графики")

    df_plot = df.copy()
    df_plot["timestep"] = pd.to_datetime(df_plot["timestep"], errors="coerce")
    df_plot = df_plot.dropna(subset=["timestep"]).sort_values("timestep")

    max_pts = len(df_plot)
    n_points = st.slider(
        "Количество последних записей для отображения на графиках",
        min_value=100,
        max_value=min(max_pts, 5000),
        value=min(1000, max_pts),
        step=100,
    )
    df_plot = df_plot.tail(n_points)

    col1, col2 = st.columns(2)

    with col1:
        fig1 = px.line(
            df_plot,
            x="timestep",
            y=["consumption_eur", "consumption_sib"],
            title="Потребление энергии (МВт·ч)",
            labels={"value": "Потребление", "timestep": "Время", "variable": "Регион"},
            color_discrete_map={
                "consumption_eur": "#636EFA",
                "consumption_sib": "#EF553B",
            },
        )
        fig1.update_layout(legend_title_text="")
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.line(
            df_plot,
            x="timestep",
            y=["price_eur", "price_sib"],
            title="Цена на энергию",
            labels={"value": "Цена", "timestep": "Время", "variable": "Регион"},
            color_discrete_map={
                "price_eur": "#00CC96",
                "price_sib": "#AB63FA",
            },
        )
        fig2.update_layout(legend_title_text="")
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

st.subheader("Добавить запись")

with st.form("add_form", clear_on_submit=True):
    timestep_val = st.text_input(
        "Дата и время", placeholder="2006-09-01 05:00", value="2006-09-01 05:00"
    )
    c1, c2 = st.columns(2)
    with c1:
        c_eur = st.number_input("Потребление (Европа)", min_value=0.0, value=60000.0, step=100.0)
        p_eur = st.number_input("Цена (Европа)", min_value=0.0, value=275.0, step=1.0)
    with c2:
        c_sib = st.number_input("Потребление (Сибирь)", min_value=0.0, value=17000.0, step=100.0)
        p_sib = st.number_input("Цена (Сибирь)", min_value=0.0, value=0.0, step=1.0)

    if st.form_submit_button("Добавить запись"):
        payload = {
            "timestep": timestep_val,
            "consumption_eur": c_eur,
            "consumption_sib": c_sib,
            "price_eur": p_eur,
            "price_sib": p_sib,
        }
        try:
            resp = requests.post(f"{API_URL}/records", json=payload, timeout=15)
            if resp.status_code == 201:
                st.success(f"Запись добавлена! ID: {resp.json()['id']}")
                st.rerun()
            else:
                detail = resp.json().get("detail", "Неизвестная ошибка")
                st.error(f"Ошибка {resp.status_code}: {detail}")
        except Exception as e:
            st.error(f"Запрос не выполнен: {e}")

st.divider()

st.subheader("Удалить запись")

with st.form("delete_form", clear_on_submit=True):
    record_id = st.number_input("ID записи для удаления", min_value=1, step=1, value=1)

    if st.form_submit_button("Удалить запись"):
        try:
            resp = requests.delete(f"{API_URL}/records/{int(record_id)}", timeout=15)
            if resp.status_code == 200:
                st.success(f"✅ Запись {int(record_id)} удалена!")
                st.rerun()
            elif resp.status_code == 404:
                st.error(f"Запись с id={int(record_id)} не найдена")
            else:
                detail = resp.json().get("detail", "Неизвестная ошибка")
                st.error(f"Ошибка {resp.status_code}: {detail}")
        except Exception as e:
            st.error(f"Запрос не выполнен: {e}")
