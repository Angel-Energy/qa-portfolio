# BUG-008: В правом сайдбаре публичного блога GetCourse отображаются ссылки на снятые/скрытые статьи — при клике редирект на общий листинг блога

> 📖 [HTML-версия отчёта (интерактивная, с полноэкранными скриншотами)](BUG-008-getcourse-blog-sidebar-broken-links-standalone.html)

## Общая информация

- **Проект:** GetCourse (getcourse.ru)
- **Раздел:** Публичный блог → Страница статьи → Правый блок «Навигация по блогу»
- **Тип бага:** Контентный / UX (неактуальные ссылки в публичной навигации)
- **Серьёзность:** Major
- **Приоритет:** High
- **Статус:** New
- **Воспроизводимость:** Always
- **Дата обнаружения:** 19.07.2026

## Окружение

- **ОС:** Windows 11 24H2
- **Браузер:** Яндекс Браузер 26.6.2.938 (64-bit)
- **VPN:** включен (IP: 72.56.50.214, Нидерланды)
- **Роль:** Неавторизованный пользователь (режим инкогнито)

## Предусловия

Пользователь является гостем (не авторизован) и открывает любую статью публичного блога GetCourse, где отображается правый сайдбар «Навигация по блогу».

## Шаги воспроизведения (публичный сценарий)

1. Открыть браузер в режиме инкогнито.
2. Перейти на публичную статью блога, например:
   `https://getcourse.ru/blog/632059?utm_source=main_blog`
3. В правом блоке **«Навигация по блогу»** раскрыть раздел **«Интеграция → SMS»**.
4. Нажать ссылку **«Интеграция с сервисом SMS-рассылок SevenTech»**.
5. Вернуться на исходную статью (или открыть её снова).
6. В правом блоке раскрыть раздел **«Дополнения»**.
7. Нажать ссылку **«Каталог дополнений GetCourse»**.
8. Вернуться на исходную статью.
9. В правом блоке раскрыть раздел **«CMS и свой сайт → Форма»**.
10. Нажать ссылку **«Как сделать фон формы прозрачным»**.
11. Вернуться на исходную статью.
12. В правом блоке раскрыть раздел **«CMS и свой сайт → Виджет»**.
13. Нажать ссылку **«Как изменить высоту виджета, который я вставил на сторонний сайт»**.
14. Вернуться на исходную статью.
15. В правом блоке раскрыть раздел **«Как заработать на GetCourse»**.
16. Нажать ссылку **«Как преодолеть потолок»**.

## Ожидаемый результат

При клике на любую ссылку в правом сайдбаре открывается соответствующая статья (или показывается корректная страница «материал перенесён/удалён» с понятным сообщением и релевантными вариантами).

## Фактический результат

При клике на ссылки из правого сайдбара открывается новая вкладка, но вместо выбранной статьи происходит редирект на общий список статей блога:

`https://getcourse.ru/pl/blog`

Пользователь теряет контекст (ожидал конкретный материал, получил общий листинг).

## Список подтверждённых проблемных ссылок (видны гостю в правом сайдбаре)

| URL статьи | Название | Поведение |
|------------|----------|----------|
| `https://getcourse.ru/blog/886415` | Интеграция с сервисом SMS-рассылок SevenTech | 301 → `/pl/blog` |
| `https://getcourse.ru/blog/1037908` | Каталог дополнений GetCourse | 301 → `/pl/blog` |
| `https://getcourse.ru/blog/275858` | Как сделать фон формы прозрачным | 301 → `/pl/blog` |
| `https://getcourse.ru/blog/275854` | Как изменить высоту виджета, который я вставил на сторонний сайт | 301 → `/pl/blog` |
| `https://getcourse.ru/blog/298451` | Как преодолеть потолок | 301 → `/pl/blog` |

## Технические детали (HTTP)

Проверка редиректа для гостя через PowerShell (без cookies, без JS) показывает, что ссылки действительно отдают постоянный редирект на `/pl/blog`.

### Скрипт проверки всех 5 битых ссылок

<details>
<summary>▶ Развернуть PowerShell-скрипт (проверка 5 битых ссылок)</summary>

