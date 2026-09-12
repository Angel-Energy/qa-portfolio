# BUG-008 — Автоматизированные тесты

Двухуровневая автоматизация бага BUG-008 (в правом сайдбаре публичного блога
GetCourse отображаются ссылки на снятые/скрытые статьи — при клике редирект
на общий листинг блога).

Покрывает все **5 подтверждённых битых ссылок**.

## Структура

```
tests/
├── test_bug008_route_check.py   # Layer 1: HTTP/route-check (requests)
├── test_bug008_e2e.py           # Layer 2: UI E2E (Playwright)
└── README.md
```

## Битые ссылки (5 шт.)

| URL | Название | Раздел сайдбара |
|-----|----------|-----------------|
| `/blog/886415` | Интеграция с сервисом SMS-рассылок SevenTech | Интеграция → SMS |
| `/blog/1037908` | Каталог дополнений GetCourse | Дополнения |
| `/blog/275858` | Как сделать фон формы прозрачным | CMS → Форма |
| `/blog/275854` | Как изменить высоту виджета | CMS → Виджет |
| `/blog/298451` | Как преодолеть потолок | Как заработать на GetCourse |

## Layer 1 — HTTP/Route-check (`test_bug008_route_check.py`)

Проверяет серверный редирект на уровне HTTP-запроса (без браузера).
Параметризован: каждая проверка выполняется для всех 5 ссылок.

| Тест | Что проверяет | Кол-во |
|------|---------------|--------|
| `test_broken_link_returns_301` | URL отдаёт 301 вместо 200 | 5 |
| `test_broken_link_redirects_to_pl_blog` | Редирект ведёт на `/pl/blog` | 5 |
| `test_redirect_is_permanent_301_not_temporary_302` | Это 301 (постоянный), а не 302 | 5 |
| `test_menublog_page_is_accessible` | `/menublog` доступен | 1 |
| `test_menublog_contains_js_preloader` | На `/menublog` есть preloader | 1 |

```powershell
py -m pytest tests/test_bug008_route_check.py -v
```

**Результат: 17 passed** — все 5 ссылок подтверждены как битые.

## Layer 2 — UI E2E (`test_bug008_e2e.py`)

Полный путь пользователя через браузер (Playwright + Chromium).
Фокус: **гости** (инкогнито) — основная аудитория публичного блога.
Параметризован: каждая проверка выполняется для всех 5 ссылок.

| Тест | Что проверяет | Результат |
|------|---------------|-----------|
| `test_guest_direct_visit_to_broken_article` | Прямой URL → редирект | ❌ 5 FAILED (баг) |
| `test_guest_sidebar_link_exists` | Ссылка есть в sidebar | ✅ 5 PASSED |
| `test_guest_sidebar_link_opens_new_tab` | `target="_blank"` работает | ✅ 5 PASSED |
| `test_guest_sidebar_link_leads_to_redirect` | Клик → редирект | ❌ 5 FAILED (баг) |

```powershell
py -m pytest tests/test_bug008_e2e.py -v --browser chromium
```

### Почему тесты «падают»

Тесты `test_guest_direct_visit_to_broken_article` и `test_guest_sidebar_link_leads_to_redirect`
**ожидаемо падают** — они подтверждают баг: вместо статьи открывается `/pl/blog`.

Когда разработчики уберут устаревшие ссылки из источника данных sidebar
(или восстановят статьи), эти тесты начнут проходить — это будет сигналом,
что баг исправлен.

## Полный запуск

```powershell
py -m pytest tests/ -v --browser chromium
```

**Результат: 10 failed, 27 passed** — все 10 failed ожидаемо подтверждают баг.

## Зависимости

```powershell
py -m pip install pytest requests playwright pytest-playwright
py -m playwright install chromium
```
