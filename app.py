import streamlit as st

st.set_page_config(
    page_title="AI Sana",
    page_icon="💡",
    layout="wide",
)

st.title("AI Sana")
st.write("Задачи бизнеса — решения студенческих команд.")

st.subheader("Опишите вашу задачу")

description = st.text_area(
    "Что вы хотите улучшить?",
    placeholder="Например: хотим уменьшить списание продуктов в магазине.",
    height=150,
)

if st.button("Продолжить"):
    if description.strip():
        st.success("Описание принято!")
        st.write(description)
    else:
        st.warning("Сначала введите описание задачи.")