def create_task():
    """Создаёт пустую карточку задачи."""
    return {
        "title": "",
        "industry": "",
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
    """Возвращает рейтинг, его расшифровку и подсказки."""
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
        filled = all(
            isinstance(task.get(field), str)
            and bool(task[field].strip())
            for field in fields
        )

        earned = (
            points
            if filled and task.get("confirmed", False)
            else 0
        )

        score += earned

        breakdown.append({
            "name": name,
            "earned": earned,
            "maximum": points,
        })

        if not filled:
            tips.append(
                f"Дополните раздел «{name}» "
                f"и подтвердите карточку: +{points} баллов."
            )

    if not task.get("confirmed", False):
        tips.append(
            "Подтвердите карточку, чтобы получить баллы."
        )

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