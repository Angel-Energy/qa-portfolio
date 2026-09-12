"""
BUG-008 — Layer 1: HTTP/Route-check.

Проверяет серверный редирект на уровне HTTP-запроса (без браузера)
для всех 5 подтверждённых битых ссылок из правого сайдбара публичного блога.

Сервер должен возвращать статью (200), но фактически отдаёт 301 (Moved Permanently)
на общий листинг /pl/blog.
"""

import pytest
import requests

BASE_URL = "https://getcourse.ru"
MENUBLOG_URL = f"{BASE_URL}/menublog"
EXPECTED_FAIL_REDIRECT = f"{BASE_URL}/pl/blog"

# Все 5 подтверждённых битых ссылок из правого сайдбара
BROKEN_LINKS = [
    pytest.param(
        "https://getcourse.ru/blog/886415",
        "Интеграция с сервисом SMS-рассылок SevenTech",
        id="blog-886415-sms-seventech",
    ),
    pytest.param(
        "https://getcourse.ru/blog/1037908",
        "Каталог дополнений GetCourse",
        id="blog-1037908-addon-catalog",
    ),
    pytest.param(
        "https://getcourse.ru/blog/275858",
        "Как сделать фон формы прозрачным",
        id="blog-275858-form-transparent-bg",
    ),
    pytest.param(
        "https://getcourse.ru/blog/275854",
        "Как изменить высоту виджета на стороннем сайте",
        id="blog-275854-widget-height",
    ),
    pytest.param(
        "https://getcourse.ru/blog/298451",
        "Как преодолеть потолок",
        id="blog-298451-overcome-ceiling",
    ),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
}


@pytest.mark.parametrize("url,title", BROKEN_LINKS)
def test_broken_link_returns_301(url, title):
    """
    Баг: URL статьи должен отдавать 200, но сервер возвращает 301.
    Проверяется для всех 5 битых ссылок из сайдбара.
    """
    response = requests.get(url, headers=HEADERS, allow_redirects=False, timeout=10)
    assert response.status_code == 301, (
        f"[{title}] Ожидался 301 (баг), получен {response.status_code}"
    )


@pytest.mark.parametrize("url,title", BROKEN_LINKS)
def test_broken_link_redirects_to_pl_blog(url, title):
    """
    Баг: редирект ведёт на /pl/blog (общий листинг), а не на статью.
    Проверяется для всех 5 битых ссылок.
    """
    response = requests.get(url, headers=HEADERS, allow_redirects=False, timeout=10)
    location = response.headers.get("Location", "")
    assert location == EXPECTED_FAIL_REDIRECT, (
        f"[{title}] Ожидался Location={EXPECTED_FAIL_REDIRECT}, получен {location}"
    )


@pytest.mark.parametrize("url,title", BROKEN_LINKS)
def test_redirect_is_permanent_301_not_temporary_302(url, title):
    """
    Баг: редирект постоянный (301), а не временный (302).
    301 кэшируется браузерами и поисковиками — это усугубляет проблему.
    """
    response = requests.get(url, headers=HEADERS, allow_redirects=False, timeout=10)
    assert response.status_code == 301, (
        f"[{title}] Редирект должен быть 301, получен {response.status_code}"
    )


def test_menublog_page_is_accessible():
    """Предусловие: страница /menublog доступна (200)."""
    response = requests.get(MENUBLOG_URL, headers=HEADERS, timeout=10)
    assert response.status_code == 200, (
        f"Страница /menublog недоступна, статус {response.status_code}"
    )


def test_menublog_contains_js_preloader():
    """Предусловие: на /menublog есть preloader (подтверждение JS-рендеринга)."""
    response = requests.get(MENUBLOG_URL, headers=HEADERS, timeout=10)
    assert "data-preloader-svg" in response.text, (
        "На /menublog не найден preloader — возможно, изменилась структура страницы"
    )