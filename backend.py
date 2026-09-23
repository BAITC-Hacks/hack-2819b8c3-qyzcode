from database import init_db, save_task, get_published_tasks
def create_task():
    """Создаёт пустую карточку задачи."""
    return {
        "title": "",
        "topic": "",
        "context": "",
        "need": "",
        "users": "",
        "data": "",
        "constraints": "",
        "result": "",
        "success_criteria": "",
        "contact": "",
        "interaction": "",
        "confirmed": False,
    }


def calculate_rating(task):
    """Считает баллы и возвращает подсказки."""
    rules = [
        ("Контекст и потребность", ["context", "need"], 20),
        ("Данные и материалы", ["data"], 20),
        ("Ожидаемый результат", ["result"], 15),
        ("Критерии успеха", ["success_criteria"], 15),
        ("Ограничения", ["constraints"], 10),
        ("Пользователи", ["users"], 10),
        ("Связь с бизнесом", ["contact", "interaction"], 10),
    ]

    score = 0
    tips = []
    breakdown = []

    for name, fields, points in rules:
        # Для баллов должны быть заполнены все поля этой группы.
        filled = all(
            isinstance(task.get(field), str)
            and task[field].strip()
            for field in fields
        )

        earned = points if filled and task.get("confirmed", False) else 0
        score += earned
        breakdown.append({
            "name": name,
            "earned": earned,
            "maximum": points,
        })

        if not filled:
            tips.append(f"Дополните раздел «{name}»: +{points} баллов.")

    if not task.get("confirmed", False):
        tips.append("Подтвердите карточку, чтобы получить баллы.")

    if score < 40:
        level = "Черновик"
    elif score < 70:
        level = "Рабочая"
    elif score < 90:
        level = "Готовая"
    else:
        level = "Приоритетная"

    return {
        "score": score,
        "level": level,
        "breakdown": breakdown,
        "tips": tips,
    }
def get_catalog(topic=None, level=None):
    """Возвращает каталог с фильтрами и сортировкой по рейтингу."""
    tasks = get_published_tasks()
    catalog = []

    for task in tasks:
        rating = calculate_rating(task)

        task["score"] = rating["score"]
        task["level"] = rating["level"]

        # У старых задач темы может не быть.
        task["topic"] = task.get("topic", "").strip() or "Без темы"

        # Если тема указана в фильтре, оставляем только совпадения.
        if topic and task["topic"].casefold() != topic.strip().casefold():
            continue

        # Аналогично проверяем уровень готовности.
        if level and task["level"].casefold() != level.strip().casefold():
            continue

        catalog.append(task)

    return sorted(
        catalog,
        key=lambda task: task["score"],
        reverse=True,
    )

# Этот пример запускается только при запуске backend.py.
if __name__ == "__main__":
    task = create_task()

    task["title"] = "Помощник для магазина"
    task["context"] = "Сотрудники отвечают на повторяющиеся вопросы."
    task["need"] = "Сократить время на ответы покупателям."
    task["users"] = "Покупатели магазина"

    # В приложении это значение задаст кнопка подтверждения.
    task["confirmed"] = True

    rating = calculate_rating(task)

    print("Задача:", task["title"])
    print("Рейтинг:", rating["score"], "/ 100")
    print("Уровень:", rating["level"])

    print("\nРасшифровка:")
    for item in rating["breakdown"]:
        print(f"- {item['name']}: {item['earned']}/{item['maximum']}")

    print("\nКак повысить рейтинг:")
    for tip in rating["tips"]:
        print("-", tip)
    init_db()
    task_id = save_task(task)
    print("\nЗадача сохранена! Её номер:", task_id)
