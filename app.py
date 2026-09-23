"""AI Sana: integrated Streamlit hackathon prototype."""
import os
import sqlite3
from pathlib import Path
import streamlit as st
from backend import create_task, calculate_rating, get_catalog
from database import (
    init_db, save_task, update_task, get_task, get_tasks, publish_task,
    get_teams, save_team, submit_proposal, get_proposals,
    decide_proposal, confirm_milestone,
)
from integration import normalize_card, clarify, apply_answers
from task_ai import InputValidationError

st.set_page_config(page_title="AI Sana", page_icon="💡", layout="wide")
st.markdown("<style>" + Path(__file__).with_name("styles.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)

env_path = Path(__file__).with_name(".env")
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() in {"OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_TIMEOUT_SECONDS"}:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ.setdefault(key.strip(), value)

try:
    init_db()
except sqlite3.Error:
    st.error("Не удалось открыть базу данных. Проверьте доступ к папке проекта.")
    st.stop()

LABELS = {
    "title": "Название задачи", "context": "Контекст — что происходит сейчас?",
    "need": "Потребность — что нужно изменить?", "users": "Пользователи",
    "data": "Данные и материалы", "constraints": "Ограничения",
    "result": "Ожидаемый результат", "success_criteria": "Критерии успеха",
    "contact": "Контакт представителя бизнеса", "interaction": "Формат взаимодействия",
}
TOPICS = ["Торговля", "Образование", "Медицина", "Логистика", "Другое"]
defaults = {"draft": normalize_card(create_task()), "task_id": None,
            "analysis": None, "revision": 0, "page": "Создать задачу"}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value
# Compatibility with the earlier frontend session.
st.session_state.draft = normalize_card(st.session_state.draft)


def load_editor(task=None):
    st.session_state.draft = normalize_card(task or create_task())
    st.session_state.task_id = task.get("id") if task else None
    st.session_state.analysis = None
    st.session_state.revision += 1
    st.session_state.page = "Создать задачу"


def feedback(message):
    st.session_state.flash = message
    st.rerun()


def details(task):
    task = normalize_card(task)
    st.write("Тема:", task["topic"])
    if task["description"]:
        st.markdown("**Исходное описание**")
        st.write(task["description"])
    for field, label in LABELS.items():
        if field != "title":
            st.markdown(f"**{label}**")
            st.write(task[field] or "Пока не указано")


def show_rating(task):
    rating = calculate_rating(task)
    left, right = st.columns(2)
    left.metric("Рейтинг", f"{rating['score']} / 100")
    right.metric("Готовность", rating["level"])
    st.progress(rating["score"] / 100)
    with st.expander("Расшифровка баллов и подсказки"):
        for item in rating["breakdown"]:
            st.write(f"{item['name']}: {item['earned']} / {item['maximum']}")
        for tip in rating["tips"]:
            st.info(tip)


st.sidebar.markdown('<div class="sana-brand">AI <span>Sana.</span><small>ПРАКТИКА СО СМЫСЛОМ</small></div>', unsafe_allow_html=True)
role = st.sidebar.radio("Режим демонстрации", ["Бизнес", "Команда"], key="role")
page = st.sidebar.radio("Раздел", ["Создать задачу", "Каталог задач", "Кабинет бизнеса"], key="page")
st.sidebar.caption("Демонстрация без регистрации. Переключение роли не является защитой доступа.")
st.sidebar.button("Новая задача", on_click=load_editor, disabled=role != "Бизнес")
st.markdown('<div class="sana-header"><div><h1>От задачи — к решению</h1><p>Бизнес делится вызовами. Команды предлагают идеи.</p></div><span class="sana-chip">AI SANA · ПРАКТИЧЕСКИЙ ХАКАТОН</span></div>', unsafe_allow_html=True)
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))


