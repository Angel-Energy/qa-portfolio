"""
BUG-008 — UI E2E (Playwright).

Проверяет полный путь пользователя в публичном блоге:
- все 5 битых ссылок присутствуют в правом блоке навигации (sidebar)
- каждая имеет правильный href
- каждая открывается в новой вкладке (target="_blank")
- каждая ведёт на редирект /pl/blog вместо статьи (баг)

Фокус: гости (инкогнито) — основная аудитория публичного блога.
"""

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://getcourse.ru"
START_ARTICLE = f"{BASE_URL}/blog/632059?utm_source=main_blog"
EXPECTED_FAIL_REDIRECT = f"{BASE_URL}/pl/blog"

# Все 5 подтверждённых битых ссылок с разделами сайдбара
BROKEN_LINKS = [
    pytest.param(
        "https://getcourse.ru/blog/886415",
        "Интеграция с сервисом SMS-рассылок SevenTech",
        "SMS",
        id="blog-886415-sms-seventech",
    ),
    pytest.param(
        "https://getcourse.ru/blog/1037908",
        "Каталог дополнений GetCourse",
        "Дополнения",
        id="blog-1037908-addon-catalog",
    ),
    pytest.param(
        "https://getcourse.ru/blog/275858",
        "Как сделать фон формы прозрачным",
        "Форма",
        id="blog-275858-form-transparent-bg",
    ),
    pytest.param(
        "https://getcourse.ru/blog/275854",
        "Как изменить высоту виджета, который я вставил на сторонний сайт",
        "Виджет",
        id="blog-275854-widget-height",
    ),
    pytest.param(
        "https://getcourse.ru/blog/298451",
        "Как преодолеть потолок",
        "Как заработать на GetCourse",
        id="blog-298451-overcome-ceiling",
    ),
]


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def expand_sidebar_and_find_link(page: Page, article_url: str, section_title: str):
    """
    Раскрывает правый блок навигации (sidebar) на странице статьи
    и возвращает локатор ссылки на целевую статью.
    """
    page.wait_for_timeout(8000)

    btn = page.locator(".blog-navigation-btn").first
    if btn.is_visible(timeout=5000):
        btn.click()
        page.wait_for_timeout(1000)

    section = page.locator(
        f".blog-navigation-item-title:has(h3:text('{section_title}'))"
    ).first
    if section.is_visible(timeout=3000):
        section.click()
        page.wait_for_timeout(500)

    return page.locator(f"a[href='{article_url}']").first


def click_and_capture_popup(page: Page, link):
    """Кликает по ссылке с target="_blank" и перехватывает новую вкладку."""
    with page.context.expect_page() as popup_info:
        link.click(force=True, timeout=5000)
    popup = popup_info.value
    popup.wait_for_load_state("domcontentloaded", timeout=15000)
    return popup


# ──────────────────────────────────────────────
# Guest — прямой переход на URL каждой битой статьи
# ──────────────────────────────────────────────

@pytest.mark.parametrize("url,title,section", BROKEN_LINKS)
def test_guest_direct_visit_to_broken_article(page: Page, url, title, section):
    """
    Guest: прямой переход на URL битой статьи.
    Ожидается: статья открывается.
    Фактически (баг): редирект на /pl/blog.
    """
    page.goto(url, wait_until="domcontentloaded", timeout=15000)
    final_url = page.url
    assert final_url == url, (
        f"[{title}] Ожидался URL статьи {url}, получен {final_url} (редирект)"
    )


# ──────────────────────────────────────────────
# Guest — проверка присутствия ссылок в sidebar
# ──────────────────────────────────────────────

@pytest.mark.parametrize("url,title,section", BROKEN_LINKS)
def test_guest_sidebar_link_exists(page: Page, url, title, section):
    """Guest: в правом блоке навигации присутствует битая ссылка."""
    page.goto(START_ARTICLE, wait_until="domcontentloaded", timeout=15000)
    link = expand_sidebar_and_find_link(page, url, section)
    expect(link).to_have_attribute("href", url)


# ──────────────────────────────────────────────
# Guest — проверка target=_blank для всех битых ссылок
# ──────────────────────────────────────────────

@pytest.mark.parametrize("url,title,section", BROKEN_LINKS)
def test_guest_sidebar_link_opens_new_tab(page: Page, url, title, section):
    """Guest: битая ссылка в sidebar открывается в новой вкладке (target=_blank)."""
    page.goto(START_ARTICLE, wait_until="domcontentloaded", timeout=15000)
    link = expand_sidebar_and_find_link(page, url, section)
    expect(link).to_have_attribute("target", "_blank")


# ──────────────────────────────────────────────
# Guest — клик по каждой битой ссылке ведёт на редирект
# ──────────────────────────────────────────────

@pytest.mark.parametrize("url,title,section", BROKEN_LINKS)
def test_guest_sidebar_link_leads_to_redirect(page: Page, url, title, section):
    """
    Guest: клик по битой ссылке в sidebar.
    Баг: открывается /pl/blog вместо статьи.
    """
    page.goto(START_ARTICLE, wait_until="domcontentloaded", timeout=15000)
    link = expand_sidebar_and_find_link(page, url, section)
    popup = click_and_capture_popup(page, link)

    final_url = popup.url
    assert final_url == url, (
        f"[{title}] Ожидалась статья {url}, получен {final_url} (баг: редирект)"
    )