```powershell
$urls = @(
  "https://getcourse.ru/blog/886415",
  "https://getcourse.ru/blog/1037908",
  "https://getcourse.ru/blog/275858",
  "https://getcourse.ru/blog/275854",
  "https://getcourse.ru/blog/298451"
)
$headers = @{
    "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
}
foreach ($u in $urls) {
  try {
    $r = Invoke-WebRequest -Uri $u -UseBasicParsing -Headers $headers `
        -MaximumRedirection 0 -ErrorAction Stop
    "{0,-55} {1} -> {2}" -f $u, $r.StatusCode, $r.Headers.Location
  } catch {
    $resp = $_.Exception.Response
    "{0,-55} {1} -> {2}" -f $u, [int]$resp.StatusCode, $resp.Headers.Location
  }
}
```

</details>

### Результат выполнения

```
https://getcourse.ru/blog/886415                        301 -> https://getcourse.ru/pl/blog
https://getcourse.ru/blog/1037908                       301 -> https://getcourse.ru/pl/blog
https://getcourse.ru/blog/275858                        301 -> https://getcourse.ru/pl/blog
https://getcourse.ru/blog/275854                        301 -> https://getcourse.ru/pl/blog
https://getcourse.ru/blog/298451                        301 -> https://getcourse.ru/pl/blog
```

Все 5 ссылок отдают **301 Moved Permanently** → `https://getcourse.ru/pl/blog`.

> ℹ️ Заголовок `User-Agent` обязателен — без него сервер GetCourse отдаёт 404
> вместо редиректа (защита от bare-клиентов).

Дополнительно выполнен полный аудит навигации — скрипт загрузил **все ссылки из Google Таблицы** (источник данных правого сайдбара блога) и проверил каждую через `Invoke-WebRequest` с паузой 200 мс. Всего проверено **666 ссылок**.

### Скрипт полного аудита (загрузка из Google Таблицы + проверка 666 ссылок)

<details>
<summary>▶ Развернуть PowerShell-скрипт (аудит 666 ссылок из Google Таблицы)</summary>

