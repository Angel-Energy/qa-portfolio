"""Тесты telegram_notifier: форматирование, конфиг, отправка.

Все сетевые вызовы замоканы — тесты не ходят в сеть, не требуют
токена и ничего не отправляют. Реальная отправка проверяется вручную:
    python tools/bug-reporter/telegram_notifier.py --test
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "tools" / "bug-reporter" / "telegram_notifier.py"
)
spec = importlib.util.spec_from_file_location("telegram_notifier", MODULE_PATH)
tn = importlib.util.module_from_spec(spec)
sys.modules["telegram_notifier"] = tn
spec.loader.exec_module(tn)


BUG = {
    "key": "BUG-009",
    "project": "Яндекс Лавка (Android)",
    "severity": "Blocker",
    "priority": "Highest",
    "status": "New",
    "title": "Кнопка «Оплатить» не реагирует при выборе СБП",
    "url": "https://example.com/bug/009",
    "environment": "POCO F5 Pro / Android 15",
}


def _env_without_telegram(**extra):
    """Чистое окружение без TELEGRAM_* + явные значения поверх."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM_")}
    env.update(extra)
    return env


# ─── Форматирование ───────────────────────────────────────────────


def test_message_contains_all_fields():
    msg = tn.format_bug_message(BUG)
    # значения полей экранируются по правилам MarkdownV2
    assert r"BUG\-009" in msg
    assert r"Яндекс Лавка \(Android\)" in msg
    assert "Blocker" in msg
    assert "Кнопка «Оплатить»" in msg
    assert "https://example.com/bug/009" in msg  # URL не экранируется
    assert "POCO F5 Pro / Android 15" in msg


def test_blocker_gets_blocker_icon():
    assert "⛔" in tn.format_bug_message(BUG)


def test_unknown_severity_gets_default_icon():
    msg = tn.format_bug_message({**BUG, "severity": "Whatever"})
    assert "🟠" in msg


def test_missing_fields_are_omitted():
    msg = tn.format_bug_message({"key": "BUG-010", "title": "Тест"})
    assert "Продукт" not in msg
    assert "Приоритет" not in msg
    assert "Статус" not in msg
    assert r"BUG\-010" in msg
    assert "Тест" in msg


def test_markdownv2_special_chars_escaped_in_values():
    msg = tn.format_bug_message({"key": "BUG-011", "title": "Ошибка (a.b) 100% [fail]"})
    assert r"\(a\.b\)" in msg
    assert r"\[fail\]" in msg
    assert "*Суть дефекта:*" in msg


def test_url_becomes_inline_link_with_escaped_parens():
    msg = tn.format_bug_message({"key": "BUG-012", "title": "x", "url": "https://ya.ru/search?q=(1)"})
    # внутри (...) инлайн-ссылки экранируются только ')' и обратный слеш,
    # '(' остаётся как есть — по документации Telegram по MarkdownV2
    assert "[открыть карточку](https://ya.ru/search?q=(1\))" in msg


def test_timestamp_dots_are_escaped():
    import re as _re

    msg = tn.format_bug_message({"key": "BUG-013", "title": "x"})
    assert _re.search(r"\d{2}\\.\d{2}\\.\d{4}", msg), msg


# ─── Конфигурация ─────────────────────────────────────────────────


def test_no_config_returns_false_without_exception():
    with patch.dict(os.environ, _env_without_telegram(), clear=True):
        ok, detail = tn.send_bug_notification(BUG)
    assert ok is False
    assert "TELEGRAM_BOT_TOKEN" in detail


def test_missing_chat_id_returns_false():
    with patch.dict(os.environ, _env_without_telegram(TELEGRAM_BOT_TOKEN="123:abc"), clear=True):
        ok, detail = tn.send_bug_notification(BUG)
    assert ok is False
    assert "TELEGRAM_CHAT_ID" in detail


# ─── Отправка (мок сети) ──────────────────────────────────────────


def test_successful_send_reports_message_id():
    env = _env_without_telegram(TELEGRAM_BOT_TOKEN="123:fake", TELEGRAM_CHAT_ID="1266934071")
    with patch.dict(os.environ, env, clear=True):
        with patch.object(tn, "_post", return_value={"ok": True, "result": {"message_id": 42}}):
            ok, detail = tn.send_bug_notification(BUG)
    assert ok is True
    assert "message_id=42" in detail


def test_payload_contains_chat_id_and_markdownv2():
    captured = {}

    def fake_post(method, payload):
        captured.update(method=method, payload=payload)
        return {"ok": True, "result": {"message_id": 1}}

    env = _env_without_telegram(TELEGRAM_BOT_TOKEN="123:fake", TELEGRAM_CHAT_ID="100200300")
    with patch.dict(os.environ, env, clear=True):
        with patch.object(tn, "_post", side_effect=fake_post):
            tn.send_bug_notification(BUG)

    assert captured["method"] == "sendMessage"
    assert captured["payload"]["chat_id"] == "100200300"
    assert captured["payload"]["parse_mode"] == "MarkdownV2"
    assert r"BUG\-009" in captured["payload"]["text"]


def test_api_error_returns_false_with_description():
    def fake_post(method, payload):
        return {"ok": False, "description": "Bad Request: chat not found"}

    env = _env_without_telegram(TELEGRAM_BOT_TOKEN="123:fake", TELEGRAM_CHAT_ID="1")
    with patch.dict(os.environ, env, clear=True):
        with patch.object(tn, "_post", side_effect=fake_post):
            ok, detail = tn.send_bug_notification(BUG)
    assert ok is False
    assert "chat not found" in detail


def test_network_error_is_swallowed_and_reported():
    def fake_post(method, payload):
        raise tn.TelegramAPIError("сеть недоступна")

    env = _env_without_telegram(TELEGRAM_BOT_TOKEN="123:fake", TELEGRAM_CHAT_ID="1")
    with patch.dict(os.environ, env, clear=True):
        with patch.object(tn, "_post", side_effect=fake_post):
            ok, detail = tn.send_bug_notification(BUG)
    assert ok is False
    assert "сеть недоступна" in detail


# ─── Чтение из БД трекера ─────────────────────────────────────────


def test_load_bug_from_missing_db_returns_none(tmp_path):
    assert tn.load_bug_from_db(1, db_path=str(tmp_path / "nope.db")) is None


def test_load_bug_from_db_returns_dict(tmp_path):
    import sqlite3

    db = tmp_path / "bug_reports.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE bugs (id INTEGER PRIMARY KEY, key TEXT, title TEXT, "
        "project TEXT, severity TEXT, priority TEXT, status TEXT, url TEXT)"
    )
    conn.execute(
        "INSERT INTO bugs (key, title, project, severity, priority, status, url) "
        "VALUES ('BUG-001', 'Тестовый баг', 'Лавка', 'Blocker', 'Highest', 'New', '')"
    )
    conn.commit()
    conn.close()

    bug = tn.load_bug_from_db(1, db_path=str(db))
    assert bug is not None
    assert bug["key"] == "BUG-001"
    assert bug["severity"] == "Blocker"


def test_load_bug_from_db_missing_id_returns_none(tmp_path):
    import sqlite3

    db = tmp_path / "bug_reports.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE bugs (id INTEGER PRIMARY KEY, key TEXT)")
    conn.commit()
    conn.close()

    assert tn.load_bug_from_db(999, db_path=str(db)) is None
