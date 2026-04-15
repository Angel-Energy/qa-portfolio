# QA Portfolio

> Портфолио начинающего тестировщика. Здесь собраны баг-репорты,
> чек-листы и примеры ручного тестирования веб- и мобильных приложений.
---

## Обо мне

Специалист службы поддержки пользователей с опытом работы
в сервисах экосистемы Яндекса и практическим опытом
поиска и описания багов в продуктах.

За 4+ года работы в Яндекс Лавке, Яндекс Плюсе,
Яндекс Доставке, Яндекс Драйве и Яндекс Еде
выявляла дефекты и оформляла баг-репорты
с шагами воспроизведения, ожидаемым
и фактическим результатом.

Имею опыт контроля качества по чек-листам,
работы с админ-панелями и взаимодействия
с техническими и продуктовыми командами.

Знакома с теорией тестирования:
функциональное, регрессионное и smoke-тестирование,
жизненный цикл дефекта.

---

## Навыки и инструменты

**Тестирование:**

![Manual Testing](https://img.shields.io/badge/Manual%20Testing-4A90D9?style=for-the-badge)
![Functional Testing](https://img.shields.io/badge/Functional%20Testing-5BA85A?style=for-the-badge)
![UI Testing](https://img.shields.io/badge/UI%20Testing-E67E22?style=for-the-badge)
![Mobile Testing](https://img.shields.io/badge/Mobile%20Testing-9B59B6?style=for-the-badge)
![Web Testing](https://img.shields.io/badge/Web%20Testing-1ABC9C?style=for-the-badge)
![Regression Testing](https://img.shields.io/badge/Regression%20Testing-E74C3C?style=for-the-badge)
![Smoke Testing](https://img.shields.io/badge/Smoke%20Testing-F39C12?style=for-the-badge)
![Negative Testing](https://img.shields.io/badge/Negative%20Testing-C0392B?style=for-the-badge)
![E2E Testing](https://img.shields.io/badge/E2E%20Testing-2980B9?style=for-the-badge)

**Документация:**

![Bug Reports](https://img.shields.io/badge/Bug%20Reports-E74C3C?style=for-the-badge)
![Checklists](https://img.shields.io/badge/Checklists-27AE60?style=for-the-badge)
![Test Cases](https://img.shields.io/badge/Test%20Cases-8E44AD?style=for-the-badge)

**Инструменты:**

![DevTools](https://img.shields.io/badge/DevTools-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)
![Yandex Tracker](https://img.shields.io/badge/Yandex%20Tracker-FFCC00?style=for-the-badge&logoColor=black)

**Платформы:**

![Android](https://img.shields.io/badge/Android%2010%20%2F%2015-3DDC84?style=for-the-badge&logo=android&logoColor=white)
![Windows](https://img.shields.io/badge/Windows%2011-0078D4?style=for-the-badge&logo=windows&logoColor=white)
![Web](https://img.shields.io/badge/Web-FF6B6B?style=for-the-badge&logo=googlechrome&logoColor=white)

**Браузеры:**

![Yandex Browser](https://img.shields.io/badge/Yandex%20Browser-FFCC00?style=for-the-badge&logoColor=black)
![Chrome](https://img.shields.io/badge/Chrome-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white)
![Opera](https://img.shields.io/badge/Opera-FF1B2D?style=for-the-badge&logo=opera&logoColor=white)

---

## Оборудование для тестирования

| Устройство | ОС | Назначение |
|------------|----|------------|
| POCO F5 Pro | Android 15 | Тестирование мобильных приложений и мобильного веба |
| HUAWEI YAL-L21 | Android 10 | Тестирование совместимости на разных версиях Android |
| ПК | Windows 11 | Тестирование десктопных веб-приложений |

**Браузеры:** Yandex Browser · Google Chrome · Opera
**Интернет:** 300 Мбит/с

---


## Баг-репорты

### ⭐ Подтверждены командами разработки

| ID | Продукт | Суть дефекта | Тип | Результат |
|----|---------|--------------|-----|-----------|
| [BUG-001](bug-reports/BUG-001.md) | Яндекс Лавка | Кнопка «В корзину» не реагирует на нажатие в составе набора | Functional | Дефект подтверждён, присвоен severity **Blocker** |
| [BUG-004](bug-reports/BUG-004.md) | НКЭиВТ | Учебный год отображается как «2025» вместо «2025/2026» | UX / Display | Дефект подтверждён, исправление запланировано. Отмечен командой разработки как **образец оформления** |

### Остальные баг-репорты

| ID | Продукт | Суть дефекта | Test Type | Severity | Среда |
|----|---------|--------------|-----------|----------|-------|
| [BUG-002](bug-reports/BUG-002.md) | sovcomjob.ru | Layout overlap: форма перекрывает nav-меню в mobile view | UI / Layout | Major | Android 10 |
| [BUG-003](bug-reports/BUG-003.md) | Яндекс Крауд | Mismatch: формулировка вопроса не соответствует типу ответа | Content / UX | Minor | Web |
| [BUG-005](bug-reports/BUG-005.md) | Яндекс Почта | Data inconsistency: счётчик треда показывает «3» при фактических 2 сообщениях | Functional | Major | Web |
| [BUG-006](bug-reports/BUG-006.md) | Электронный город | API response mismatch: сервер возвращает `text/html` вместо `application/json` | Functional / Server-side | Critical | Web |
| [BUG-007](bug-reports/BUG-007.md) | Т-Образование | HTTP 400 Bad Request при вызове endpoint восстановления пароля — server-side error `bff:invalid-email` | Functional / Server-side | Critical | Web |

---

## Покрытие типов тестирования

```mermaid
pie title Покрытие типов тестирования
    "Functional" : 4
    "UI" : 1
    "UX / Content" : 2
    "Mobile" : 2
    "Web" : 5
    "API" : 2
    "Negative" : 1
    "E2E" : 1
```

| Test Type | Technique | Level | Баг-репорты |
|-----------|-----------|-------|-------------|
| Functional Testing | Black-box | UI + API | BUG-001, BUG-005, BUG-006, BUG-007 |
| UI Testing | Layout / Visual | Frontend | BUG-002 |
| UX / Content Testing | Exploratory | UI | BUG-003, BUG-004 |
| Mobile Testing | Cross-platform | Device | BUG-001, BUG-002 |
| Web Testing | Regression | Browser | BUG-003, BUG-004, BUG-005, BUG-006, BUG-007 |
| API Testing | Negative | Server-side | BUG-006, BUG-007 |
| Negative Testing | Boundary / Error flow | UI + API | BUG-007 |
| End-to-End Testing | Scenario-based | UI + API | BUG-007 |

---

## Чек-листы

| Название | Тип |
|----------|-----|
| [Smoke Checklist — мобильное приложение](checklists/smoke-checklist-mobile-app.md) | Smoke |
| [Regression Checklist — корзина интернет-магазина](checklists/regression-checklist-cart.md) | Regression |

---

## Контакты

[![Email](https://img.shields.io/badge/ms1gnatov1%40yandex.ru-FFCC00?style=for-the-badge&logo=mail.ru&logoColor=black)](mailto:ms1gnatov1@yandex.ru)
[![Новосибирск](https://img.shields.io/badge/Новосибирск-4A90D9?style=for-the-badge&logo=googlemaps&logoColor=white)]()
