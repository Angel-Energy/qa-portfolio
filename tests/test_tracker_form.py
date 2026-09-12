"""Тесты формы баг-репорта: поля формы сохраняются в БД.

app.py импортируется по пути (как в test_telegram_notifier.py).
БД подменяется на временную, Telegram-переменные окружения
удаляются — уведомление не пытается уйти в сеть, а маршрут
/new отрабатывает штатно (send_bug_notification возвращает False).
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

APP_PATH = Path(__file__).resolve().parent.parent / "tools" / "bug-reporter" / "app.py"
spec = importlib.util.spec_from_file_location("tracker_app", APP_PATH)
app_module = importlib.util.module_from_spec(spec)
sys.modules["tracker_app"] = app_module
spec.loader.exec_module(app_module)


FORM_DATA = {
    "title": "Кнопка «Оплатить» не реагирует",
    "project": "Яндекс Лавка",
    "type": "Функциональный",
    "component": "Оплата",
    "severity": "Blocker",
    "priority": "Highest",
    "status": "New",
    "assignee": "Unassigned",
    "reporter": "QA Engineer",
    "environment": "POCO F5 Pro / Android 15",
    "preconditions": "В корзине один товар",
    "steps": "1. Открыть корзину\n2. Нажать «Оплатить»",
    "expected_result": "Открывается экран оплаты",
    "actual_result": "Ничего не происходит",
    "user_impact": "Нельзя оплатить заказ",
    "root_cause": "Не обрабатывается onClick",
    "recommendations": "Проверить обработчик",
    "labels": "mobile, auth",
    "comments": "Воспроизводится стабильно",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "tracker.db"
    monkeypatch.setattr(app_module, "DB_PATH", str(db))
    for var in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_API_IP"):
        monkeypatch.delenv(var, raising=False)
    app_module.init_db()
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c, str(db)


def _fetch(db_path, key):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return dict(conn.execute("SELECT * FROM bugs WHERE key=?", (key,)).fetchone())
    finally:
        conn.close()


def test_form_post_saves_all_fields(client):
    c, db = client
    resp = c.post("/new", data=FORM_DATA)
    assert resp.status_code == 302
    row = _fetch(db, "BUG-001")
    assert row["title"] == FORM_DATA["title"]
    assert row["type"] == "Функциональный"
    assert row["component"] == "Оплата"
    assert row["environment"] == FORM_DATA["environment"]
    assert row["steps"] == FORM_DATA["steps"]
    assert row["expected_result"] == FORM_DATA["expected_result"]
    assert row["actual_result"] == FORM_DATA["actual_result"]
    assert row["user_impact"] == FORM_DATA["user_impact"]
    assert row["labels"] == "mobile, auth"
    assert row["comments"] == "Воспроизводится стабильно"


def test_edit_get_shows_saved_fields(client):
    c, db = client
    c.post("/new", data=FORM_DATA)
    resp = c.get("/edit/1")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Открывается экран оплаты" in html
    assert "1. Открыть корзину" in html


def test_edit_post_updates_fields(client):
    c, db = client
    c.post("/new", data=FORM_DATA)
    updated = dict(FORM_DATA, actual_result="Кнопка зависает на 5 секунд")
    resp = c.post("/edit/1", data=updated)
    assert resp.status_code == 302
    row = _fetch(db, "BUG-001")
    assert row["actual_result"] == "Кнопка зависает на 5 секунд"


def test_minimal_post_creates_bug_with_empty_details(client):
    c, db = client
    resp = c.post("/new", data={"title": "Минимальный баг"})
    assert resp.status_code == 302
    row = _fetch(db, "BUG-001")
    assert row["title"] == "Минимальный баг"
    assert row["steps"] == ""


def test_init_db_migrates_old_schema(tmp_path, monkeypatch):
    """База старой версии (без url/attachments/полей формы) дополняется."""
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE bugs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        project TEXT DEFAULT '',
        severity TEXT DEFAULT 'Major',
        priority TEXT DEFAULT 'Medium',
        status TEXT DEFAULT 'New',
        date TEXT DEFAULT (date('now')),
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime')))""")
    conn.execute("INSERT INTO bugs (key, title) VALUES ('BUG-001', 'Старый баг')")
    conn.commit()
    conn.close()

    monkeypatch.setattr(app_module, "DB_PATH", str(db))
    app_module.init_db()

    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(bugs)").fetchall()}
    conn.close()
    for column in ("url", "attachments", "type", "environment", "steps",
                   "expected_result", "actual_result", "user_impact"):
        assert column in cols, column
    # данные старой записи не потерялись
    conn = sqlite3.connect(db)
    title = conn.execute("SELECT title FROM bugs WHERE key='BUG-001'").fetchone()[0]
    conn.close()
    assert title == "Старый баг"