```powershell
# ============================================================
# ПОЛНЫЙ СКРИПТ ПРОВЕРКИ ССЫЛОК ИЗ GOOGLE ТАБЛИЦЫ
# ============================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   🔗 ПРОВЕРКА ССЫЛОК БЛОГА GetCourse          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ШАГ 1: Загрузка ссылок из Google Таблицы
Write-Host "📊 Загружаем Google Таблицу..." -ForegroundColor Yellow

$csvUrl = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTT26be3k3-KkD859vPjLPrTPlsoGaO-SgYUZ2VQxg6PT3Hd0cE37qRi4X4pJ2Jt5YeNWS2_bYg0Stn/pub?output=csv"

try {
    $csvData = Invoke-WebRequest -Uri $csvUrl -UseBasicParsing -ErrorAction Stop
    Write-Host "✅ Таблица загружена: $($csvData.Content.Length) байт" -ForegroundColor Green
} catch {
    Write-Host "❌ ОШИБКА загрузки таблицы: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Нажми Enter для выхода"
    exit
}

# ШАГ 2: Извлечение ссылок
Write-Host "🔍 Извлекаем ссылки..." -ForegroundColor Yellow

$csv = $csvData.Content | ConvertFrom-Csv
$links = $csv | Where-Object { $_.link -like "*getcourse.ru*" } | Select-Object -ExpandProperty link -Unique

Write-Host "✅ Найдено ссылок: $($links.Count)" -ForegroundColor Green

if ($links.Count -eq 0) {
    Write-Host "❌ Ссылки не найдены в таблице!" -ForegroundColor Red
    Read-Host "Нажми Enter для выхода"
    exit
}

# ШАГ 3: Проверка ссылок
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  ПРОВЕРКА ССЫЛОК" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Начинаем проверку $($links.Count) ссылок..." -ForegroundColor White
Write-Host "Примерно времени: ~$([math]::Ceiling($links.Count * 0.2)) секунд" -ForegroundColor Gray
Write-Host ""

$results = @()
$counter = 0
$stats = @{
    Working = 0
    Redirects = 0
    BrokenRedirects = 0
    NotFound = 0
    Errors = 0
}

foreach ($url in $links) {
    $counter++

    try {
        $response = Invoke-WebRequest -Uri $url -MaximumRedirection 0 -UseBasicParsing -ErrorAction SilentlyContinue
        $status = [int]$response.StatusCode
        $location = if ($response.Headers.Location) { $response.Headers.Location } else { "" }
    }
    catch {
        if ($_.Exception.Response) {
            $status = [int]$_.Exception.Response.StatusCode
            $location = if ($_.Exception.Response.Headers.Location) { $_.Exception.Response.Headers.Location.ToString() } else { "" }
        } else {
            $status = "ERROR"
            $location = $_.Exception.Message
        }
    }

    # Определяем тип и цвет
    $isBroken = $false
    $color = "Gray"

    switch ($status) {
        200 {
            $stats.Working++
            $color = "Green"
        }
        301 {
            if ($location -eq "https://getcourse.ru/pl/blog" -or $location -eq "https://getcourse.ru/") {
                $stats.BrokenRedirects++
                $isBroken = $true
                $color = "Red"
            } else {
                $stats.Redirects++
                $color = "Yellow"
            }
        }
        302 {
            $stats.Redirects++
            $color = "Yellow"
        }
        404 {
            $stats.NotFound++
            $isBroken = $true
            $color = "Red"
        }
        default {
            $stats.Errors++
            $color = "Magenta"
        }
    }

    # Показываем прогресс
    if ($counter % 50 -eq 0 -or $isBroken) {
        Write-Host "[$counter/$($links.Count)] $status | $url" -ForegroundColor $color
        if ($location) {
            Write-Host "               → $location" -ForegroundColor DarkGray
        }
    }

    $results += [PSCustomObject]@{
        URL       = $url
        Status    = $status
        Location  = $location
        IsBroken  = $isBroken
    }

    Start-Sleep -Milliseconds 200
}

# ШАГ 4: Статистика
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  📊 СТАТИСТИКА" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "✅ Рабочие (200):        $($stats.Working)" -ForegroundColor Green
Write-Host "🔄 Редиректы (301/302):  $($stats.Redirects)" -ForegroundColor Yellow
Write-Host "❌ Битые редиректы:      $($stats.BrokenRedirects)" -ForegroundColor Red
Write-Host "❌ Не найдено (404):     $($stats.NotFound)" -ForegroundColor Red
Write-Host "⚠️  Ошибки:              $($stats.Errors)" -ForegroundColor Magenta
Write-Host ""

# Группировка по статусам
$results | Group-Object Status | Sort-Object Count -Descending | Format-Table -AutoSize

# ШАГ 5: Битые редиректы
Write-Host "=== ❌ БИТЫЕ РЕДИРЕКТЫ (301 → /pl/blog или /) ===" -ForegroundColor Red
$brokenRedirects = $results | Where-Object {
    $_.Status -eq 301 -and (
        $_.Location -eq "https://getcourse.ru/pl/blog" -or
        $_.Location -eq "https://getcourse.ru/"
    )
}

if ($brokenRedirects.Count -gt 0) {
    $brokenRedirects | Format-Table URL, Status, Location -AutoSize
    Write-Host "❌ НАЙДЕНО БИТЫХ РЕДИРЕКТОВ: $($brokenRedirects.Count)" -ForegroundColor Red
} else {
    Write-Host "✅ Битых редиректов не найдено!" -ForegroundColor Green
}

Write-Host ""

# ШАГ 6: Ошибки 404
Write-Host "=== ❌ ОШИБКИ 404 ===" -ForegroundColor Red
$notFound = $results | Where-Object { $_.Status -eq 404 }
if ($notFound.Count -gt 0) {
    $notFound | Select-Object -First 10 | Format-Table URL -AutoSize
    if ($notFound.Count -gt 10) {
        Write-Host "... и ещё $($notFound.Count - 10) ошибок 404" -ForegroundColor Gray
    }
    Write-Host "❌ ВСЕГО 404: $($notFound.Count)" -ForegroundColor Red
} else {
    Write-Host "✅ Ошибок 404 не найдено!" -ForegroundColor Green
}

# ШАГ 7: Сохранение результатов
$outputFile = "$env:USERPROFILE\Desktop\blog-check-results.csv"
$results | Export-Csv -Path $outputFile -Encoding UTF8 -NoTypeInformation -Delimiter ';'

Write-Host ""
Write-Host "💾 Результаты сохранены: $outputFile" -ForegroundColor Green
Write-Host ""
Write-Host "✅ ГОТОВО!" -ForegroundColor Green
Write-Host ""
```

