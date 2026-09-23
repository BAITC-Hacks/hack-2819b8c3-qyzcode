import streamlit as st

st.set_page_config(
    page_title="AI Sana",
    page_icon="💡",
    layout="wide",
)

st.title("AI Sana")
st.write("Задачи бизнеса — решения студенческих команд.")

# Здесь временно храним подтверждённую карточку.
if "confirmed_task" not in st.session_state:
    st.session_state.confirmed_task = None

st.subheader("Карточка бизнес-задачи")
st.caption("Заполните известные сведения. Остальные можно дополнить позже.")

with st.form("task_form"):
    title = st.text_input(
        "Название задачи",
        placeholder="Например: уменьшить списание продуктов",
    )

    industry = st.selectbox(
        "Тема задачи",
        ["Торговля", "Образование", "Медицина", "Логистика", "Другое"],
    )

    context = st.text_area(
        "Контекст — что происходит сейчас?",
        placeholder="Как сейчас устроен процесс?",
    )

    need = st.text_area(
        "Потребность — что нужно изменить?",
        placeholder="Какую проблему вы хотите решить?",
    )

    users = st.text_area(
        "Пользователи",
        placeholder="Кто будет пользоваться решением?",
    )

    data = st.text_area(
        "Данные и материалы",
        placeholder="Какие таблицы, документы или примеры доступны?",
    )

    constraints = st.text_area(
        "Ограничения",
        placeholder="Сроки, технологии, доступы и другие условия",
    )

    result = st.text_area(
        "Ожидаемый результат",
        placeholder="Что команда должна передать в конце работы?",
    )

    success = st.text_area(
        "Критерии успеха",
        placeholder="Как вы определите, что задача решена?",
    )

    contact = st.text_input(
        "Контакт представителя бизнеса",
        placeholder="Email или другой способ связи",
    )

    interaction = st.text_area(
        "Формат взаимодействия",
        placeholder="Как часто вы готовы отвечать на вопросы команды?",
    )

    confirmed = st.checkbox(
        "Подтверждаю достоверность заполненных сведений"
    )

    submitted = st.form_submit_button("Подтвердить карточку")

if submitted:
    if not title.strip() or not need.strip():
        st.warning("Заполните название задачи и потребность.")
    elif not confirmed:
        st.warning("Поставьте галочку подтверждения сведений.")
    else:
        st.session_state.confirmed_task = {
            "title": title.strip(),
            "industry": industry,
            "context": context.strip(),
            "need": need.strip(),
            "users": users.strip(),
            "data": data.strip(),
            "constraints": constraints.strip(),
            "result": result.strip(),
            "success": success.strip(),
            "contact": contact.strip(),
            "interaction": interaction.strip(),
            "confirmed": True,
        }
        st.success("Карточка подтверждена!")

task = st.session_state.confirmed_task

if task is not None:
    st.divider()
    st.subheader("Последняя подтверждённая карточка")
    st.caption(
        "После изменения полей нажмите «Подтвердить карточку» ещё раз, "
        "чтобы обновить этот просмотр."
    )

    labels = {
        "title": "Название",
        "industry": "Тема",
        "context": "Контекст",
        "need": "Потребность",
        "users": "Пользователи",
        "data": "Данные и материалы",
        "constraints": "Ограничения",
        "result": "Ожидаемый результат",
        "success": "Критерии успеха",
        "contact": "Контакт",
        "interaction": "Формат взаимодействия",
    }

    for field, label in labels.items():
        st.markdown(f"**{label}**")
        st.write(task[field] or "Пока не указано")