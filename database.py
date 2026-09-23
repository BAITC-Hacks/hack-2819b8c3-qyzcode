"""Merged backend contracts and migrations for both teammates' SQLite layouts."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

DB_PATH = Path(__file__).with_name("ai_sana.db")
TASK_FIELDS = {"title", "topic", "context", "need", "users", "data", "constraints",
               "result", "success_criteria", "contact", "interaction", "description"}


@contextmanager
def connect():
    connection = sqlite3.connect(DB_PATH, timeout=15)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    """Create tables and migrate existing backend/frontend data without deleting rows."""
    with connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft')""")
        c.execute("""CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
            interests TEXT NOT NULL DEFAULT '', skills TEXT NOT NULL DEFAULT '',
            technologies TEXT NOT NULL DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id),
            team_id INTEGER REFERENCES teams(id), team_name TEXT NOT NULL DEFAULT '',
            idea TEXT NOT NULL, plan TEXT NOT NULL, deadline TEXT NOT NULL,
            link TEXT NOT NULL DEFAULT '', prototype_url TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            milestone TEXT NOT NULL DEFAULT '', progress_points INTEGER NOT NULL DEFAULT 0)""")
        columns = {r[1] for r in c.execute("PRAGMA table_info(proposals)")}
        for name, sql_type in {
            "team_id": "INTEGER REFERENCES teams(id)",
            "team_name": "TEXT NOT NULL DEFAULT ''",
            "link": "TEXT NOT NULL DEFAULT ''",
            "prototype_url": "TEXT NOT NULL DEFAULT ''",
            "milestone": "TEXT NOT NULL DEFAULT ''",
            "progress_points": "INTEGER NOT NULL DEFAULT 0",
        }.items():
            if name not in columns:
                c.execute(f"ALTER TABLE proposals ADD COLUMN {name} {sql_type}")
        c.execute("""CREATE TABLE IF NOT EXISTS completed_stages (
            proposal_id INTEGER PRIMARY KEY REFERENCES proposals(id),
            team_id INTEGER NOT NULL REFERENCES teams(id),
            description TEXT NOT NULL, points INTEGER NOT NULL)""")

        # The backend stored team names; the frontend stored team IDs. Keep both APIs.
        rows = c.execute("SELECT id, team_id, team_name, link, prototype_url FROM proposals").fetchall()
        for pid, team_id, name, link, prototype_url in rows:
            if team_id is None:
                name = name.strip() or f"Команда из отклика №{pid}"
                c.execute("INSERT OR IGNORE INTO teams (name, interests, skills, technologies) VALUES (?, '', '', '')", (name,))
                team_id = c.execute("SELECT id FROM teams WHERE name = ?", (name,)).fetchone()[0]
            name = c.execute("SELECT name FROM teams WHERE id = ?", (team_id,)).fetchone()[0]
            url = link or prototype_url
            c.execute("UPDATE proposals SET team_id=?, team_name=?, link=?, prototype_url=? WHERE id=?",
                      (team_id, name, url, url, pid))
        c.execute("UPDATE proposals SET status='accepted' WHERE status='selected'")
        c.execute("""INSERT OR IGNORE INTO completed_stages (proposal_id, team_id, description, points)
            SELECT id, team_id, milestone, progress_points FROM proposals WHERE progress_points > 0""")
        # Mirror legacy columns for backwards compatibility, but count only the stage table.
        c.execute("""UPDATE proposals SET
            milestone=(SELECT description FROM completed_stages WHERE proposal_id=proposals.id),
            progress_points=(SELECT points FROM completed_stages WHERE proposal_id=proposals.id)
            WHERE id IN (SELECT proposal_id FROM completed_stages)""")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Заполните поле: {label}")
    return value.strip()


def save_task(task):
    task = dict(task)
    task.pop("id", None)
    task.pop("status", None)
    with connect() as c:
        return c.execute("INSERT INTO tasks (content) VALUES (?)",
                         (json.dumps(task, ensure_ascii=False),)).lastrowid


def get_tasks():
    with connect() as c:
        rows = c.execute("SELECT id, content, status FROM tasks ORDER BY id DESC").fetchall()
    return [{**json.loads(content), "id": tid, "status": status} for tid, content, status in rows]


def get_task(task_id):
    with connect() as c:
        row = c.execute("SELECT content, status FROM tasks WHERE id=?", (task_id,)).fetchone()
    if row is None:
        raise ValueError("Задача не найдена.")
    return {**json.loads(row[0]), "id": task_id, "status": row[1]}