</details>

### Результат аудита (666 ссылок)

> 📸 Скриншот вывода PowerShell (реальное окно консоли): `screenshots/bug008-powershell-audit-666-links.png`

Проверено **666 ссылок** из Google Таблицы (источник данных правого сайдбара):

| Статус | Кол-во | Описание |
|--------|--------|----------|
| 200 | 661 | Рабочие статьи |
| 301 → `/pl/blog` | 5 | Битые редиректы |
| 404 | 0 | Не найдено |

Найдено **5 битых редиректов** вида `301 → /pl/blog`:

- `https://getcourse.ru/blog/886415`  → `https://getcourse.ru/pl/blog`
- `https://getcourse.ru/blog/1037908` → `https://getcourse.ru/pl/blog`
- `https://getcourse.ru/blog/275858`  → `https://getcourse.ru/pl/blog`
- `https://getcourse.ru/blog/275854`  → `https://getcourse.ru/pl/blog`
- `https://getcourse.ru/blog/298451`  → `https://getcourse.ru/pl/blog`

Ошибок 404 не обнаружено — ссылки ведут на существующие страницы, но сервер редиректит их на общий листинг, а не на конкретную статью.

## Влияние на пользователя

- Гости и потенциальные клиенты получают «сломанные» ссылки в публичной навигации.
- Ухудшается UX: пользователь ожидает конкретную статью, но попадает на общий список.
- Навигация по блогу теряет смысл и снижает доверие к контенту.

## Предположение о причине

Часть статей была снята с публикации/скрыта для гостей или перенесена, но ссылки на них остаются в источнике формирования правого сайдбара (и/или в связанных навигационных списках), из-за чего публичная навигация содержит недоступные материалы.

## Рекомендации по исправлению

**Контент (приоритетно):**

1. Удалить/заменить в навигации правого сайдбара ссылки на снятые/скрытые статьи (список из 5 URL).
2. Если есть актуальные версии материалов — настроить редирект на конкретные статьи, а не на общий листинг.

**Разработка (желательно):**

1. Вместо редиректа на общий листинг показывать страницу «Материал недоступен/перенесён» с подсказками и релевантными ссылками.
2. Автоматизировать проверку «битых» ссылок (например, регулярный аудит списка ссылок навигации).

## Вложения

**Скриншоты правого сайдбара с подсветкой битых ссылок (красная рамка + URL):**

> ℹ️ Скриншоты получены через автотесты Playwright (Chromium headless).
> Ручное воспроизведение проводилось в Яндекс Браузере (см. раздел «Окружение»).
> Баг воспроизводится в обоих браузерах.

1. `screenshots/bug008-link-886415-sms-seventech.png` — «Интеграция с сервисом SMS-рассылок SevenTech» (раздел «Интеграция → SMS»)
2. `screenshots/bug008-link-1037908-addon-catalog.png` — «Каталог дополнений GetCourse» (раздел «Дополнения»)
3. `screenshots/bug008-link-275858-form-transparent.png` — «Как сделать фон формы прозрачным» (раздел «CMS → Форма»)
4. `screenshots/bug008-link-275854-widget-height.png` — «Как изменить высоту виджета» (раздел «CMS → Виджет»)
5. `screenshots/bug008-link-298451-overcome-ceiling.png` — «Как преодолеть потолок» (раздел «Как заработать на GetCourse»)

**Скриншот результата редиректа:**

6. `screenshots/bug008-redirect-result-pl-blog.png` — итог клика по битой ссылке: общий листинг блога вместо статьи

**Скриншот вывода PowerShell (реальная консоль):**

7. `screenshots/bug008-powershell-audit-666-links.png` — результат полного аудита 666 ссылок из Google Таблицы: статистика, список 5 битых редиректов, отсутствие 404