def render_catalog():
    st.subheader("Каталог задач")
    st.caption("Все опубликованные задачи доступны каждой команде, независимо от рейтинга.")
    catalog = get_catalog()
    a, b, c = st.columns(3)
    a.metric("Открытых задач", len(catalog))
    b.metric("Готовы к работе · 70+", sum(t["score"] >= 70 for t in catalog))
    c.metric("Студенческих команд", len(get_teams()))
    topics = sorted({t["topic"] for t in catalog})
    a, b = st.columns(2)
    topic = a.selectbox("Тема", ["Все темы"] + topics)
    level = b.selectbox("Готовность", ["Все уровни", "Черновик", "Рабочая", "Готовая", "Приоритетная"])
    catalog = get_catalog(None if topic == "Все темы" else topic,
                          None if level == "Все уровни" else level)
    if not catalog:
        st.info("Задач по этим условиям пока нет. Опубликуйте задачу или измените фильтры.")

    if role == "Команда":
        with st.expander("Добавить профиль команды"):
            with st.form("team_form"):
                name = st.text_input("Название команды")
                interests = st.text_input("Интересы")
                skills = st.text_input("Навыки")
                technologies = st.text_input("Технологии")
                if st.form_submit_button("Добавить команду"):
                    save_team(name, interests, skills, technologies)
                    feedback("Профиль команды доступен в списке.")
        teams = get_teams()
        if teams:
            team_id = st.selectbox("Ваша команда", [t["id"] for t in teams],
                format_func=lambda tid: next(t["name"] for t in teams if t["id"] == tid))
        else:
            team_id = None
            st.info("Добавьте профиль команды, чтобы отправить предложение.")

    for task in catalog:
        with st.expander(f"№{task['id']} · {task['title']} — {task['score']}/100 · {task['level']}"):
            details(task)
            # Do not nest expanders: render the summary directly here.
            st.write("Рейтинг:", task["score"], "/ 100")
            if role == "Команда" and team_id is not None:
                with st.form(f"proposal_{task['id']}"):
                    idea = st.text_area("Идея решения")
                    plan = st.text_area("План работы")
                    deadline = st.text_input("Срок выполнения")
                    link = st.text_input("Ссылка на прототип", placeholder="https://...")
                    if st.form_submit_button("Отправить предложение", type="primary"):
                        submit_proposal(task["id"], team_id, idea, plan, deadline, link)
                        feedback("Предложение отправлено. Решение принимает бизнес.")


def render_business():
    st.subheader("Кабинет бизнеса")
    if role != "Бизнес":
        st.info("Для демонстрации выбора команд переключите режим на «Бизнес».")
        return
    tasks = get_tasks()
    if not tasks:
        st.info("Сохранённых задач пока нет.")
    statuses = {"pending": "Ожидает решения", "selected": "Выбрана", "rejected": "Отклонена"}
    for task in tasks:
        with st.expander(f"№{task['id']} · {task['title'] or 'Без названия'}"):
            st.write("Публикация:", "В каталоге" if task["status"] == "published" else "Черновик")
            rating = calculate_rating(task)
            st.write("Рейтинг:", rating["score"], "/ 100 ·", rating["level"])
            st.button("Редактировать", key=f"edit_{task['id']}", on_click=load_editor, args=(task,))
            if task["status"] != "published":
                if st.button("Опубликовать", key=f"pub_{task['id']}"):
                    publish_task(task["id"])
                    feedback("Задача опубликована.")
            st.markdown("**Предложения команд**")
            proposals = get_proposals(task["id"])
            if not proposals:
                st.caption("Откликов пока нет.")
            for p in proposals:
                st.divider()
                st.markdown(f"**{p['team_name']} — {statuses[p['status']]}**")
                st.write("Идея:", p["idea"])
                st.write("План:", p["plan"])
                st.write("Срок:", p["deadline"])
                st.link_button("Открыть прототип", p["link"])
                a, b = st.columns(2)
                if a.button("Выбрать", key=f"select_{p['id']}", disabled=p["status"] == "selected"):
                    decide_proposal(p["id"], "selected")
                    feedback("Команда выбрана. Другие предложения остаются доступными.")
                if b.button("Отклонить", key=f"reject_{p['id']}", disabled=p["status"] == "rejected"):
                    decide_proposal(p["id"], "rejected")
                    feedback("Предложение отклонено.")
                if p["progress_points"]:
                    st.success(f"Подтверждён этап: {p['milestone']} · +{p['progress_points']} баллов")
                elif p["status"] == "selected":
                    with st.form(f"milestone_{p['id']}"):
                        evidence = st.text_area("Какой результат этапа вы проверили?")
                        checked = st.checkbox("Подтверждаю, что результат получен и проверен")
                        if st.form_submit_button("Подтвердить этап: +10 баллов"):
                            if not checked:
                                st.warning("Подтвердите проверку результата.")
                            else:
                                confirm_milestone(p["id"], evidence)
                                feedback("Команде начислено 10 баллов за подтверждённый этап.")
    teams = get_teams()
    if teams:
        st.subheader("Баллы команд за подтверждённые этапы")
        st.table([{"Команда": t["name"], "Баллы": t["points"]} for t in teams])


