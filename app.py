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


# Данные текущей сессии.
if "confirmed_task" not in st.session_state:
    st.session_state.confirmed_task = None

if "last_saved_task" not in st.session_state:
    st.session_state.last_saved_task = None

if "last_saved_id" not in st.session_state:
    st.session_state.last_saved_id = None

# Сохраняем введённые поля при переключении разделов.
if "draft" not in st.session_state:
    st.session_state.draft = {
        "title": "",
        "industry": "Торговля",
        "context": "",
        "need": "",
        "users": "",
        "data": "",
        "constraints": "",
        "result": "",
        "success_criteria": "",
        "contact": "",
        "interaction": "",
    }


# Меню слева.
st.sidebar.title("💡 AI Sana")

page = st.sidebar.radio(
    "Раздел",
    [
        "Создать задачу",
        "Каталог задач",
        "Кабинет бизнеса",
    ],
)

st.sidebar.caption(
    "Перед переходом в другой раздел "
    "нажмите «Подтвердить карточку», чтобы сохранить введённые поля."
)


st.title("AI Sana")
st.write("Задачи бизнеса — решения студенческих команд.")


# Каталог пока не подключён.
if page == "Каталог задач":
    st.subheader("Каталог задач")
    st.info(
        "Здесь появятся опубликованные задачи, "
        "сортировка по рейтингу и фильтры."
    )
    st.caption(
        "Сохранённые черновики пока не публикуются в каталоге."
    )
    st.stop()


# Кабинет пока не подключён.
if page == "Кабинет бизнеса":
    st.subheader("Кабинет бизнеса")
    st.info(
        "Здесь появятся отклики студентов "
        "и кнопки «Выбрать» и «Отклонить»."
    )
    st.stop()


# Форма создания задачи.
st.subheader("Карточка бизнес-задачи")
st.caption(
    "Заполните известные сведения. "
    "Остальные можно дополнить позже."
)

draft = st.session_state.draft

industries = [
    "Торговля",
    "Образование",
    "Медицина",
    "Логистика",
    "Другое",
]

with st.form("task_form"):
    title = st.text_input(
        "Название задачи",
        value=draft["title"],
        placeholder="Например: уменьшить списание продуктов",
    )

    industry = st.selectbox(
        "Тема задачи",
        industries,
        index=industries.index(draft["industry"]),
    )

    context = st.text_area(
        "Контекст — что происходит сейчас?",
        value=draft["context"],
        placeholder="Как сейчас устроен процесс?",
    )

    need = st.text_area(
        "Потребность — что нужно изменить?",
        value=draft["need"],
        placeholder="Какую проблему вы хотите решить?",
    )

    users = st.text_area(
        "Пользователи",
        value=draft["users"],
        placeholder="Кто будет пользоваться решением?",
    )

    data = st.text_area(
        "Данные и материалы",
        value=draft["data"],
        placeholder="Какие таблицы, документы или примеры доступны?",
    )

    constraints = st.text_area(
        "Ограничения",
        value=draft["constraints"],
        placeholder="Сроки, технологии, доступы и другие условия",
    )

    result = st.text_area(
        "Ожидаемый результат",
        value=draft["result"],
        placeholder="Что команда должна передать в конце работы?",
    )

    success_criteria = st.text_area(
        "Критерии успеха",
        value=draft["success_criteria"],
        placeholder="По каким измеримым признакам вы примете результат?",
    )

    contact = st.text_input(
        "Контакт представителя бизнеса",
        value=draft["contact"],
        placeholder="Email или другой способ связи",
    )

    interaction = st.text_area(
        "Формат взаимодействия",
        value=draft["interaction"],
        placeholder="Как часто вы готовы отвечать на вопросы команды?",
    )

    confirmed = st.checkbox(
        "Подтверждаю достоверность заполненных сведений"
    )

    submitted = st.form_submit_button("Подтвердить карточку")


# Обрабатываем подтверждение формы.
if submitted:
    form_data = {
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
    }

    st.session_state.draft = form_data.copy()

    if not form_data["title"] or not form_data["need"]:
        st.warning("Заполните название задачи и потребность.")
    elif not confirmed:
        st.warning("Поставьте галочку подтверждения сведений.")
    else:
        st.session_state.confirmed_task = {
            **form_data,
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

    # Рейтинг рассчитывается в backend.py.
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

    # Сохранение в SQLite.
    st.divider()
    st.subheader("Сохранение")

    st.caption(
        "Карточка сохраняется как черновик. "
        "В этой версии изменённая карточка создаёт новую запись. "
        "Повторное сохранение той же версии блокируется "
        "только в текущей сессии."
    )

    already_saved = st.session_state.last_saved_task == task

    if already_saved:
        st.success(
            f"Эта версия сохранена: задача "
            f"№{st.session_state.last_saved_id}."
        )
    elif st.button("Сохранить карточку в базу"):
        try:
            task_id = save_task(task)
        except Exception as error:
            st.error(f"Не удалось сохранить карточку: {error}")
        else:
            st.session_state.last_saved_task = task.copy()
            st.session_state.last_saved_id = task_id
            st.rerun()