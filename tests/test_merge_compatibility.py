"""Both branch schemas and both public APIs must survive the merge."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
from backend import calculate_rating
from seed_demo import seed


class BranchCompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "legacy.db"
        self.override = patch.object(db, "DB_PATH", self.path)
        self.override.start()
        self.addCleanup(self.override.stop)

    def legacy(self, kind):
        c = sqlite3.connect(self.path)
        try:
            c.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft')")
            c.execute("INSERT INTO tasks VALUES (7, ?, 'published')", (json.dumps({
                "title": "Старая задача", "need": "Потребность", "context": "Контекст", "confirmed": True}),))
            c.execute("CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, interests TEXT NOT NULL, skills TEXT NOT NULL, technologies TEXT NOT NULL)")
            c.execute("INSERT INTO teams VALUES (3, 'QyzCode', 'Торговля', 'Python', 'Streamlit')")
            if kind == "backend":
                c.execute("""CREATE TABLE proposals (id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL,
                    team_name TEXT NOT NULL, idea TEXT NOT NULL, plan TEXT NOT NULL, deadline TEXT NOT NULL,
                    prototype_url TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending')""")
                c.execute("INSERT INTO proposals VALUES (9, 7, 'QyzCode', 'Идея', 'План', 'Неделя', 'https://example.com', 'accepted')")
                c.execute("""CREATE TABLE completed_stages (proposal_id INTEGER PRIMARY KEY REFERENCES proposals(id),
                    team_id INTEGER NOT NULL REFERENCES teams(id), description TEXT NOT NULL, points INTEGER NOT NULL)""")
                c.execute("INSERT INTO completed_stages VALUES (9, 3, 'Готов прототип', 10)")
            else:
                c.execute("""CREATE TABLE proposals (id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL,
                    team_id INTEGER NOT NULL, idea TEXT NOT NULL, plan TEXT NOT NULL, deadline TEXT NOT NULL,
                    link TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', milestone TEXT NOT NULL DEFAULT '',
                    progress_points INTEGER NOT NULL DEFAULT 0)""")
                c.execute("INSERT INTO proposals VALUES (9, 7, 3, 'Идея', 'План', 'Неделя', 'https://example.com', 'selected', 'Готов прототип', 10)")
            c.commit()
        finally:
            c.close()

    def check_migration(self, kind):
        self.legacy(kind)
        db.init_db()
        db.init_db()
        proposal = db.get_proposals(7)[0]
        self.assertEqual(proposal["id"], 9)
        self.assertEqual(proposal["status"], "accepted")
        self.assertEqual(proposal["team_name"], "QyzCode")
        self.assertEqual(proposal["link"], proposal["prototype_url"])
        self.assertEqual(proposal["milestone"], "Готов прототип")
        self.assertEqual(proposal["progress_points"], 10)
        self.assertEqual(db.get_teams()[0]["points"], 10)
        with self.assertRaises(ValueError):
            db.confirm_stage(9, "Повтор")
        with self.assertRaises(ValueError):
            db.confirm_milestone(9, "Повтор через интерфейс")
        pid = db.create_proposal(7, "QyzCode", "Вторая идея", "План", "Неделя", "https://example.com/two")
        db.set_proposal_status(pid, "accepted")
        self.assertEqual(db.confirm_stage(pid, "Проверено бизнесом"), 10)
        self.assertEqual(db.get_teams()[0]["points"], 20)
        with db.connect() as c:
            self.assertEqual(c.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(seed(), 5)
        self.assertEqual(seed(), 0)
        self.assertEqual(len(db.get_tasks()), 6)
        self.assertEqual(len(db.get_proposals(7)), 2)
        self.assertEqual(db.get_teams()[0]["points"], 20)

    def test_backend_database_keeps_proposals_and_stages(self):
        self.check_migration("backend")

    def test_frontend_database_keeps_proposals_and_stages(self):
        self.check_migration("frontend")

    def test_partial_update_invalidates_confirmation_and_keeps_other_fields(self):
        db.init_db()
        tid = db.save_task({"title": "Задача", "need": "Потребность", "context": "Контекст",
                            "data": "CSV", "confirmed": True})
        db.publish_task(tid)
        db.update_task(tid, {"users": "Менеджер"})
        task = db.get_task(tid)
        self.assertEqual(task["data"], "CSV")
        self.assertFalse(task["confirmed"])
        self.assertEqual(task["status"], "draft")
        self.assertEqual(calculate_rating(task)["score"], 0)
        with self.assertRaises(ValueError):
            db.update_task(tid, {"confirmed": True})
        db.confirm_task(tid)
        self.assertEqual(calculate_rating(db.get_task(tid))["score"], 50)
        db.publish_task(tid)
        self.assertEqual(len(db.get_published_tasks()), 1)

    def test_backend_team_profiles_are_idempotent(self):
        db.init_teams()
        db.init_teams()
        self.assertEqual(len(db.get_teams()), 5)
        self.assertTrue(all(t["points"] == 0 for t in db.get_teams()))


if __name__ == "__main__":
    unittest.main()
