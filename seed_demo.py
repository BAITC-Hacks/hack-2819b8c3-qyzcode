"""Explicit, idempotent synthetic demo data. Existing user records are preserved."""
import json
from pathlib import Path

import database as db
from backend import calculate_rating

DEMO_VERSION = "ai-sana-demo-v1"


def demo_data():
    rows = [
        ("Торговля", "Снизить списание продуктов", "У магазина много списаний.",
         "Менеджер заказывает продукты вручную, часть остаётся непроданной.", "Точнее планировать закупки.",
         "Менеджер по закупкам", "Обезличенный CSV продаж и списаний за 8 недель.",
         "Таблица рекомендаций по закупкам и прототип прогноза.",
         "Ошибка прогноза на отложенных данных ниже базового среднего за неделю."),
        ("Образование", "Помощник по учебным материалам", "Студенты долго ищут нужные материалы.",
         "Материалы курса распределены по разным папкам.", "Сократить время поиска нужной темы.",
         "Студенты и преподаватели курса", "20 учебных PDF и перечень тем без персональных данных.",
         "Поиск по материалам с указанием источника.",
         "В 8 из 10 контрольных запросов найден нужный документ."),
        ("Логистика", "Обзор задержек доставки", "Хотим видеть причины задержек.",
         "Диспетчер вручную сверяет статусы доставок.", "Выявлять повторяющиеся причины опозданий.",
         "Диспетчеры склада", "CSV со временем отправки и прибытия 200 заказов без адресов.",
         "Дашборд задержек и список основных причин.",
         "Все 20 контрольных задержек верно отображаются в отчёте."),
        ("Торговля", "Анализ отзывов покупателей", "Нужен обзор частых жалоб из отзывов.",
         "Сотрудник вручную читает отзывы и отмечает темы.", "Собирать повторяющиеся проблемы по категориям.",
         "Менеджер клиентского сервиса", "100 синтетических отзывов и 10 размеченных примеров.",
         "Прототип классификации отзывов и сводка проблем.",
         "Не менее 8 из 10 контрольных отзывов отнесены к верной категории."),
        ("Другое", "Навигатор по внутренним инструкциям", "Сотрудники не находят актуальные инструкции.",
         "Инструкции лежат в общей папке без единого указателя.", "Находить актуальный документ по вопросу сотрудника.",
         "Новые сотрудники", "15 учебных инструкций с номерами версий.",
         "Прототип поиска с названием документа и номером версии.",
         "10 контрольных запросов возвращают актуальную версию инструкции."),
    ]
    targets = [20, 40, 70, 90, 100]
    cards = []
    teams = []
    proposals = []
    for i, row in enumerate(rows):
        topic, title, description, context, need, users, data, result, criteria = row
        card = {
            "title": "[Демо] " + title, "topic": topic, "description": description,
            "context": context, "need": need, "data": data if i >= 1 else "",
            "result": result if i >= 2 else "", "success_criteria": criteria if i >= 2 else "",
            "users": users if i >= 3 else "",
            "constraints": "7 дней, Python, только синтетические данные." if i >= 3 else "",
            "contact": "demo-business@example.com" if i >= 4 else "",
            "interaction": "Две консультации по 15 минут и итоговая проверка." if i >= 4 else "",
            "confirmed": True, "demo_key": f"{DEMO_VERSION}-{i}",
        }
        score = calculate_rating(card)["score"]
        assert score == targets[i]
        cards.append({**card, "score": score})
        teams.append({"name": f"[Демо] Команда {i + 1}", "interests": topic,
                      "skills": ["Анализ данных", "Поиск документов", "Визуализация", "NLP", "UX"][i],
                      "technologies": "Python, Streamlit, SQLite"})
        proposals.append({"task_index": i, "team_index": i,
            "idea": result, "plan": "Уточнить данные → подготовить прототип → проверить на примерах.",
            "deadline": "7 дней", "link": f"https://example.com/ai-sana-demo/{i + 1}"})
    return {"synthetic": True, "drafts": [{"text": r[2], "industry": r[0]} for r in rows],
            "cards": cards, "teams": teams, "proposals": proposals}


def seed():
    db.init_db()
    data = demo_data()
    added = 0
    with db.connect() as connection:
        existing = {}
        for tid, content in connection.execute("SELECT id, content FROM tasks"):
            key = json.loads(content).get("demo_key")
            if key:
                existing[key] = tid
        for i, card in enumerate(data["cards"]):
            if card["demo_key"] in existing:
                continue
            content = {k: v for k, v in card.items() if k != "score"}
            tid = connection.execute(
                "INSERT INTO tasks (content, status) VALUES (?, 'published')",
                (json.dumps(content, ensure_ascii=False),),
            ).lastrowid
            team = data["teams"][i]
            connection.execute(
                "INSERT OR IGNORE INTO teams (name, interests, skills, technologies) VALUES (?, ?, ?, ?)",
                (team["name"], team["interests"], team["skills"], team["technologies"]),
            )
            team_id = connection.execute("SELECT id FROM teams WHERE name = ?", (team["name"],)).fetchone()[0]
            proposal = data["proposals"][i]
            connection.execute(
                "INSERT INTO proposals (task_id, team_id, team_name, idea, plan, deadline, link, prototype_url) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (tid, team_id, team["name"], proposal["idea"], proposal["plan"], proposal["deadline"],
                 proposal["link"], proposal["link"]),
            )
            added += 1
    return added


if __name__ == "__main__":
    print("Добавлено демонстрационных задач:", seed())
