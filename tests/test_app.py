import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database as db
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppJourneyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        p = patch.object(db, "DB_PATH", Path(self.temp.name) / "ui.db")
        p.start()
        self.addCleanup(p.stop)
        env = patch.dict(os.environ, {"OPENAI_API_KEY": ""})
        env.start()
        self.addCleanup(env.stop)
        self.app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
        self.assertFalse(self.app.exception)

    def element(self, kind, label):
        return next(e for e in getattr(self.app, kind) if e.label == label)

    def click(self, label):
        self.element("button", label).click().run()
        self.assertFalse(self.app.exception)

    def test_ui_journey(self):
        self.element("text_area", "Исходное описание проблемы").set_value("В магазине много списаний")
        self.click("Уточнить с ИИ")
        questions = self.app.session_state["analysis"]["questions"]
        self.assertGreaterEqual(len(questions), 3)
        for question in questions:
            self.element("text_area", question["question"]).set_value("Ответ пользователя")
        self.click("Перенести ответы в карточку")
        self.element("text_input", "Название задачи").set_value("Списания магазина")
        self.element("checkbox", "Подтверждаю достоверность заполненных сведений").check()
        self.click("Подтвердить и сохранить карточку")
        tid = self.app.session_state["task_id"]
        self.assertTrue(db.get_task(tid)["confirmed"])
        self.click("Опубликовать сохранённую карточку")
        self.app.radio(key="page").set_value("Каталог задач").run()
        self.app.radio(key="role").set_value("Команда").run()
        self.element("text_input", "Название команды").set_value("UI Team")
        self.click("Добавить команду")
        self.element("text_area", "Идея решения").set_value("Прогноз спроса")
        self.element("text_area", "План работы").set_value("Анализ и прототип")
        self.element("text_input", "Срок выполнения").set_value("Неделя")
        self.element("text_input", "Ссылка на прототип").set_value("https://example.com")
        self.click("Отправить предложение")
        self.app.radio(key="role").set_value("Бизнес").run()
        self.app.radio(key="page").set_value("Кабинет бизнеса").run()
        self.click("Выбрать")
        self.element("text_area", "Какой результат этапа вы проверили?").set_value("Проверен прототип")
        self.element("checkbox", "Подтверждаю, что результат получен и проверен").check()
        self.click("Подтвердить этап: +10 баллов")
        self.assertEqual(db.get_teams()[0]["points"], 10)
        self.click("Редактировать")
        self.assertEqual(self.app.radio(key="page").value, "Создать задачу")
        self.element("text_area", "Пользователи").set_value("Менеджер")
        self.element("checkbox", "Подтверждаю достоверность заполненных сведений").check()
        self.click("Подтвердить и сохранить карточку")
        self.assertEqual(len(db.get_tasks()), 1)
        self.assertEqual(db.get_task(tid)["users"], "Менеджер")

    def test_empty_input_and_unconfirmed_card(self):
        self.click("Уточнить с ИИ")
        self.assertTrue(self.app.warning)
        self.element("text_input", "Название задачи").set_value("Тест")
        self.element("text_area", "Потребность — что нужно изменить?").set_value("Потребность")
        self.click("Подтвердить и сохранить карточку")
        self.assertEqual(db.get_tasks(), [])
        self.click("Сохранить черновик")
        self.assertFalse(db.get_tasks()[0]["confirmed"])
        self.assertFalse(any(b.label == "Опубликовать сохранённую карточку" for b in self.app.button))


if __name__ == "__main__":
    unittest.main()
