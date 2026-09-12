"""Telegram-уведомления о новых баг-репортах.

Модуль отправляет карточку бага в Telegram через Bot API.

Конфигурация — только через переменные окружения, никаких секретов
в коде и в репозитории:

    TELEGRAM_BOT_TOKEN  токен от @BotFather (обязателен для отправки)
    TELEGRAM_CHAT_ID    куда слать: id чата/канала (обязателен)
    TELEGRAM_API_IP     необязательный IP для обхода блокировки
                        api.telegram.org на уровне DNS; если задан,
                        запросы идут на него, но с настоящим Host и
                        SNI, поэтому сертификат проверяется штатно

Использование из кода:

    from telegram_notifier import send_bug_notification
    ok, detail = send_bug_notification({"key": "BUG-009", ...})

Из командной строки (отправить баг из базы трекера):

    python telegram_notifier.py --bug-id 1
    python telegram_notifier.py --test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sqlite3
import ssl
import sys
from datetime import datetime, timezone

API_HOST = "api.telegram.org"
DEFAULT_TIMEOUT = 20

# Значки критичности: от Blocker к Trivial
SEVERITY_ICONS = {
    "Blocker": "⛔",
    "Critical": "🔥",
    "Major": "🟠",
    "Minor": "🟡",
    "Trivial": "⚪",
}


class TelegramConfigError(RuntimeError):
    """Обязательные переменные окружения не заданы."""


class TelegramAPIError(RuntimeError):
    """Telegram API вернул ошибку или сеть недоступна."""


def _is_ipv4(value: str) -> bool:
    return re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", value) is not None


def _post(method: str, payload: dict) -> dict:
    """POST на Bot API с поддержкой обхода блокировки через TELEGRAM_API_IP.

    При заданном IP соединение создаётся на него, но в TLS передаётся
    настоящий server_hostname и в HTTP — настоящий Host: заголовок
    SNI и валидация сертификата остаются подлинными.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    override = os.environ.get("TELEGRAM_API_IP", "")
    if not token:
        raise TelegramConfigError("TELEGRAM_BOT_TOKEN не задан")

    if override and _is_ipv4(override):
        return _post_via_ip(override, token, method, payload)

    try:
        import requests
    except ImportError as exc:
        raise TelegramAPIError("библиотека requests не установлена") from exc

    url = f"https://{API_HOST}/bot{token}/{method}"
    try:
        resp = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
    except OSError as exc:
        raise TelegramAPIError(
            f"сеть недоступна ({type(exc).__name__}); если api.telegram.org "
            "блокируется провайдером, задай TELEGRAM_API_IP с рабочим IP"
        ) from exc
    return resp.json()


