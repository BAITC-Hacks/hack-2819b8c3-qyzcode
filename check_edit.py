from backend import calculate_rating
from database import (
    init_db,
    get_tasks,
    get_task,
    update_task,
    confirm_task,
    publish_task,
)


def main():
    init_db()

    tasks = get_tasks()

    if not tasks:
        print("Сначала создайте задачу.")
        return

    for task in tasks:
        print(f"№{task['id']}: {task['title']}")

    try:
        task_id = int(input("\nНомер задачи для изменения: "))
        task = get_task(task_id)

        print("\nТекущая тема:", task.get("topic", ""))
        print("Критерии успеха:", task.get("success_criteria", ""))
        print("Enter — оставить поле без изменений.")

        topic = input("\nНовая тема: ").strip()
        criteria = input("Новые критерии успеха: ").strip()

        changes = {}

        if topic:
            changes["topic"] = topic

        if criteria:
            changes["success_criteria"] = criteria

        if not changes:
            print("Вы ничего не изменили.")
            return

        update_task(task_id, changes)
        task = get_task(task_id)

        print("\nИзменения сохранены. Проверьте карточку:")
        for field, value in task.items():
            print(f"{field}: {value}")

        answer = input("\nПодтвердить эту версию? Введите да: ")

        if answer.strip().lower() != "да":
            print("Карточка осталась неподтверждённым черновиком.")
            return

        confirm_task(task_id)

        task = get_task(task_id)
        rating = calculate_rating(task)

        print(f"\nРейтинг: {rating['score']}/100")
        print("Уровень:", rating["level"])

        answer = input("\nОпубликовать? Введите да: ")

        if answer.strip().lower() == "да":
            publish_task(task_id)
            print("Задача опубликована!")
        else:
            print("Карточка подтверждена, но пока не опубликована.")

    except ValueError as error:
        print("Ошибка:", error)


if __name__ == "__main__":
    main()