def render_editor():
    if role != "Бизнес":
        st.info("Для заполнения задачи выберите режим «Бизнес». Команды отправляют предложения в каталоге.")
        return
    draft = st.session_state.draft
    revision = st.session_state.revision
    st.subheader("Создайте задачу для команды")
    st.markdown('<div class="sana-steps"><span>01 · Опишите проблему</span><span>02 · Уточните детали</span><span>03 · Подтвердите и опубликуйте</span></div>', unsafe_allow_html=True)
    st.caption("Перед переходом в другой раздел сохраните черновик. Подтверждение и публикация выполняются вручную.")
    analysis = st.session_state.analysis
    if analysis:
        if analysis["mode"] == "openai":
            st.success("Уточняющие вопросы подготовлены ИИ.")
        else:
            st.info("Резервные вопросы: работает локальная заглушка, а не языковая модель.")
            reasons = {"offline_requested": "Выбран режим без API.", "missing_api_key": "Ключ API не настроен.",
                       "timeout": "ИИ не ответил вовремя.", "network_error": "Сервис временно недоступен.",
                       "invalid_response": "Ответ ИИ не прошёл проверку формата.", "rate_limit": "Достигнут лимит запросов API."}
            st.caption(reasons.get(analysis["fallback_reason"], "Сервис ИИ недоступен; можно продолжить с резервными вопросами."))
        with st.form(f"answers_{revision}"):
            answers = [st.text_area(q["question"], key=f"answer_{revision}_{i}", max_chars=4000)
                       for i, q in enumerate(analysis["questions"])]
            if st.form_submit_button("Перенести ответы в карточку"):
                if not any(a.strip() for a in answers):
                    st.warning("Введите хотя бы один ответ.")
                else:
                    st.session_state.draft = apply_answers(draft, analysis["questions"], answers)
                    st.session_state.analysis = None
                    st.session_state.revision += 1
                    feedback("Ответы перенесены. Проверьте карточку и подтвердите сведения.")

    with st.form(f"editor_{revision}"):
        description = st.text_area("Исходное описание проблемы", value=draft.get("description", ""),
            placeholder="Например: в магазине много списаний, хотим их сократить.", max_chars=12000)
        topics = list(dict.fromkeys(TOPICS + [draft["topic"]]))
        topic = st.selectbox("Тема задачи", topics, index=topics.index(draft["topic"]))
        values = {}
        st.markdown("**Карточка задачи**")
        for index, (field, label) in enumerate(LABELS.items()):
            if index % 2 == 0:
                columns = st.columns(2)
            with columns[index % 2]:
                widget = st.text_input if field in ("title", "contact") else st.text_area
                values[field] = widget(label, value=draft.get(field, ""), max_chars=4000)
        offline = st.checkbox("Использовать резервные вопросы без API", value=not bool(os.getenv("OPENAI_API_KEY")))
        confirmed = st.checkbox("Подтверждаю достоверность заполненных сведений", value=False)
        action_columns = st.columns([1, 1, 1.5])
        with action_columns[0]:
            ask = st.form_submit_button("Уточнить с ИИ")
        with action_columns[1]:
            save_draft = st.form_submit_button("Сохранить черновик")
        with action_columns[2]:
            confirm = st.form_submit_button("Подтвердить и сохранить карточку", type="primary")

    if ask or save_draft or confirm:
        candidate = {**{k: v.strip() for k, v in values.items()},
                     "topic": topic, "description": description.strip(), "confirmed": False}
        st.session_state.draft = candidate
        if ask:
            with st.spinner("Подготавливаем вопросы…"):
                result = clarify(candidate, offline=offline)
            st.session_state.analysis = result
            st.session_state.revision += 1
            st.rerun()
        elif confirm and (not confirmed or not candidate["title"] or not candidate["need"]):
            st.warning("Заполните название и потребность, затем поставьте галочку подтверждения.")
        elif save_draft and not any(candidate[k] for k in LABELS) and not candidate["description"]:
            st.warning("Введите описание или заполните хотя бы одно поле.")
        else:
            candidate["confirmed"] = bool(confirm)
            task_id = st.session_state.task_id
            if task_id is None:
                task_id = save_task(candidate)
            else:
                update_task(task_id, candidate)
            st.session_state.task_id = task_id
            st.session_state.draft = candidate
            st.session_state.analysis = None
            st.session_state.revision += 1
            feedback(f"Задача №{task_id} сохранена. " + ("Карточка подтверждена." if confirm else "Черновик не опубликован."))

    task_id = st.session_state.task_id
    if task_id is not None:
        saved = get_task(task_id)
        st.divider()
        st.subheader(f"Сохранённая версия · №{task_id}")
        st.caption("Рейтинг и публикация относятся к сохранённой версии. После правок подтвердите и сохраните карточку ещё раз.")
        show_rating(saved)
        if saved["status"] == "published":
            st.success("Задача доступна в каталоге.")
        elif saved.get("confirmed"):
            if st.button("Опубликовать сохранённую карточку", type="primary"):
                publish_task(task_id)
                feedback("Задача опубликована. Теперь команда может отправить предложение.")


try:
    if page == "Каталог задач":
        render_catalog()
    elif page == "Кабинет бизнеса":
        render_business()
    else:
        render_editor()
except InputValidationError:
    st.warning("Для уточнения введите описание или поля карточки. Проверьте длину: описание до 12000 символов, поле до 4000, весь текст до 50000.")
except ValueError as error:
    st.warning(str(error))
except sqlite3.Error:
    st.error("Не удалось выполнить действие с базой. Проверьте доступ к файлу и повторите попытку.")
