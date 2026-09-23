"""Deterministic fallback, explicitly not an LLM."""
from .schema import FIELDS

QUESTIONS = {
    "need": "Какую проблему нужно решить и что должно измениться для бизнеса?",
    "context": "Как сейчас выполняется работа и на каком шаге возникает проблема?",
    "data": "Какие данные, примеры или материалы доступны и как команда получит к ним доступ?",
    "result": "Какой конкретный результат должна передать команда: анализ, прототип или инструмент?",
    "success_criteria": "По какому измеримому показателю, целевому значению и способу проверки вы примете результат?",
    "constraints": "Какие сроки, технологии и ограничения доступа нужно учесть?",
    "users": "Кто будет пользоваться решением и для каких действий?",
    "contact": "Какой рабочий контакт представителя бизнеса можно указать для связи?",
    "interaction": "Как часто возможны консультации и как команда будет получать обратную связь?",
    "title": "Как кратко назвать задачу, чтобы было понятно, какой результат нужен?",
}


def local_analysis(description, card):
    missing = [field for field in FIELDS if not card[field].strip()]
    questions = dict(QUESTIONS)
    text = (description + " " + " ".join(card[f] for f in FIELDS)).casefold()
    if "кафе" in text or "ресторан" in text:
        questions["context"] = "Как сейчас устроено обслуживание в заведении и на каком этапе возникает проблема?"
        questions["data"] = "Есть ли примеры заказов или данные о времени обслуживания, доступные команде?"
    elif "магазин" in text:
        questions["context"] = "Какой процесс магазина нужно улучшить и как он работает сейчас?"
        questions["data"] = "Есть ли доступные примеры обращений покупателей, заказов или других нужных материалов?"
    elif "обучен" in text or "школ" in text:
        questions["context"] = "На каком этапе обучения возникает проблема и как её решают сейчас?"
        questions["data"] = "Есть ли обезличенные примеры учебных материалов или результатов для работы команды?"
    chosen = [
        {"field": field, "question": question}
        for field, question in questions.items() if field in missing
    ][:5]
    reviews = [
        ("success_criteria", "Как на практике будет проводиться проверка указанных критериев успеха?"),
        ("data", "Как команда сможет проверить доступность указанных материалов перед началом работы?"),
        ("result", "Какие пограничные случаи стоит обсудить перед согласованием результата?"),
    ]
    for field, question in reviews:
        if len(chosen) >= 3:
            break
        chosen.append({"field": field, "question": question})
    return {"missing_fields": missing, "questions": chosen}
