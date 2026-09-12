# Bug Reporter

Мини-трекер багов на **Flask + SQLite** с Jira-подобным интерфейсом.
Инструмент для ведения портфолио-багов из `../../bug-reports/`.

## Возможности

- Список багов со статистикой: total / open / in progress / resolved / critical
- Карточка бага: severity, priority, статус, URL, вложения, скриншоты
- Полный отчёт из формы хранится в БД: тип, компонент, окружение, предусловия, шаги воспроизведения, ожидаемый/фактический результат, влияние на пользователя, причина, рекомендации, метки
- Комментарии к багу, навигация prev/next
- Создание и редактирование, смена статуса в один клик
- Экспорт карточки бага
- Импорт существующих багов из `../../bug-reports/*.md` (`import_bugs.py`): новые ключи вставляются, существующие обновляются из markdown — шаги и результаты подтягиваются из репортов
- Telegram-уведомления о багах (`telegram_notifier.py`)

## Структура

```
tools/bug-reporter/
├── app.py                    # Flask-приложение, маршруты, схема БД
├── import_bugs.py            # Импорт багов из markdown-репортов
├── telegram_notifier.py      # Отправка карточек багов в Telegram
├── add_screenshots_column.py
├── update_screenshots.py
├── write_css.py
├── requirements.txt
├── bug_reports.db            # SQLite (не коммитится, см. .gitignore)
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── bug_detail.html
│   ├── bug_detail_nav.html
│   ├── new_bug.html
│   └── edit_bug.html
└── static/
    └── *.css                 # Jira-подобные стили
```

Скриншоты приложение берёт из корневой папки `../../screenshots/`
через маршрут `/screenshots/<filename>` — отдельной копии в `static/` не нужно.

## Установка и запуск

```powershell
cd tools/bug-reporter
py -m pip install -r requirements.txt
py app.py
# → http://127.0.0.1:5000
```

База данных `bug_reports.db` создаётся автоматически при первом запуске
(`init_db()` в `app.py`).

## Импорт существующих багов

```powershell
py import_bugs.py
```

Скрипт читает `../../bug-reports/BUG-*.md` и заполняет таблицу `bugs`.

## Telegram-уведомления

`telegram_notifier.py` отправляет карточку бага в Telegram через Bot API
(формат MarkdownV2, значки критичности, ссылка на карточку).

Конфигурация — только переменные окружения, секреты в код не попадают:

| Переменная | Обязательна | Назначение |
|------------|-------------|------------|
| `TELEGRAM_BOT_TOKEN` | да | токен от [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_CHAT_ID` | да | id чата: напиши боту, затем `getUpdates` |
| `TELEGRAM_API_IP` | нет | IP для обхода блокировки api.telegram.org на уровне DNS; соединение идёт на него, но с настоящими Host и SNI — сертификат проверяется штатно |

```powershell
# тестовая отправка
$env:TELEGRAM_BOT_TOKEN = "123:abc..."   # токен от @BotFather
$env:TELEGRAM_CHAT_ID   = "123456789"    # свой id: напиши боту, затем getUpdates
py telegram_notifier.py --test

# отправить баг №1 из базы трекера
py telegram_notifier.py --bug-id 1
```

Без заданных переменных окружения `send_bug_notification()` возвращает
`(False, ...)` и не бросает исключений — вызов из веб-приложения не ломается.

Тесты (`../../tests/test_telegram_notifier.py`, 16 шт.) полностью замоканы:
не ходят в сеть, не требуют токена, проверяют форматирование MarkdownV2,
экранирование спецсимволов, обработку ошибок API и чтение из БД.

## Маршруты

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/` | Список багов + статистика |
| GET | `/bug/<id>` | Карточка бага, комментарии |
| GET | `/new` | Форма создания бага |
| POST | `/new` | Сохранение нового бага |
| GET | `/edit/<id>` | Форма редактирования |
| POST | `/edit/<id>` | Сохранение изменений |
| POST | `/change-status/<id>` | Смена статуса |
| GET | `/change-status-get/<id>/<status>` | Смена статуса ссылкой |
| POST | `/delete/<id>` | Удаление бага |
| POST | `/comment/<id>` | Добавить комментарий |
| POST | `/delete-comment/<cid>` | Удалить комментарий |
| GET | `/export/<id>` | Экспорт карточки бага |
| GET | `/screenshots/<filename>` | Отдать файл из `../../screenshots/` |
