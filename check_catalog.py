from database import init_db, get_tasks, publish_task
from backend import get_catalog


def main():
    init_db()

    tasks = get_tasks()

    if not tasks:
        print("В базе нет задач. Сначала запустите backend.py.")
        return

    print("Сохранённые задачи:")
    for task in tasks:
        print(
            f"№{task['id']}: {task['title']} "
            f"— статус: {task['status']}"
        )

    try:
        task_id = int(input("\nВведите номер задачи для публикации: "))
        publish_task(task_id)
    except ValueError as error:
        print("Не удалось опубликовать:", error)
        return

    print("\nЗадача опубликована!")
    print("\nКаталог:")

    for task in get_catalog():
        print(
            f"№{task['id']}: {task['title']} "
            f"— {task['score']}/100, {task['level']}"
        )


if __name__ == "__main__":
    main()