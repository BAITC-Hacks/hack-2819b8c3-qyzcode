import json
import sqlite3
from pathlib import Path



# База будет создана рядом с этим файлом.
DB_PATH = Path(__file__).with_name("ai_sana.db")


def init_db():
    """Создаёт таблицы задач и откликов."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft'
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                team_name TEXT NOT NULL,
                idea TEXT NOT NULL,
                plan TEXT NOT NULL,
                deadline TEXT NOT NULL,
                prototype_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)


def save_task(task):
    """Сохраняет новую карточку и возвращает её номер."""
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

def create_proposal(task_id, team_name, idea, plan, deadline, prototype_url):
    """Сохраняет отклик на опубликованную задачу."""
    fields = {
        "Название команды": team_name,
        "Идея": idea,
        "План": plan,
        "Срок": deadline,
        "Ссылка на прототип": prototype_url,
    }

    for label, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Заполните поле: {label}")

    prototype_url = prototype_url.strip()

    # Базовая проверка ссылки. Доступность сайта пока не проверяем.
    from urllib.parse import urlsplit

    parsed_url = urlsplit(prototype_url)

    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError("Укажите полную ссылку: https://example.com")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        task = connection.execute(
            "SELECT status FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if task is None:
            raise ValueError("Задача не найдена.")

        if task[0] != "published":
            raise ValueError("Можно откликаться только на опубликованные задачи.")

        cursor = connection.execute(
            """
            INSERT INTO proposals (
                task_id, team_name, idea, plan, deadline, prototype_url
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                team_name.strip(),
                idea.strip(),
                plan.strip(),
                deadline.strip(),
                prototype_url,
            ),
        )

        return cursor.lastrowid


def get_proposals(task_id):
    """Возвращает все отклики на выбранную задачу."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT *
            FROM proposals
            WHERE task_id = ?
            ORDER BY id DESC
            """,
            (task_id,),
        ).fetchall()

    return [dict(row) for row in rows]
def set_proposal_status(proposal_id, status):
    """Сохраняет решение бизнеса по отклику."""
    if status not in ("accepted", "rejected"):
        raise ValueError("Допустимые статусы: accepted или rejected.")

    with sqlite3.connect(DB_PATH) as connection:
        proposal = connection.execute(
            "SELECT id FROM proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()

        if proposal is None:
            raise ValueError("Отклик не найден.")

        connection.execute(
            "UPDATE proposals SET status = ? WHERE id = ?",
            (status, proposal_id),
        )

def get_task(task_id):
    """Возвращает одну задачу по номеру."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        row = connection.execute(
            "SELECT id, content, status FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

    if row is None:
        raise ValueError("Задача не найдена.")

    task = json.loads(row["content"])
    task["id"] = row["id"]
    task["status"] = row["status"]
    return task


def update_task(task_id, changes):
    """Изменяет поля карточки и сбрасывает подтверждение."""
    allowed_fields = {
        "title",
        "topic",
        "context",
        "need",
        "users",
        "data",
        "constraints",
        "result",
        "success_criteria",
        "contact",
        "interaction",
    }

    if not changes:
        raise ValueError("Нет изменений для сохранения.")

    for field, value in changes.items():
        if field not in allowed_fields:
            raise ValueError(f"Нельзя изменить поле: {field}")

        if not isinstance(value, str):
            raise ValueError(f"Поле {field} должно содержать текст.")

    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT content FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Задача не найдена.")

        task = json.loads(row[0])

        for field, value in changes.items():
            task[field] = value.strip()

        task["confirmed"] = False

        connection.execute(
            """
            UPDATE tasks
            SET content = ?, status = 'draft'
            WHERE id = ?
            """,
            (json.dumps(task, ensure_ascii=False), task_id),
        )


def confirm_task(task_id):
    """Подтверждает текущую сохранённую версию карточки."""
    with sqlite3.connect(DB_PATH) as connection:
        row = connection.execute(
            "SELECT content FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Задача не найдена.")

        task = json.loads(row[0])

        if not task.get("title", "").strip():
            raise ValueError("Добавьте название задачи.")

        task["confirmed"] = True

        connection.execute(
            "UPDATE tasks SET content = ? WHERE id = ?",
            (json.dumps(task, ensure_ascii=False), task_id),
        )

def init_teams():
    """Создаёт профили команд и таблицу подтверждённых этапов."""
    profiles = [
        ("QyzCode", "Торговля", "Python, анализ данных", "Streamlit, SQLite"),
        ("DataTeam", "Аналитика", "Python, SQL", "Pandas"),
        ("EduAI", "Образование", "Python, интерфейсы", "Streamlit"),
        ("WebTeam", "Веб-сервисы", "JavaScript, дизайн", "React"),
        ("LogicAI", "Логистика", "Python, оптимизация", "FastAPI"),
    ]

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                interests TEXT NOT NULL,
                skills TEXT NOT NULL,
                technologies TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS completed_stages (
                proposal_id INTEGER PRIMARY KEY,
                team_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                points INTEGER NOT NULL,
                FOREIGN KEY (proposal_id) REFERENCES proposals(id),
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
        """)

        connection.executemany(
            """
            INSERT OR IGNORE INTO teams (
                name, interests, skills, technologies
            )
            VALUES (?, ?, ?, ?)
            """,
            profiles,
        )


def get_teams():
    """Возвращает профили и заработанные командами баллы."""
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute("""
            SELECT
                teams.*,
                COALESCE(
                    (
                        SELECT SUM(points)
                        FROM completed_stages
                        WHERE team_id = teams.id
                    ),
                    0
                ) AS points
            FROM teams
            ORDER BY points DESC, name
        """).fetchall()

    return [dict(row) for row in rows]


def confirm_stage(proposal_id, description):
    """Подтверждает один выполненный этап выбранной команды."""
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Опишите фактически выполненную работу.")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        proposal = connection.execute(
            "SELECT team_name, status FROM proposals WHERE id = ?",
            (proposal_id,),
        ).fetchone()

        if proposal is None:
            raise ValueError("Отклик не найден.")

        team_name, status = proposal

        if status != "accepted":
            raise ValueError("Бизнес должен сначала выбрать эту команду.")

        team = connection.execute(
            "SELECT id FROM teams WHERE name = ?",
            (team_name,),
        ).fetchone()

        if team is None:
            raise ValueError(
                "У команды нет профиля. Используйте название из списка команд."
            )

        completed = connection.execute(
            "SELECT proposal_id FROM completed_stages WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()

        if completed is not None:
            raise ValueError("За этот этап баллы уже начислены.")

        connection.execute(
            """
            INSERT INTO completed_stages (
                proposal_id, team_id, description, points
            )
            VALUES (?, ?, ?, ?)
            """,
            (proposal_id, team[0], description.strip(), 10),
        )

    return 10
if __name__ == "__main__":
    init_db()

    tasks = get_tasks()
    print("Задач в базе:", len(tasks))

    for task in tasks:
        print(f"№{task['id']}: {task['title']}")