"""Public JSON contract and strict validation, using only the standard library."""

FIELDS = (
    "title", "context", "need", "users", "data", "constraints",
    "result", "success_criteria", "contact", "interaction",
)


class InputValidationError(ValueError):
    """Bad caller input; the backend should return HTTP 400/422."""


class ResponseValidationError(ValueError):
    """Unusable AI response; the service falls back to local questions."""


def validate_input(description, fields):
    if not isinstance(description, str) or len(description) > 12000:
        raise InputValidationError("description must be a string of at most 12000 characters")
    if fields is None:
        fields = {}
    if not isinstance(fields, dict):
        raise InputValidationError("fields must be an object")
    if set(fields) - set(FIELDS) - {"confirmed"}:
        raise InputValidationError("fields contains unsupported keys")
    if "confirmed" in fields and not isinstance(fields["confirmed"], bool):
        raise InputValidationError("confirmed must be a boolean")
    card = {}
    for field in FIELDS:
        value = fields.get(field, "")
        if not isinstance(value, str) or len(value) > 4000:
            raise InputValidationError(f"{field} must be a string of at most 4000 characters")
        card[field] = value
    if not description.strip() and not any(value.strip() for value in card.values()):
        raise InputValidationError("Provide a description or at least one non-empty field")
    if len(description) + sum(map(len, card.values())) > 50000:
        raise InputValidationError("Combined input exceeds 50000 characters")
    card["confirmed"] = False
    return card


def validate_analysis(value):
    if not isinstance(value, dict) or set(value) != {"missing_fields", "questions"}:
        raise ResponseValidationError("Invalid analysis object")
    missing = value["missing_fields"]
    if (not isinstance(missing, list)
            or any(not isinstance(f, str) or f not in FIELDS for f in missing)
            or len(set(missing)) != len(missing)):
        raise ResponseValidationError("Invalid missing_fields")
    questions = value["questions"]
    if not isinstance(questions, list) or not 3 <= len(questions) <= 6:
        raise ResponseValidationError("Expected 3 to 6 questions")
    normalized = []
    for item in questions:
        if not isinstance(item, dict) or set(item) != {"field", "question"}:
            raise ResponseValidationError("Invalid question object")
        if not isinstance(item["field"], str) or item["field"] not in FIELDS:
            raise ResponseValidationError("Invalid question field")
        question = item["question"]
        if not isinstance(question, str) or not 10 <= len(question.strip()) <= 600:
            raise ResponseValidationError("Invalid question text")
        normalized.append({"field": item["field"], "question": question.strip()})
    if len({item["question"].casefold() for item in normalized}) != len(normalized):
        raise ResponseValidationError("Duplicate questions")
    return {"missing_fields": missing, "questions": normalized}


ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "missing_fields": {"type": "array", "items": {"type": "string", "enum": list(FIELDS)}},
        "questions": {
            "type": "array", "minItems": 3, "maxItems": 6,
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "field": {"type": "string", "enum": list(FIELDS)},
                    "question": {"type": "string"},
                },
                "required": ["field", "question"],
            },
        },
    },
    "required": ["missing_fields", "questions"],
}
