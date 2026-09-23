import json
import sqlite3
from urllib.parse import urlparse
from pathlib import Path



# База будет создана рядом с этим файлом.
DB_PATH = Path(__file__).with_name("ai_sana.db")


def init_db():
    """Создаёт таблицу задач, если её ещё нет."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft'
            )
        """)
        connection.execute("""CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            interests TEXT NOT NULL DEFAULT '',
            skills TEXT NOT NULL DEFAULT '',
            technologies TEXT NOT NULL DEFAULT ''
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES tasks(id),
            team_id INTEGER NOT NULL REFERENCES teams(id),
            idea TEXT NOT NULL, plan TEXT NOT NULL,
            deadline TEXT NOT NULL, link TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            milestone TEXT NOT NULL DEFAULT '',
            progress_points INTEGER NOT NULL DEFAULT 0
        )""")


def save_task(task):
    """Сохраняет новую карточку и возвращает её номер."""
    task = dict(task)
    task.pop("id", None)
    task.pop("status", None)
    content = json.dumps(task, ensure_ascii=False)

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (content) VALUES (?)",
            (content,),
        )
        return cursor.lastrowid


def get_tasks():
    """Возвращает все сохранённые карточки."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, content, status FROM tasks ORDER BY id DESC"
        ).fetchall()

    tasks = []

    for row in rows:
        task = json.loads(row["content"])
        task["id"] = row["id"]
        task["status"] = row["status"]
        tasks.append(task)

    return tasks

def publish_task(task_id):
    """Публикует подтверждённую задачу."""
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT content FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Задача не найдена.")

        task = json.loads(row[0])

        if not task.get("confirmed", False):
            raise ValueError("Сначала подтвердите карточку.")

        if not task.get("title", "").strip():
            raise ValueError("Добавьте название задачи.")

        if not task.get("need", "").strip():
            raise ValueError("Добавьте потребность.")

        connection.execute(
            "UPDATE tasks SET status = 'published' WHERE id = ?",
            (task_id,),
        )


def get_published_tasks():
    """Возвращает только опубликованные задачи."""
    return [
        task
        for task in get_tasks()
        if task["status"] == "published"
    ]


def get_task(task_id):
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT content, status FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise ValueError("Задача не найдена.")
    return {**json.loads(row[0]), "id": task_id, "status": row[1]}


def update_task(task_id, task):
    """Update one record; unconfirmed edits remove it from the public catalog."""
    task = dict(task)
    task.pop("id", None)
    task.pop("status", None)
    if task.get("confirmed") and not (
        task.get("title", "").strip() and task.get("need", "").strip()
    ):
        raise ValueError("Заполните название и потребность.")
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT status FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Задача не найдена.")
        status = row[0] if task.get("confirmed") else "draft"
        connection.execute(
            "UPDATE tasks SET content = ?, status = ? WHERE id = ?",
            (json.dumps(task, ensure_ascii=False), status, task_id),
        )


def save_team(name, interests="", skills="", technologies=""):
    if not name.strip():
        raise ValueError("Введите название команды.")
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "INSERT OR IGNORE INTO teams (name, interests, skills, technologies) VALUES (?, ?, ?, ?)",
            (name.strip(), interests.strip(), skills.strip(), technologies.strip()),
        )
        return connection.execute(
            "SELECT id FROM teams WHERE name = ?", (name.strip(),)
        ).fetchone()[0]


def get_teams():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(
            "SELECT teams.*, COALESCE((SELECT SUM(progress_points) FROM proposals "
            "WHERE team_id = teams.id), 0) AS points FROM teams ORDER BY name"
        )]


def submit_proposal(task_id, team_id, idea, plan, deadline, link):
    values = [idea.strip(), plan.strip(), deadline.strip(), link.strip()]
    if not all(values):
        raise ValueError("Заполните идею, план, срок и ссылку на прототип.")
    url = urlparse(values[3])
    if url.scheme not in ("http", "https") or not url.netloc:
        raise ValueError("Укажите ссылку, начинающуюся с https:// или http://.")
    with sqlite3.connect(DB_PATH) as connection:
        task = connection.execute("SELECT status FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task is None or task[0] != "published":
            raise ValueError("Отклик доступен только на опубликованную задачу.")
        if connection.execute("SELECT id FROM teams WHERE id = ?", (team_id,)).fetchone() is None:
            raise ValueError("Выберите существующую команду.")
        cursor = connection.execute(
            "INSERT INTO proposals (task_id, team_id, idea, plan, deadline, link) VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, team_id, *values),
        )
        return cursor.lastrowid


def get_proposals(task_id):
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(
            "SELECT proposals.*, teams.name AS team_name FROM proposals "
            "JOIN teams ON teams.id = proposals.team_id WHERE task_id = ? ORDER BY proposals.id",
            (task_id,),
        )]


def decide_proposal(proposal_id, decision):
    if decision not in ("selected", "rejected"):
        raise ValueError("Недопустимое решение.")
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "UPDATE proposals SET status = ? WHERE id = ?", (decision, proposal_id)
        )
        if cursor.rowcount != 1:
            raise ValueError("Отклик не найден.")


def confirm_milestone(proposal_id, evidence):
    """Award once, only to a selected proposal after explicit business confirmation."""
    if not evidence.strip():
        raise ValueError("Опишите проверенный результат этапа.")
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "UPDATE proposals SET milestone = ?, progress_points = 10 "
            "WHERE id = ? AND status = 'selected' AND progress_points = 0",
            (evidence.strip(), proposal_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Этап уже подтверждён или команда не выбрана.")


if __name__ == "__main__":
    init_db()

    tasks = get_tasks()
    print("Задач в базе:", len(tasks))

    for task in tasks:
        print(f"№{task['id']}: {task['title']}")