def _post_via_ip(ip: str, token: str, method: str, payload: dict) -> dict:
    """POST raw-сокетом на конкретный IP (Host и SNI — настоящие)."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    chunks: list[bytes] = []
    try:
        with socket.create_connection((ip, 443), timeout=DEFAULT_TIMEOUT) as sock:
            ctx = ssl.create_default_context()
            with ctx.wrap_socket(sock, server_hostname=API_HOST) as tls:
                request = (
                    f"POST /bot{token}/{method} HTTP/1.1\r\n"
                    f"Host: {API_HOST}\r\n"
                    "Content-Type: application/json\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Connection: close\r\n\r\n"
                )
                tls.sendall(request.encode("ascii") + body)
                while True:
                    chunk = tls.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
    except OSError as exc:
        raise TelegramAPIError(f"соединение не удалось: {exc}") from exc

    raw = b"".join(chunks)
    _, _, http_body = raw.partition(b"\r\n\r\n")
    if http_body.startswith(b"HTTP/"):  # редирект или двойной заголовок
        _, _, http_body = http_body.partition(b"\r\n\r\n")
    try:
        return json.loads(http_body.decode("utf-8"))
    except ValueError as exc:
        raise TelegramAPIError(f"нечитаемый ответ API: {http_body[:120]!r}") from exc


def _escape_markdownv2(text: str) -> str:
    """Экранирование спецсимволов MarkdownV2 в значениях полей."""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(text))


def format_bug_message(bug: dict) -> str:
    """Карточка бага в MarkdownV2. Поля, которых нет, не выводятся."""
    esc = _escape_markdownv2
    severity = bug.get("severity") or ""
    icon = SEVERITY_ICONS.get(severity, "🟠")

    lines = [r"🚨 *НОВЫЙ БАГ\-РЕПОРТ ОБНАРУЖЕН\!*", ""]

    header: list[str] = [f"📌 *ID:* {esc(bug.get('key', '—'))}"]
    if bug.get("project"):
        header.append(f"💻 *Продукт:* {esc(bug['project'])}")
    if severity:
        header.append(f"{icon} *Критичность:* {esc(severity)}")
    if bug.get("priority"):
        header.append(f"🎚 *Приоритет:* {esc(bug['priority'])}")
    if bug.get("status"):
        header.append(f"📊 *Статус:* {esc(bug['status'])}")
    lines += header

    lines += ["", f"📝 *Суть дефекта:* {esc(bug.get('title', '—'))}"]

    tail: list[str] = []
    if bug.get("url"):
        # Внутри (...) инлайн-ссылки MarkdownV2 экранируются только
        # ')' и обратный слеш — документированное правило Telegram.
        # chr(92) = обратный слеш; так в исходнике не нужны двойные
        # бэкслеши, которые легко потерять при правках.
        bs = chr(92)
        safe_url = bug["url"].replace(bs, bs + bs).replace(")", bs + ")")
        tail.append(f"🔗 [открыть карточку]({safe_url})")
    if bug.get("environment"):
        tail.append(f"⚙️ *Окружение:* {esc(bug['environment'])}")
    tail.append(f"👤 *Тестировщик:* {esc(bug.get('reporter', 'Мария Игнатова'))}")
    # Локальное время машины с явным смещением, затем UTC: точки и плюс
    # в смещении — зарезервированные символы MarkdownV2, поэтому весь
    # штамп проходит через esc().
    now_local = datetime.now().astimezone()
    offset_minutes = int(now_local.utcoffset().total_seconds() // 60)
    sign = "+" if offset_minutes >= 0 else "-"
    off_h, off_m = divmod(abs(offset_minutes), 60)
    tz_label = f"UTC{sign}{off_h}" + (f":{off_m:02d}" if off_m else "")
    utc_now = datetime.now(timezone.utc)
    stamp = (
        f"{now_local.strftime('%d.%m.%Y %H:%M')} ({tz_label})"
        f" / {utc_now.strftime('%H:%M')} UTC"
    )
    tail.append(f"🕐 {esc(stamp)}")
    lines += ["", *tail]

    return "\n".join(lines)


def send_bug_notification(bug: dict) -> tuple[bool, str]:
    """Отправить карточку бага. Возвращает (успех, описание результата).

    Не бросает исключений: отсутствие конфига — штатная ситуация
    (уведомление просто не отправляется), чтобы вызов из веб-приложения
    не ломал запрос пользователя.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False, (
            "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID не заданы — "
            "уведомление не отправляется (это не ошибка)"
        )

    try:
        result = _post(
            "sendMessage",
            {"chat_id": chat_id, "text": format_bug_message(bug), "parse_mode": "MarkdownV2"},
        )
    except (TelegramConfigError, TelegramAPIError) as exc:
        return False, str(exc)

    if result.get("ok"):
        return True, f"доставлено: message_id={result['result']['message_id']}"
    return False, f"Telegram API: {result.get('description', result)}"


def load_bug_from_db(bug_id: int, db_path: str | None = None) -> dict | None:
    """Прочитать баг из базы трекера.

    db_path по умолчанию — bug_reports.db рядом с модулем; параметр
    нужен для тестов.
    """
    if db_path is None:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bug_reports.db")
    if not os.path.exists(db_path):
        return None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM bugs WHERE id = ?", (bug_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Отправка баг-репорта в Telegram")
    parser.add_argument("--bug-id", type=int, help="id бага в базе трекера")
    parser.add_argument("--test", action="store_true", help="отправить тестовое сообщение")
    args = parser.parse_args()

    if args.test:
        bug = {
            "key": "TEST-001",
            "project": "Проверка интеграции",
            "severity": "Major",
            "priority": "High",
            "title": "Тестовая отправка из telegram_notifier.py",
        }
    elif args.bug_id is not None:
        bug = load_bug_from_db(args.bug_id)
        if bug is None:
            print(f"Баг с id={args.bug_id} не найден в bug_reports.db", file=sys.stderr)
            return 2
    else:
        parser.error("укажи --bug-id N или --test")

    ok, detail = send_bug_notification(bug)
    print(("OK: " if ok else "FAIL: ") + detail)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
