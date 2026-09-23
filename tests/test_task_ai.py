import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from http.client import IncompleteRead
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from task_ai import FIELDS, InputValidationError, analyze_task
from task_ai.schema import ResponseValidationError, validate_analysis
from task_ai.service import MAX_RESPONSE_BYTES

ROOT = Path(__file__).resolve().parents[1]
VALID = {
    "missing_fields": ["data", "result", "success_criteria"],
    "questions": [
        {"field": "data", "question": "Какие данные о заказах доступны команде?"},
        {"field": "result", "question": "Какой результат вы хотите получить от команды?"},
        {"field": "success_criteria", "question": "Каким способом вы проверите сокращение ожидания?"},
    ],
}


def envelope(analysis=None):
    return {
        "status": "completed",
        "output": [{
            "type": "message",
            "content": [{"type": "output_text", "text": json.dumps(analysis or VALID)}],
        }],
    }


class TaskAITest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def fake_api(self, value):
        os.environ["OPENAI_API_KEY"] = "test-only-not-a-real-key"
        return patch("task_ai.service.urlopen", return_value=io.BytesIO(json.dumps(value).encode()))

    def test_offline_never_uses_network_and_preserves_user_fields(self):
        fields = {"need": "  Сократить ожидание  ", "confirmed": True}
        before = copy.deepcopy(fields)
        with patch("task_ai.service.urlopen") as request:
            result = analyze_task("Кафе", fields, offline=True)
        request.assert_not_called()
        self.assertEqual(fields, before)
        self.assertEqual(result["card"]["need"], fields["need"])
        self.assertFalse(result["card"]["confirmed"])
        self.assertTrue(result["requires_confirmation"])
        self.assertEqual(result["card"]["data"], "")
        self.assertEqual(result["fallback_reason"], "offline_requested")

    def test_missing_key_has_explicit_fallback(self):
        result = analyze_task("Задача магазина")
        self.assertEqual(result["mode"], "fallback")
        self.assertEqual(result["fallback_reason"], "missing_api_key")
        self.assertGreaterEqual(len(result["questions"]), 3)

    def test_all_fields_present_still_get_three_review_questions(self):
        result = analyze_task("", {f: "Сообщено пользователем" for f in FIELDS}, offline=True)
        self.assertEqual(result["missing_fields"], [])
        self.assertEqual(len(result["questions"]), 3)

    def test_one_missing_field_does_not_create_extra_missing_fields(self):
        card = {f: "Сообщено пользователем" for f in FIELDS}
        card["data"] = ""
        result = analyze_task("", card, offline=True)
        self.assertEqual(result["missing_fields"], ["data"])
        self.assertEqual(len(result["questions"]), 3)

    def test_fallback_is_relevant_to_cafe(self):
        result = analyze_task("Нужна помощь кафе", offline=True)
        question = next(q["question"] for q in result["questions"] if q["field"] == "data")
        self.assertIn("заказов", question)

    def test_bad_caller_input_is_rejected_before_network(self):
        cases = [
            ("", {}), ("   ", {}), (None, {}), ("x" * 12001, {}),
            ("Задача", []), ("Задача", {"users": None}), ("Задача", {"score": 100}),
            ("Задача", {"users": "x" * 4001}), ("Задача", {"confirmed": "yes"}),
            ("x" * 12000, {f: "x" * 4000 for f in FIELDS}),
        ]
        with patch("task_ai.service.urlopen") as request:
            for description, fields in cases:
                with self.subTest(description_type=type(description), fields_type=type(fields)):
                    with self.assertRaises(InputValidationError):
                        analyze_task(description, fields)
            request.assert_not_called()

    def test_openai_request_and_public_output_contract(self):
        with self.fake_api(envelope()) as request:
            result = analyze_task("Очереди в кафе", {"title": "Кафе"})
        self.assertEqual(result["mode"], "openai")
        self.assertIsNone(result["fallback_reason"])
        self.assertEqual(result["questions"], VALID["questions"])
        self.assertEqual(result["card"]["result"], "")
        self.assertEqual(result["missing_fields"], VALID["missing_fields"])
        req = request.call_args.args[0]
        payload = json.loads(req.data)
        self.assertEqual(req.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(req.get_method(), "POST")
        self.assertFalse(payload["store"])
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertEqual(json.loads(payload["input"])["description"], "Очереди в кафе")
        self.assertEqual(request.call_args.kwargs["timeout"], 15)
        self.assertEqual(request.call_count, 1)
        self.assertNotIn("test-only", json.dumps(result))

    def test_nonempty_but_vague_fields_can_be_flagged_by_ai(self):
        with self.fake_api(envelope()):
            result = analyze_task("Кафе", {"result": "что-нибудь полезное"})
        self.assertIn("result", result["missing_fields"])
        self.assertEqual(result["card"]["result"], "что-нибудь полезное")

    def test_provider_failures_are_sanitized(self):
        cases = [
            (TimeoutError("private details"), "timeout"),
            (URLError(TimeoutError()), "timeout"),
            (URLError("private details"), "network_error"),
            (OSError("private details"), "network_error"),
            (IncompleteRead(b"partial"), "network_error"),
            (HTTPError("url", 401, "private details", {}, None), "authentication_error"),
            (HTTPError("url", 403, "private details", {}, None), "access_denied"),
            (HTTPError("url", 429, "private details", {}, None), "rate_limit"),
            (HTTPError("url", 500, "private details", {}, None), "api_error"),
        ]
        os.environ["OPENAI_API_KEY"] = "test-only-not-a-real-key"
        for error, reason in cases:
            with self.subTest(reason=reason):
                with patch("task_ai.service.urlopen", side_effect=error):
                    result = analyze_task("Кафе")
                self.assertEqual(result["fallback_reason"], reason)
                self.assertNotIn("private details", json.dumps(result))
                self.assertGreaterEqual(len(result["questions"]), 3)

    def test_malformed_or_truncated_responses_fall_back(self):
        bodies = [
            b"not json", b"\xff", b"[]", b"{}", b"x" * (MAX_RESPONSE_BYTES + 1),
            json.dumps(envelope({"missing_fields": [], "questions": []})).encode(),
            json.dumps({"status": "completed", "output": [None]}).encode(),
            json.dumps({"status": "completed", "output": [{"type": "message", "content": None}]}).encode(),
        ]
        os.environ["OPENAI_API_KEY"] = "test-only-not-a-real-key"
        for body in bodies:
            with self.subTest(size=len(body)):
                with patch("task_ai.service.urlopen", return_value=io.BytesIO(body)):
                    result = analyze_task("Кафе")
                self.assertEqual(result["mode"], "fallback")
                self.assertGreaterEqual(len(result["questions"]), 3)

    def test_refusal_and_incomplete_have_distinct_reasons(self):
        refused = {"status": "completed", "output": [
            {"type": "message", "content": [{"type": "refusal", "refusal": "private details"}]}]}
        for value, reason in [(refused, "refusal"), ({"status": "incomplete"}, "incomplete_response")]:
            with self.fake_api(value):
                result = analyze_task("Кафе")
            self.assertEqual(result["fallback_reason"], reason)

    def test_response_validator_rejects_duplicates_and_extra_facts(self):
        bad_values = []
        value = copy.deepcopy(VALID)
        value["questions"][1] = dict(value["questions"][0])
        bad_values.append(value)
        value = copy.deepcopy(VALID)
        value["card"] = {"data": "invented"}
        bad_values.append(value)
        value = copy.deepcopy(VALID)
        value["missing_fields"] = ["data", "data"]
        bad_values.append(value)
        value = copy.deepcopy(VALID)
        value["questions"][0]["field"] = "score"
        bad_values.append(value)
        value = copy.deepcopy(VALID)
        value["questions"][0]["question"] = ""
        bad_values.append(value)
        for value in bad_values:
            with self.assertRaises(ResponseValidationError):
                validate_analysis(value)

    def test_invalid_config_does_not_call_api(self):
        os.environ["OPENAI_API_KEY"] = "test-only"
        for timeout in ["nan", "inf", "0", "-1", "61", "bad"]:
            with patch.dict(os.environ, {"OPENAI_TIMEOUT_SECONDS": timeout}):
                with patch("task_ai.service.urlopen") as request:
                    result = analyze_task("Кафе")
                self.assertEqual(result["fallback_reason"], "invalid_configuration")
                request.assert_not_called()

    def test_model_and_timeout_can_be_configured(self):
        with self.fake_api(envelope()) as request:
            with patch.dict(os.environ, {"OPENAI_MODEL": "configured-model", "OPENAI_TIMEOUT_SECONDS": "5"}):
                analyze_task("Кафе")
        self.assertEqual(json.loads(request.call_args.args[0].data)["model"], "configured-model")
        self.assertEqual(request.call_args.kwargs["timeout"], 5)

    def test_cli_offline(self):
        result = subprocess.run(
            [sys.executable, "-m", "task_ai", "examples/ai_input.json", "--offline"],
            cwd=ROOT, capture_output=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["mode"], "fallback")

    def test_cli_invalid_json_exits_with_error(self):
        result = subprocess.run(
            [sys.executable, "-m", "task_ai", "README.md", "--offline"],
            cwd=ROOT, capture_output=True, encoding="utf-8", check=False,
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
