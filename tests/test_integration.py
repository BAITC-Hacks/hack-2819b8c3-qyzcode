import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
from backend import calculate_rating, create_task, get_catalog
from integration import normalize_card, clarify, apply_answers


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_patch = patch.object(db, "DB_PATH", Path(self.temp.name) / "test.db")
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        db.init_db()

    def card(self):
        return {**create_task(), "title": "Магазин", "topic": "Торговля",
                "context": "Списываем продукты", "need": "Сократить списания", "confirmed": True}

    def test_full_journey_and_multiple_teams(self):
        task = self.card()
        analysis = clarify({**task, "description": "Проблема магазина", "id": 12}, offline=True)
        self.assertGreaterEqual(len(analysis["questions"]), 3)
        self.assertFalse(analysis["card"]["confirmed"])
        task_id = db.save_task(task)
        self.assertEqual(get_catalog(), [])
        db.publish_task(task_id)
        self.assertEqual(get_catalog()[0]["score"], 20)
        task["users"] = "Менеджер магазина"
        db.update_task(task_id, task)
        self.assertEqual(len(db.get_tasks()), 1)
        self.assertEqual(get_catalog()[0]["score"], 30)
        ids = []
        for name in ["Alpha", "Beta"]:
            team = db.save_team(name)
            ids.append(db.submit_proposal(task_id, team, "Идея", "План", "Неделя", "https://example.com"))
        self.assertEqual([p["status"] for p in db.get_proposals(task_id)], ["pending", "pending"])
        for pid in ids:
            db.decide_proposal(pid, "selected")
        self.assertTrue(all(p["status"] == "selected" for p in db.get_proposals(task_id)))
        self.assertEqual(sum(t["points"] for t in db.get_teams()), 0)
        db.confirm_milestone(ids[0], "Проверен прототип на примерах")
        with self.assertRaises(ValueError):
            db.confirm_milestone(ids[0], "Повтор")
        self.assertEqual(sum(t["points"] for t in db.get_teams()), 10)

    def test_unconfirmed_cannot_publish_or_earn(self):
        task = {**self.card(), "confirmed": False}
        self.assertEqual(calculate_rating(task)["score"], 0)
        tid = db.save_task(task)
        with self.assertRaises(ValueError):
            db.publish_task(tid)
        team = db.save_team("Team")
        with self.assertRaises(ValueError):
            db.submit_proposal(tid, team, "x", "y", "z", "https://example.com")

    def test_edit_draft_removes_publication_without_losing_record(self):
        task = self.card()
        tid = db.save_task(task)
        db.publish_task(tid)
        db.update_task(tid, {**task, "confirmed": False})
        self.assertEqual(get_catalog(), [])
        self.assertEqual(len(db.get_tasks()), 1)

    def test_legacy_topic_filters_and_sorting(self):
        weak = self.card()
        weak.pop("topic")
        weak["industry"] = "Торговля"
        strong = {**self.card(), "data": "CSV", "users": "Кассир"}
        for task in [weak, strong]:
            db.publish_task(db.save_task(task))
        self.assertEqual([t["score"] for t in get_catalog(topic="торговля")], [50, 20])
        self.assertEqual(len(get_catalog(level="Черновик")), 1)
        self.assertEqual(get_catalog(topic="Медицина"), [])

    def test_answers_preserve_facts_and_invalidate_confirmation(self):
        original = {**self.card(), "data": "CSV продаж", "industry": "Торговля"}
        updated = apply_answers(original, [{"field": "data"}], ["Доступ после согласования"])
        self.assertEqual(updated["data"], "CSV продаж\nДоступ после согласования")
        self.assertFalse(updated["confirmed"])
        self.assertEqual(original["data"], "CSV продаж")
        self.assertEqual(normalize_card({"success": "10 тестов"})["success_criteria"], "10 тестов")

    def test_proposal_validation_and_no_automatic_award(self):
        tid = db.save_task(self.card())
        db.publish_task(tid)
        team = db.save_team("Team")
        for link in ["javascript:alert(1)", "https://", "not a url"]:
            with self.assertRaises(ValueError):
                db.submit_proposal(tid, team, "Идея", "План", "Срок", link)
        pid = db.submit_proposal(tid, team, "Идея", "План", "Срок", "https://example.com")
        with self.assertRaises(ValueError):
            db.confirm_milestone(pid, "Результат")
        db.decide_proposal(pid, "rejected")
        self.assertEqual(db.get_proposals(tid)[0]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
