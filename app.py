import streamlit as st

from backend import calculate_rating
from database import init_db, save_task


st.set_page_config(
    page_title="AI Sana",
    page_icon="💡",
    layout="wide",
)

# Подготавливаем базу данных.
try:
    init_db()
except Exception as error:
    st.error(f"Не удалось открыть базу данных: {error}")
    st.stop()


# Запоминаем данные между нажатиями кнопок.
if "confirmed_task" not in st.session_state:
    st.session_state.confirmed_task = None

if "last_saved_task" not in st.session_state:
    st.session_state.last_saved_task = None

if "last_saved_id" not in st.session_state:
    st.session_state.last_saved_id = None


st.title("💡 AI Sana")
st.write("Задачи бизнеса — решения студенческих команд.")

st.subheader("Карточка бизнес-задачи")
st.caption(
    "Заполните известные сведения. "
    "Остальные можно дополнить позже."
)

with st.form("task_form"):
    title = st.text_input(
        "Название задачи",
        placeholder="Например: уменьшить списание продуктов",
    )

    industry = st.selectbox(
        "Тема задачи",
        [
            "Торговля",
            "Образование",
            "Медицина",
            "Логистика",
            "Другое",
        ],
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

    success_criteria = st.text_area(
        "Критерии успеха",
        placeholder="По каким измеримым признакам вы примете результат?",
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
            "success_criteria": success_criteria.strip(),
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
        "Просмотр, рейтинг и сохранение относятся к этой версии. "
        "После изменения полей снова нажмите «Подтвердить карточку»."
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
        "success_criteria": "Критерии успеха",
        "contact": "Контакт",
        "interaction": "Формат взаимодействия",
    }

    for field, label in labels.items():
        st.markdown(f"**{label}**")
        st.write(task.get(field) or "Пока не указано")

    # Получаем рейтинг из бэкенда.
    rating = calculate_rating(task)

    st.divider()
    st.subheader("Рейтинг готовности")

    score_column, level_column = st.columns(2)

    with score_column:
        st.metric("Баллы", f"{rating['score']} / 100")

    with level_column:
        st.metric("Уровень", rating["level"])

    st.progress(rating["score"] / 100)

    st.markdown("**За что начислены баллы**")

    for item in rating["breakdown"]:
        st.write(
            f"{item['name']}: "
            f"{item['earned']} из {item['maximum']}"
        )

    st.markdown("**Как повысить рейтинг**")

    if rating["tips"]:
        for tip in rating["tips"]:
            st.info(tip)
    else:
        st.success("Все разделы заполнены и подтверждены!")

    # Сохраняем подтверждённую карточку в SQLite.
    st.divider()
    st.subheader("Сохранение")

    st.caption(
        "Карточка сохраняется как черновик и пока не публикуется. "
        "В этой версии приложения изменённая карточка "
        "сохраняется отдельной записью."
    )

    already_saved = st.session_state.last_saved_task == task

    if already_saved:
        st.success(
            f"Эта версия сохранена: задача "
            f"№{st.session_state.last_saved_id}."
        )
    else:
        if st.button("Сохранить карточку в базу"):
            try:
                task_id = save_task(task)

                st.session_state.last_saved_task = task.copy()
                st.session_state.last_saved_id = task_id

                st.rerun()
            except Exception as error:
                st.error(f"Не удалось сохранить карточку: {error}")