def update_task(task_id, changes):
    """Backend contract: partial update preserves other fields and invalidates confirmation."""
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Нет изменений для сохранения.")
    for key, value in changes.items():
        if key not in TASK_FIELDS:
            raise ValueError(f"Нельзя изменить поле: {key}")
        if not isinstance(value, str):
            raise ValueError(f"Поле {key} должно содержать текст.")
    with connect() as c:
        row = c.execute("SELECT content FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("Задача не найдена.")
        task = json.loads(row[0])
        task.update({key: value.strip() for key, value in changes.items()})
        task["confirmed"] = False
        c.execute("UPDATE tasks SET content=?, status='draft' WHERE id=?",
                  (json.dumps(task, ensure_ascii=False), task_id))


def confirm_task(task_id):
    with connect() as c:
        row = c.execute("SELECT content FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("Задача не найдена.")
        task = json.loads(row[0])
        _text(task.get("title"), "Название задачи")
        _text(task.get("need"), "Потребность")
        task["confirmed"] = True
        c.execute("UPDATE tasks SET content=? WHERE id=?", (json.dumps(task, ensure_ascii=False), task_id))


def publish_task(task_id):
    with connect() as c:
        row = c.execute("SELECT content FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError("Задача не найдена.")
        task = json.loads(row[0])
        if task.get("confirmed") is not True:
            raise ValueError("Сначала подтвердите карточку.")
        _text(task.get("title"), "Название задачи")
        _text(task.get("need"), "Потребность")
        c.execute("UPDATE tasks SET status='published' WHERE id=?", (task_id,))


def get_published_tasks():
    return [task for task in get_tasks() if task["status"] == "published"]


def save_team(name, interests="", skills="", technologies=""):
    name = _text(name, "Название команды")
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO teams (name, interests, skills, technologies) VALUES (?, ?, ?, ?)",
                  (name, interests.strip(), skills.strip(), technologies.strip()))
        return c.execute("SELECT id FROM teams WHERE name=?", (name,)).fetchone()[0]


def init_teams():
    """Keep the backend participant's five example profiles as an explicit action."""
    init_db()
    profiles = [
        ("QyzCode", "Торговля", "Python, анализ данных", "Streamlit, SQLite"),
        ("DataTeam", "Аналитика", "Python, SQL", "Pandas"),
        ("EduAI", "Образование", "Python, интерфейсы", "Streamlit"),
        ("WebTeam", "Веб-сервисы", "JavaScript, дизайн", "React"),
        ("LogicAI", "Логистика", "Python, оптимизация", "FastAPI"),
    ]
    for profile in profiles:
        save_team(*profile)


def get_teams():
    with connect() as c:
        c.row_factory = sqlite3.Row
        return [dict(row) for row in c.execute("""SELECT teams.*,
            COALESCE((SELECT SUM(points) FROM completed_stages WHERE team_id=teams.id), 0) AS points
            FROM teams ORDER BY points DESC, name""")]


def _proposal_values(idea, plan, deadline, link):
    values = [_text(v, label) for v, label in zip(
        [idea, plan, deadline, link], ["Идея", "План", "Срок", "Ссылка на прототип"])]
    parsed = urlsplit(values[3])
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Укажите полную ссылку: https://example.com")
    return values


def submit_proposal(task_id, team_id, idea, plan, deadline, link):
    values = _proposal_values(idea, plan, deadline, link)
    with connect() as c:
        task = c.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        if task is None or task[0] != "published":
            raise ValueError("Можно откликаться только на опубликованную задачу.")
        team = c.execute("SELECT name FROM teams WHERE id=?", (team_id,)).fetchone()
        if team is None:
            raise ValueError("Выберите существующую команду.")
        return c.execute("""INSERT INTO proposals
            (task_id, team_id, team_name, idea, plan, deadline, link, prototype_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, team_id, team[0], *values, values[3])).lastrowid


def create_proposal(task_id, team_name, idea, plan, deadline, prototype_url):
    """Backend API retained; the UI uses the equivalent team-ID API."""
    _proposal_values(idea, plan, deadline, prototype_url)
    task = get_task(task_id)
    if task["status"] != "published":
        raise ValueError("Можно откликаться только на опубликованную задачу.")
    return submit_proposal(task_id, save_team(team_name), idea, plan, deadline, prototype_url)


def get_proposals(task_id):
    with connect() as c:
        c.row_factory = sqlite3.Row
        return [dict(row) for row in c.execute("""SELECT p.*, t.name AS current_team_name,
            COALESCE(s.description, '') AS stage_description, COALESCE(s.points, 0) AS stage_points
            FROM proposals p JOIN teams t ON t.id=p.team_id
            LEFT JOIN completed_stages s ON s.proposal_id=p.id
            WHERE p.task_id=? ORDER BY p.id DESC""", (task_id,))]


def set_proposal_status(proposal_id, status):
    if status not in ("accepted", "rejected"):
        raise ValueError("Допустимые статусы: accepted или rejected.")
    with connect() as c:
        if c.execute("UPDATE proposals SET status=? WHERE id=?", (status, proposal_id)).rowcount != 1:
            raise ValueError("Отклик не найден.")


def decide_proposal(proposal_id, decision):
    set_proposal_status(proposal_id, "accepted" if decision == "selected" else decision)


def confirm_stage(proposal_id, description):
    description = _text(description, "Фактически выполненная работа")
    with connect() as c:
        cursor = c.execute("""INSERT INTO completed_stages (proposal_id, team_id, description, points)
            SELECT id, team_id, ?, 10 FROM proposals WHERE id=? AND status='accepted'
            AND NOT EXISTS (SELECT 1 FROM completed_stages WHERE proposal_id=proposals.id)""",
            (description, proposal_id))
        if cursor.rowcount != 1:
            raise ValueError("Этап уже подтверждён или команда не выбрана.")
        c.execute("UPDATE proposals SET milestone=?, progress_points=10 WHERE id=?", (description, proposal_id))
    return 10


def confirm_milestone(proposal_id, evidence):
    return confirm_stage(proposal_id, evidence)


if __name__ == "__main__":
    init_db()
    tasks = get_tasks()
    print("База данных готова. Задач:", len(tasks))
    for task in tasks:
        print(f"№{task['id']}: {task.get('title', 'Без названия')}")
