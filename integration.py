"""Adapter between the task_ai contract and persisted business cards."""
from task_ai import FIELDS, analyze_task


def normalize_card(task):
    card = dict(task)
    card["topic"] = card.get("topic") or card.get("industry") or "Другое"
    card["success_criteria"] = card.get("success_criteria") or card.get("success") or ""
    for field in FIELDS:
        card.setdefault(field, "")
    card.setdefault("description", "")
    return card


def clarify(card, *, offline=False):
    card = normalize_card(card)
    # AI rejects persistence metadata and topic; only pass its documented fields.
    return analyze_task(
        card["description"],
        {field: card[field] for field in FIELDS},
        offline=offline,
    )


def apply_answers(card, questions, answers):
    """Append only user-authored answers, without erasing existing information."""
    result = normalize_card(card)
    for question, answer in zip(questions, answers):
        field = question["field"]
        if field not in FIELDS or not isinstance(answer, str):
            raise ValueError("Неверный формат ответа.")
        answer = answer.strip()
        if answer:
            existing = result[field].strip()
            result[field] = existing + "\n" + answer if existing else answer
            if len(result[field]) > 4000:
                raise ValueError("Ответ слишком длинный: в поле допускается 4000 символов.")
    result["confirmed"] = False
    return result
