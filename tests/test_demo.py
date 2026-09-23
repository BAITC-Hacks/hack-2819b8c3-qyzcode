import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import database as db
from seed_demo import seed, demo_data


class DemoTest(unittest.TestCase):
    def test_five_samples_idempotent_and_preserve_existing(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(db, "DB_PATH", Path(directory) / "demo.db"):
                db.init_db()
                original = db.save_task({"title": "Моя задача"})
                self.assertEqual(seed(), 5)
                self.assertEqual(seed(), 0)
                self.assertEqual(len(db.get_tasks()), 6)
                self.assertEqual(db.get_task(original)["title"], "Моя задача")
                self.assertEqual(len(db.get_teams()), 5)
                self.assertEqual(sum(len(db.get_proposals(t["id"])) for t in db.get_tasks()), 5)
                self.assertEqual([t["score"] for t in demo_data()["cards"]], [20, 40, 70, 90, 100])


if __name__ == "__main__":
    unittest.main()
