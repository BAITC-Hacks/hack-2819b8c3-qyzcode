from database import init_db
from backend import get_catalog


def main():
    init_db()

    print("Все опубликованные задачи:")
    for task in get_catalog():
        print(
            f"№{task['id']}: {task['title']} "
            f"| {task['topic']} "
            f"| {task['score']}/100 "
            f"| {task['level']}"
        )

    print("\nВведите фильтры. Enter — пропустить фильтр.")
    topic = input("Тема: ").strip()
    level = input(
        "Уровень (Черновик / Рабочая / Готовая / Приоритетная): "
    ).strip()

    tasks = get_catalog(topic=topic, level=level)

    print("\nРезультат:")
    if not tasks:
        print("По этим фильтрам задач нет.")

    for task in tasks:
        print(
            f"№{task['id']}: {task['title']} "
            f"| {task['topic']} "
            f"| {task['score']}/100 "
            f"| {task['level']}"
        )


if __name__ == "__main__":
    main()