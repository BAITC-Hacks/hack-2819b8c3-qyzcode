import json
import sqlite3
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
if __name__ == "__main__":
    init_db()

    tasks = get_tasks()
    print("Задач в базе:", len(tasks))

    for task in tasks:
        print(f"№{task['id']}: {task['title']}")